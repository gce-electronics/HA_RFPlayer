"""Home Assistant gateway for an RFPlayer config entry."""

from collections.abc import Mapping
import json
import logging
from typing import TYPE_CHECKING, Any

from custom_components.rfplayer.config_options import RfPlayerConfigData, RfPlayerDeviceInfo, load_options, save_options
from custom_components.rfplayer.const import (
    INIT_COMMANDS_EMPTY,
    INIT_COMMANDS_SEPARATOR,
    SIGNAL_RFPLAYER_AVAILABILITY,
    SIGNAL_RFPLAYER_EVENT,
)
from custom_components.rfplayer.device_profiles import UNDEFINED_PROFILE, async_get_profile_registry
from custom_components.rfplayer.device_publishers import get_bus_publisher
from custom_components.rfplayer.discovery import DiscoverySession
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.session import RfPlayerSession, RfPlayerSessionCallbacks, RfPlayerSessionConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, PlatformNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

if TYPE_CHECKING:
    from custom_components.rfplayer.runtime import RfPlayerConfigEntry

_LOGGER = logging.getLogger(__name__)


class Gateway:
    """Coordinate an RFPlayer session with Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: RfPlayerConfigEntry):
        """Create a gateway for a finalized config entry."""
        self.hass = hass
        self.entry = entry
        self._session: RfPlayerSession | None = None
        self.discovery = DiscoverySession()

    async def async_setup(self) -> None:
        """Load options and establish the RFPlayer connection."""
        self.config = RfPlayerConfigData.from_json(self.entry.data)
        self.options = load_options(self.entry)
        self.profile_registry = await async_get_profile_registry(self.hass, self.options.verbose_mode)
        self.bus_publisher = get_bus_publisher()
        self._session = RfPlayerSession(
            hass=self.hass,
            config=RfPlayerSessionConfig(
                device=self.config.device,
                receiver_protocols=self.options.receiver_protocols,
                init_commands=self._prepare_init_commands(),
                verbose_mode=self.options.verbose_mode,
                reconnect_interval=self.options.reconnect_interval,
            ),
            callbacks=RfPlayerSessionCallbacks(
                receive=self._async_handle_receive,
                connected=self._handle_connected,
                disconnected=self._handle_disconnected,
            ),
        )

        try:
            await self._session.async_setup()
        except (RfPlayerException, TimeoutError) as exc:
            raise ConfigEntryNotReady(f"Failed to setup gateway: {exc!s}") from exc

    async def async_unload(self) -> None:
        """Unload the active RFPlayer session."""
        if self._session is not None:
            await self._session.async_unload()

    @property
    def client(self) -> RfPlayerClient:
        """Return the underlying RFPlayer client."""
        if self._session is None:
            raise PlatformNotReady("RfPlayer not connected")
        return self._session.client

    def _prepare_init_commands(self) -> list[str]:
        commands = self.options.init_commands.split(INIT_COMMANDS_SEPARATOR)
        commands = [command.strip() for command in commands]
        return [command for command in commands if command != INIT_COMMANDS_EMPTY]

    @callback
    def _handle_connected(self) -> None:
        """Mark all RFPlayer entities as available."""
        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_AVAILABILITY, True)  # type: ignore[has-type]

    @callback
    def _handle_disconnected(self) -> None:
        """Mark all RFPlayer entities as unavailable."""
        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_AVAILABILITY, False)

    @callback
    def _async_handle_receive(self, event: RfDeviceEvent) -> None:
        """Handle a device event from the active RFPlayer session."""
        _LOGGER.debug("Received event from %s", event.device.canonical_id)
        if self.options.verbose_mode:
            _LOGGER.debug("Event data %s", json.dumps(event.data))

        canonical_id = event.device.canonical_id
        redirected_device = self.options.get_redirected_device(canonical_id)
        if self.discovery.capture(
            event,
            eligible=not self.options.has_device(canonical_id) and redirected_device is None,
        ):
            # Stop further processing of the event if the device is unknown and was captured
            # for discovery
            return

        if self.options.automatic_add and not self.options.has_device(canonical_id) and redirected_device is None:
            # Legacy auto discovery method
            self._add_rf_device(event)

        if redirected_device:
            event.device.address = redirected_device.address

        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_EVENT, event)  # type: ignore[has-type]
        self.hass.async_create_task(self.bus_publisher.async_fire(self.hass, event))

    def start_discovery(self) -> None:
        """Start buffering unknown device events."""
        self.discovery.start()

    def stop_discovery(self) -> list[RfDeviceEvent]:
        """Stop buffering and return captured unknown device events."""
        return self.discovery.stop()

    @callback
    def _add_rf_device(self, event: RfDeviceEvent) -> None:
        """Add an automatically discovered RF device to config entry options."""
        profile_name = self.profile_registry.get_profile_name_from_event(event.data)
        if profile_name == UNDEFINED_PROFILE:
            _LOGGER.debug(
                "No matching profile for device %s event %s", event.device.canonical_id, json.dumps(event.data)
            )
            return

        device_info = RfPlayerDeviceInfo.from_event(profile_name, event)
        self.options = self.options.with_updated_device(event.device.canonical_id, device_info)
        save_options(self.hass, self.entry, self.options)
        _LOGGER.debug(
            "Device %s added (Proto: %s Addr: %s Model: %s)",
            event.device.canonical_id,
            event.device.protocol,
            event.device.address,
            event.device.model,
        )

    async def async_remove_rf_device(self, device_entry: dr.DeviceEntry) -> bool:
        """Remove a device from the config entry."""
        if len(device_entry.identifiers) != 1:
            _LOGGER.warning("Device %s has more than one identifier, cannot remove", device_entry.id)
            return False

        _, canonical_id = next(iter(device_entry.identifiers))
        self.options = self.options.with_removed_device(canonical_id)
        updated = save_options(self.hass, self.entry, self.options)
        _LOGGER.debug("Device %s %s", canonical_id, "removed" if updated else "not removed")
        return updated

    async def async_send_raw_command(self, command: str) -> None:
        """Send a raw command to the RFPlayer."""
        if not (self._session and self._session.client.connected):
            raise PlatformNotReady("RfPlayer not connected")
        await self._session.client.send_raw_command(command)

    async def async_send_pairing_command(self, device_id: RfDeviceId) -> None:
        """Send an association command so the RF device learns the RfPlayer address."""
        await self.async_send_raw_command(f"ASSOC {device_id.protocol} ID {device_id.integer_address}")

    async def async_simulate_event(self, event_data: Mapping[str, Any]) -> None:
        """Send a simulated RF event."""
        if not (self._session and self._session.client.connected):
            raise PlatformNotReady("RfPlayer not connected")
        await self._session.client.simulate_event(event_data)
