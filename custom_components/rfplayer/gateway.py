"""RfPlayer gateway."""

import asyncio
import contextlib
import copy
import json
import logging
from typing import TYPE_CHECKING, cast

from custom_components.rfplayer.const import (
    ATTR_COMMAND,
    ATTR_EVENT_DATA,
    CONF_AUTOMATIC_ADD,
    CONF_INIT_COMMANDS,
    CONF_RECEIVER_PROTOCOLS,
    CONF_RECONNECT_INTERVAL,
    CONF_REDIRECT_ADDRESS,
    CONF_VERBOSE_MODE,
    CONNECTION_TIMEOUT,
    INIT_COMMANDS_EMPTY,
    INIT_COMMANDS_SEPARATOR,
    SIGNAL_RFPLAYER_AVAILABILITY,
    SIGNAL_RFPLAYER_EVENT,
)
from custom_components.rfplayer.device_profiles import UNDEFINED_PROFILE, async_get_profile_registry
from custom_components.rfplayer.device_publishers import get_bus_publisher
from custom_components.rfplayer.helpers import build_device_info_from_event
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE, CONF_DEVICES, CONF_PROFILE_NAME, CONF_PROTOCOL
from homeassistant.core import CoreState, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, PlatformNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

if TYPE_CHECKING:
    from custom_components.rfplayer.runtime import RfPlayerConfigEntry

_LOGGER = logging.getLogger(__name__)


JAMMING_DEVICE_ID_STRING = "JAMMING_0"
JAMMING_DEVICE_INFO = {CONF_PROTOCOL: "JAMMING", CONF_ADDRESS: "0", CONF_PROFILE_NAME: "Jamming Detector"}


