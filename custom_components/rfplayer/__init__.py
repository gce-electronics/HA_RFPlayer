"""Support for Rfplayer devices."""

from asyncio import BaseTransport, timeout
import copy
import logging
from typing import Any, cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_STATE,
    CONF_COMMAND,
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_PROTOCOL,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import CoreState, HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_ADDRESS,
    CONF_RECONNECT_INTERVAL,
    CONNECTION_TIMEOUT,
    DATA_DEVICE_REGISTER,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_BUTTON_PRESSED,
    EVENT_KEY_COMMAND,
    EVENT_KEY_ID,
    EVENT_KEY_JAMMING,
    EVENT_KEY_SENSOR,
    PLATFORMS,
    RFPLAYER_PROTOCOL,
    SERVICE_SEND_COMMAND,
    SIGNAL_AVAILABILITY,
    SIGNAL_EVENT,
    SIGNAL_HANDLE_EVENT,
)
from .rflib.rfpprotocol import (
    ProtocolBase,
    RfplayerProtocol,
    create_rfplayer_connection,
)

_LOGGER = logging.getLogger(__name__)


SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROTOCOL): cv.string,
        vol.Required(CONF_COMMAND): cv.string,
        vol.Optional(CONF_DEVICE_ADDRESS): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_AUTOMATIC_ADD, default=False): cv.boolean,  # type: ignore
    }
)


def identify_event_type(event):
    """Look at event to determine type of device.

    Async friendly.
    """
    if "JAMMING_" in event.get(EVENT_KEY_ID):
        return EVENT_KEY_JAMMING
    if EVENT_KEY_COMMAND in event:
        return EVENT_KEY_COMMAND
    if EVENT_KEY_SENSOR in event:
        return EVENT_KEY_SENSOR
    return "unknown"


