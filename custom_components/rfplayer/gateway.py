"""RfPlayer gateway."""

import asyncio
from collections.abc import Mapping
import contextlib
import json
import logging
from typing import TYPE_CHECKING, Any

from custom_components.rfplayer.config_options import RfPlayerDeviceInfo, RfPlayerOptions, save_options
from custom_components.rfplayer.const import (
    CONNECTION_TIMEOUT,
    INIT_COMMANDS_EMPTY,
    INIT_COMMANDS_SEPARATOR,
    SIGNAL_RFPLAYER_AVAILABILITY,
    SIGNAL_RFPLAYER_EVENT,
)
from custom_components.rfplayer.device_profiles import UNDEFINED_PROFILE, async_get_profile_registry
from custom_components.rfplayer.device_publishers import get_bus_publisher
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, PlatformNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

if TYPE_CHECKING:
    from custom_components.rfplayer.runtime import RfPlayerConfigEntry

_LOGGER = logging.getLogger(__name__)


class Gateway:
    """RfPlayer gateway."""

    def __init__(self, hass: HomeAssistant, entry: RfPlayerConfigEntry):
        """Create a new RfPlayer gateway."""
        self.hass = hass
        self.entry = entry
        self._reconnect_task: asyncio.Task[None] | None = None
        self._unloading = False

    async def async_setup(self) -> None:
        """Load a RfPlayer gateway."""

        self.options = RfPlayerOptions.from_json(self.entry.data)

        self.profile_registry = await async_get_profile_registry(self.hass, self.options.verbose_mode)
        self.bus_publisher = get_bus_publisher()

        # Initialize library
        self.client = RfPlayerClient(
            event_callback=self._async_handle_receive,
            disconnect_callback=self._reconnect_gateway,
            port=self.options.device,
            receiver_protocols=self.options.receiver_protocols,
            init_commands=self._prepare_init_commands(),
            verbose=self.options.verbose_mode,
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
        commands = self.options.init_commands.split(INIT_COMMANDS_SEPARATOR)
        commands = [c.strip() for c in commands]
        return [c for c in commands if c != INIT_COMMANDS_EMPTY]

    @callback
    def _async_handle_receive(self, event: RfDeviceEvent) -> None:
        """Event handler connected to the client."""

        _LOGGER.debug("Received event from %s", event.device.canonical_id)
        if self.options.verbose_mode:
            _LOGGER.debug("Event data %s", json.dumps(event.data))

        if self.options.automatic_add and not self.options.has_device(event.device.canonical_id):
            self._add_rf_device(event)
            # Still send event for group events

        # Replace event address if device has redirect configuration
        device_info = self.options.get_redirected_device(event.device.canonical_id)
        if device_info:
            event.device.address = device_info.address

        # Callback to HA registered components.
        async_dispatcher_send(self.hass, SIGNAL_RFPLAYER_EVENT, event)  # type: ignore[has-type]

        self.hass.async_create_task(self.bus_publisher.async_fire(self.hass, event))

    @callback
    def _add_rf_device(self, event: RfDeviceEvent) -> None:
        profile_name = self.profile_registry.get_profile_name_from_event(event.data)
        if profile_name == UNDEFINED_PROFILE:
            _LOGGER.debug(
                "No matching profile for device %s event %s", event.device.canonical_id, json.dumps(event.data)
            )
            return
        device_info = RfPlayerDeviceInfo.from_event(profile_name, event)

        self.options = self.options.with_updated_device(event.device.canonical_id, device_info)
        save_options(self.hass, self.entry, self.options, reload=False)

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
                await asyncio.sleep(self.options.reconnect_interval)

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

    async def async_send_raw_command(self, command: str) -> None:
        """Send a raw command to the RfPlayer gateway."""
        if not self.client.connected:
            raise PlatformNotReady("RfPlayer not connected")

        await self.client.send_raw_command(command)

    async def async_simulate_event(self, event_data: Mapping[str, Any]) -> None:
        """Send a raw command to the RfPlayer gateway."""
        if not self.client.connected:
            raise PlatformNotReady("RfPlayer not connected")

        await self.client.simulate_event(event_data)