class Gateway:
    """RfPlayer gateway."""

    def __init__(self, hass: HomeAssistant, entry: RfPlayerConfigEntry):
        """Create a new RfPlayer gateway."""

        self.hass = hass
        self.entry = entry
        self.config = entry.data
        # All RfPlayer gateways are configured by default with a Jamming detector
        self.config[CONF_DEVICES].update({JAMMING_DEVICE_ID_STRING: JAMMING_DEVICE_INFO})
        self._reconnect_task: asyncio.Task[None] | None = None
        self._unloading = False

    async def async_setup(self):
        """Load a RfPlayer gateway."""

        self.verbose = self.config.get(CONF_VERBOSE_MODE, False)
        self.profile_registry = await async_get_profile_registry(self.hass, self.verbose)
        self.bus_publisher = get_bus_publisher()

        # Initialize library
        self.client = RfPlayerClient(
            event_callback=self._async_handle_receive,
            disconnect_callback=self._reconnect_gateway,
            port=self.config[CONF_DEVICE],
            receiver_protocols=self.config[CONF_RECEIVER_PROTOCOLS],
            init_commands=self._prepare_init_commands(),
            verbose=self.verbose,
        )

        try:
            await self._connect_gateway()
        except (
            RfPlayerException,
            TimeoutError,
        ) as exc:
            raise ConfigEntryNotReady(f"Failed to setup gateway: {exc!s}") from exc

    async def async_unload(self):
        """Unload a RfPlayer gateway."""
        self._unloading = True

        await self._cancel_reconnect_task()
        self.client.close()

    def is_stopping(self) -> bool:
        """Return True if HA is stopping or the gateway is unloading."""
        return self._unloading or self.hass.state is CoreState.stopping

    def _prepare_init_commands(self) -> list[str]:
        command_string = cast(str, self.config[CONF_INIT_COMMANDS])
        commands = command_string.split(INIT_COMMANDS_SEPARATOR)
        commands = [c.strip() for c in commands]
        return [c for c in commands if c != INIT_COMMANDS_EMPTY]

    @callback
    def _async_handle_receive(self, event: RfDeviceEvent) -> None:
        """Event handler connected to the client."""

        _LOGGER.debug("Received event from %s", event.device.id_string)
        if self.verbose:
            _LOGGER.debug("Event data %s", json.dumps(event.data))

        if event.device.id_string not in self.entry.data[CONF_DEVICES] and self.config[CONF_AUTOMATIC_ADD]:
            self._add_rf_device(event)
            # Still send event for group events

        # Replace event address if device has redirect configuration
        if event.device.id_string in self.config[CONF_REDIRECT_ADDRESS]:
            redirected_id_string = self.config[CONF_REDIRECT_ADDRESS][event.device.id_string]
            event.device.address = self.config[CONF_DEVICES][redirected_id_string][CONF_ADDRESS]

        # Callback to HA registered components.
        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_EVENT, event)  # type: ignore[has-type]

        self.hass.async_create_task(self.bus_publisher.async_fire(self.hass, event))

    @callback
    def _add_rf_device(self, event: RfDeviceEvent) -> None:
        device_info = build_device_info_from_event(self.profile_registry, event)
        if device_info[CONF_PROFILE_NAME] == UNDEFINED_PROFILE:
            _LOGGER.debug("No matching profile for device %s event %s", event.device.id_string, json.dumps(event.data))
            return

        data = self.entry.data.copy()
        data[CONF_DEVICES] = copy.deepcopy(self.entry.data[CONF_DEVICES])
        data[CONF_DEVICES][event.device.id_string] = device_info
        self.hass.config_entries.async_update_entry(entry=self.entry, data=data)
        _LOGGER.debug(
            "Device %s added (Proto: %s Addr: %s Model: %s)",
            event.device.id_string,
            event.device.protocol,
            event.device.address,
            event.device.model,
        )

    async def async_remove_rf_device(self, device_entry: dr.DeviceEntry) -> bool:
        """Remove a device from the config entry."""
        if len(device_entry.identifiers) != 1:
            _LOGGER.warning("Device %s has more than one identifier, cannot remove", device_entry.id)
            return False
        _, id_string = next(iter(device_entry.identifiers))
        data = {
            **self.entry.data,
            CONF_DEVICES: {
                device_config_id: entity_info
                for device_config_id, entity_info in self.entry.data[CONF_DEVICES].items()
                if device_config_id != id_string
            },
        }
        updated = self.hass.config_entries.async_update_entry(entry=self.entry, data=data)
        _LOGGER.debug("Device %s %s", id_string, "removed" if updated else "not removed")
        return updated

    async def _connect_gateway(self) -> None:
        """Set up connection and hook it into HA for reconnect/shutdown."""
        _LOGGER.debug("Initiating RFPlayer connection")

        if self.is_stopping():
            _LOGGER.debug("Not connecting to RFPlayer because HA is stopping")
            return
        connect_task = self.hass.async_create_task(self.client.connect())
        await asyncio.wait_for(connect_task, timeout=CONNECTION_TIMEOUT)

        # There is a valid connection to a RfPlayer gateway now so
        # mark entities as available
        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_AVAILABILITY, True)  # type: ignore[has-type]

        _LOGGER.debug("Connected to RfPlayer")

    @callback
    def _reconnect_gateway(self, exc: Exception | None = None) -> None:
        """Schedule reconnect after connection has been unexpectedly lost."""
        if exc:
            _LOGGER.warning("Connection error %s", exc)
        else:
            _LOGGER.info("Connection explicitly closed")

        # Connection to RfPlayer gateway is lost, make entities unavailable
        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_AVAILABILITY, False)

        # If HA is not stopping, initiate new connection
        if self.is_stopping():
            return

        # Do not schedule a new reconnect if one is already scheduled and not done yet
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return

        self._reconnect_task = self.hass.async_create_task(
            self._reconnect_after_delay(),
        )

    async def _reconnect_after_delay(self) -> None:
        """Reconnect after the configured delay."""
        try:
            while not self.is_stopping():
                await asyncio.sleep(self.config[CONF_RECONNECT_INTERVAL])

                if self.is_stopping():
                    return

                try:
                    await self._connect_gateway()
                except (RfPlayerException, TimeoutError) as exc:
                    _LOGGER.warning("Reconnect failed: %s", exc)
                    continue

                return
        except asyncio.CancelledError:
            _LOGGER.debug("Reconnect task cancelled")
        finally:
            self._reconnect_task = None

    async def _cancel_reconnect_task(self) -> None:
        """Cancel any scheduled reconnect task."""
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

    async def async_send_raw_command(self, call: ServiceCall) -> None:
        """Send a raw command to the RfPlayer gateway."""
        if not self.client.connected:
            raise PlatformNotReady("RfPlayer not connected")

        command = call.data[ATTR_COMMAND]
        await self.client.send_raw_command(command)

    async def async_send_pairing_command(self, call: ServiceCall) -> None:
        """Send a pairing command to the RfPlayer gateway."""
        if not self.client.connected:
            raise PlatformNotReady("RfPlayer not connected")

        device_id = RfDeviceId(protocol=call.data[CONF_PROTOCOL], address=call.data[CONF_ADDRESS])
        await self.client.send_raw_command(f"ASSOC {device_id.protocol} ID {device_id.integer_address}")

    async def async_simulate_event(self, call: ServiceCall) -> None:
        """Simulate an event from a device."""
        if not self.client.connected:
            raise PlatformNotReady("RfPlayer not connected")

        await self.client.simulate_event(call.data[ATTR_EVENT_DATA])