# pylint: disable-next=too-many-statements
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GCE RFPlayer from a config entry."""

    config = entry.data
    options = entry.options

    hass.data.setdefault(
        DOMAIN,
        {
            CONF_DEVICE: config[CONF_DEVICE],
            DATA_ENTITY_LOOKUP: {
                EVENT_KEY_COMMAND: {},
                EVENT_KEY_SENSOR: {},
                EVENT_KEY_JAMMING: {},
            },
            DATA_DEVICE_REGISTER: {},
        },
    )

    async def async_send_command(call):
        """Send Rfplayer command."""
        _LOGGER.debug("Rfplayer send command for %s", str(call.data))
        if not await hass.data[DOMAIN][RFPLAYER_PROTOCOL].send_command_ack(
            protocol=call.data[CONF_PROTOCOL],
            command=call.data[CONF_COMMAND],
            device_address=call.data.get(CONF_DEVICE_ADDRESS),
            device_id=call.data.get(CONF_DEVICE_ID),
        ):
            _LOGGER.error("Failed Rfplayer command")
        if call.data[CONF_AUTOMATIC_ADD] is True:
            _LOGGER.debug("Add device for %s", str(call.data))
            event_id = "_".join(
                [
                    call.data[CONF_PROTOCOL],
                    call.data.get(CONF_DEVICE_ID)
                    or call.data.get(CONF_DEVICE_ADDRESS)
                    or call.data.get(CONF_COMMAND),
                ]
            )
            device = {
                CONF_PROTOCOL: call.data[CONF_PROTOCOL],
                CONF_DEVICE_ADDRESS: call.data.get(CONF_DEVICE_ADDRESS),
                CONF_DEVICE_ID: call.data.get(CONF_DEVICE_ID),
                EVENT_KEY_COMMAND: True,
                EVENT_KEY_ID: event_id,
            }
            await hass.data[DOMAIN][DATA_DEVICE_REGISTER][EVENT_KEY_COMMAND](device)
            _add_device_to_base_config(device, event_id)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_COMMAND, async_send_command, schema=SEND_COMMAND_SCHEMA
    )

    @callback
    def event_callback(event):
        """Handle incoming Rfplayer events.

        Rfplayer events arrive as dictionaries of varying content
        depending on their type. Identify the events and distribute
        accordingly.
        """
        event_type = identify_event_type(event)
        _LOGGER.debug("event of type %s: %s", event_type, event)

        # Don't propagate non entity events (eg: version string, ack response)
        if event_type not in hass.data[DOMAIN][DATA_ENTITY_LOOKUP]:
            _LOGGER.debug("unhandled event of type: %s", event_type)
            return

        # Lookup entities who registered this device id as device id or alias
        event_id = event.get(EVENT_KEY_ID)

        entity_id = hass.data[DOMAIN][DATA_ENTITY_LOOKUP][event_type].get(event_id)

        if entity_id:
            # Propagate event to every entity matching the device id
            _LOGGER.debug("passing event to %s", entity_id)
            async_dispatcher_send(hass, SIGNAL_HANDLE_EVENT.format(entity_id), event)
        elif event_type in hass.data[DOMAIN][DATA_DEVICE_REGISTER]:
            _LOGGER.debug("event_id not known, adding new device")
            # Should be entity_id (see above) which is not yet known
            # Set to event to prevent race condition
            # Will be set to entity_id once created
            hass.data[DOMAIN][DATA_ENTITY_LOOKUP][event_type][event_id] = event
            _add_device_to_base_config(event, event_id)
            hass.async_create_task(
                hass.data[DOMAIN][DATA_DEVICE_REGISTER][event_type](event)
            )
        else:
            _LOGGER.debug("event_id not known and automatic add disabled")

    @callback
    def _add_device_to_base_config(event, event_id):
        """Add a device to config entry."""
        data = entry.data.copy()
        data[CONF_DEVICES] = copy.deepcopy(entry.data[CONF_DEVICES])
        data[CONF_DEVICES][event_id] = event
        hass.config_entries.async_update_entry(entry=entry, data=data)

    @callback
    def reconnect(exc=None):
        """Schedule reconnect after connection has been unexpectedly lost."""

        # Reset protocol binding before starting reconnect
        if exc:
            _LOGGER.error(exc)

        # Check if domain unloaded
        if DOMAIN in hass.data:
            hass.data[DOMAIN][RFPLAYER_PROTOCOL] = None

        async_dispatcher_send(hass, SIGNAL_AVAILABILITY, False)

        # If HA is not stopping and connection not explicitly closed, initiate new connection
        if hass.state != CoreState.stopping and exc:
            _LOGGER.warning("Disconnected from Rfplayer, reconnecting")
            hass.async_create_task(connect())
        else:
            _LOGGER.warning("Rfplayer connection closed")

    async def connect():
        """Set up connection and hook it into HA for reconnect/shutdown."""
        _LOGGER.info("Initiating Rfplayer connection")
        connection = create_rfplayer_connection(
            port=config[CONF_DEVICE],
            event_callback=event_callback,
            disconnect_callback=reconnect,
            loop=hass.loop,
        )
        transport: BaseTransport
        protocol: ProtocolBase

        try:
            async with timeout(CONNECTION_TIMEOUT):
                transport, protocol = await connection

        except (TimeoutError, OSError) as exc:
            reconnect_interval = config[CONF_RECONNECT_INTERVAL]
            _LOGGER.exception(
                "Error connecting to Rfplayer, reconnecting in %s",
                reconnect_interval,
            )
            # Connection to Rfplayer device is lost, make entities unavailable
            async_dispatcher_send(hass, SIGNAL_AVAILABILITY, False)

            hass.loop.call_later(reconnect_interval, reconnect, exc)
            return

        # There is a valid connection to a Rfplayer device now so
        # mark entities as available
        async_dispatcher_send(hass, SIGNAL_AVAILABILITY, True)

        # FIXME don't reload on update cause it's causing serial reconnection and duplicate entries

        hass.data[DOMAIN][RFPLAYER_PROTOCOL] = protocol

        # handle shutdown of Rfplayer asyncio transport
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, lambda x: transport.close()
        )

        _LOGGER.info("Connected to Rfplayer")

    hass.async_create_task(connect())

    async_dispatcher_connect(hass, SIGNAL_EVENT, event_callback)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)

    protocol = cast(ProtocolBase, hass.data[DOMAIN][RFPLAYER_PROTOCOL])
    if protocol:
        _LOGGER.info("Closing RfPlayer connection on unload")
        hass.data[DOMAIN][RFPLAYER_PROTOCOL] = None
        if protocol.transport:
            protocol.transport.close()

    hass.data.pop(DOMAIN)

    return True


# pylint: disable-next=too-many-instance-attributes
class RfplayerDevice(RestoreEntity):
    """Representation of a Rfplayer device.

    Contains the common logic for Rfplayer entities.
    """

    _available = True
    _attr_assumed_state = True
    _attr_should_poll = False

    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        unique_id: str,
        protocol: str,
        event_type: str,
        device_address: str | None = None,
        device_id: str | None = None,
        initial_event: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize the device."""
        # Rfplayer specific attributes for every component type
        if not (device_address or device_id):
            raise TypeError("Incorrect arguments for RfplayerDevice")
        self._initial_event = initial_event
        self._protocol = protocol
        self._device_id = device_id
        self._device_address = device_address
        self._event = None

        self._attr_name = (
            name or f"{protocol} {device_address or device_id} {event_type}"
        )
        self._attr_unique_id = slugify(unique_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.hass.data[DOMAIN][CONF_DEVICE])},
            manufacturer="GCE",
            model="RFPlayer",
            name="RFPlayer",
        )

    async def _async_send_command(self, command) -> None:
        rfplayer: RfplayerProtocol = self.hass.data[DOMAIN][RFPLAYER_PROTOCOL]
        await rfplayer.send_command_ack(
            command=command,
            protocol=self._protocol,
            device_id=self._device_id,
            device_address=self._device_address,
        )

    @callback
    def handle_event_callback(self, event: dict[str, Any]) -> None:
        """Handle incoming event for device type."""
        # Call platform specific event handler
        self._handle_event(event)

        # Propagate changes through ha
        self.async_write_ha_state()

        # Put command onto bus for user to subscribe to
        if identify_event_type(event) == EVENT_KEY_COMMAND:
            self.hass.bus.async_fire(
                EVENT_BUTTON_PRESSED,
                {ATTR_ENTITY_ID: self.entity_id, ATTR_STATE: event[EVENT_KEY_COMMAND]},
            )
            _LOGGER.debug(
                "Fired bus event for %s: %s", self.entity_id, event[EVENT_KEY_COMMAND]
            )

    def _handle_event(self, event) -> None:
        """Platform specific event handler."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self._available)

    @callback
    def _availability_callback(self, availability) -> None:
        """Update availability state."""
        _LOGGER.debug("availability state updated %s", availability)
        self._available = availability
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        await super().async_added_to_hass()

        self.async_on_remove(
            # connect returns the method to be called on remove
            async_dispatcher_connect(
                self.hass, SIGNAL_AVAILABILITY, self._availability_callback
            )
        )
        self.async_on_remove(
            # connect returns the method to be called on remove
            async_dispatcher_connect(
                self.hass,
                SIGNAL_HANDLE_EVENT.format(self.entity_id),
                self.handle_event_callback,
            )
        )

        # Process the initial event now that the entity is created
        if self._initial_event:
            self.handle_event_callback(self._initial_event)
