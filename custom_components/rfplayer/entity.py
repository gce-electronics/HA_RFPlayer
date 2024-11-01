"""Support for RF devices."""

from collections.abc import Callable
import json
import logging
from typing import cast

import slugify

from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, async_get_profile_registry
from custom_components.rfplayer.helpers import (
    build_device_id_from_device_info,
    build_device_info_from_event,
    build_event_data_from_device_info,
    get_identifiers_from_device_id,
)
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES, CONF_PROFILE_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_EVENT_DATA,
    CONF_AUTOMATIC_ADD,
    CONF_VERBOSE_MODE,
    DOMAIN,
    RFPLAYER_CLIENT,
    SIGNAL_RFPLAYER_AVAILABILITY,
    SIGNAL_RFPLAYER_EVENT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform: Platform,
    builder: Callable[
        [RfDeviceId, list[AnyRfpPlatformConfig], RfPlayerEventData | None, bool],
        list[Entity],
    ],
) -> None:
    """Set up config entry."""
    entry_data = config_entry.data
    # Set of device IDs already configured for the current platform
    string_ids: set[str] = set()

    profile_registry = await async_get_profile_registry(hass, entry_data.get(CONF_VERBOSE_MODE, False))

    # Add entities from config
    entities = []
    for id_string, device_info in entry_data[CONF_DEVICES].items():
        if id_string in string_ids:
            _LOGGER.info(
                "Device %s already configured for platform %s",
                id_string,
                platform,
            )
            continue

        profile_name = device_info.get(CONF_PROFILE_NAME)
        if profile_name is None:
            _LOGGER.warning("Missing profile in device info for %s", id_string)
            continue

        platform_config = profile_registry.get_platform_config(profile_name, platform)
        if not platform_config:
            continue

        device_id = build_device_id_from_device_info(device_info)
        event_data = build_event_data_from_device_info(device_info)

        string_ids.add(id_string)
        entities.extend(builder(device_id, platform_config, event_data, entry_data.get(CONF_VERBOSE_MODE, False)))

    async_add_entities(entities)

    # If automatic add is on, hookup listener
    if entry_data[CONF_AUTOMATIC_ADD]:

        @callback
        def _update(event: RfDeviceEvent) -> None:
            if event.device.id_string in string_ids:
                return

            # Add the device to the list of already processed devices
            # so that we don't try to match a device profile again
            # regardless of whether the platform is supported or not
            string_ids.add(event.device.id_string)

            device_info = build_device_info_from_event(profile_registry, event)
            device_id = build_device_id_from_device_info(device_info)
            platform_config = profile_registry.get_platform_config(device_info[CONF_PROFILE_NAME], platform)
            if not platform_config:
                _LOGGER.debug("Device %s does not support platform %s", event.device.id_string, platform)
                return

            async_add_entities(
                builder(device_id, platform_config, event.data, entry_data.get(CONF_VERBOSE_MODE, False))
            )

        config_entry.async_on_unload(
            async_dispatcher_connect(hass, SIGNAL_RFPLAYER_EVENT, _update)  # type: ignore[has-type]
        )


class RfDeviceEntity(RestoreEntity):
    """Represents a RfPlayer device.

    Contains the common logic for RfPlayer lights and switches.
    """

    _attr_assumed_state = True
    _attr_has_entity_name = True
    _attr_should_poll = False
    _device_id: RfDeviceId
    _event_data: RfPlayerEventData | None

    def __init__(self, device_id: RfDeviceId, name: str, event_data: RfPlayerEventData | None, verbose: bool) -> None:
        """Initialize the device."""
        self._attr_device_info = DeviceInfo(
            identifiers=get_identifiers_from_device_id(device_id),
            manufacturer=device_id.protocol,
            model=device_id.model,
            name=f"{device_id.protocol} {device_id.model} {device_id.address}"
            if device_id.model
            else f"{device_id.protocol} {device_id.address}",
        )
        self.name = name
        self._attr_unique_id = slugify.slugify(f"{device_id.id_string}.{name}")
        self._event_data = event_data
        self._device_id = device_id
        self.entity_id = f"{DOMAIN}.{device_id.id_string}.{name}"
        self._verbose = verbose

    async def async_added_to_hass(self) -> None:
        """Restore RfPlayer device from last event stored in attributes."""
        if self._event_data is None and (old_state := await self.async_get_last_state()) is not None:
            json_event_data = cast(str, old_state.attributes.get(ATTR_EVENT_DATA))
            self._event_data = json.loads(json_event_data) if json_event_data else None

        if self._event_data:
            self._apply_event(self._event_data)

        self.async_on_remove(
            async_dispatcher_connect(  # type: ignore[has-type]
                self.hass, SIGNAL_RFPLAYER_EVENT, self._handle_event
            )
        )

        self.async_on_remove(
            async_dispatcher_connect(  # type: ignore[has-type]
                self.hass, SIGNAL_RFPLAYER_AVAILABILITY, self._handle_availability
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the device state attributes."""
        if not self._event_data:
            return None
        return {ATTR_EVENT_DATA: json.dumps(self._event_data)}

    def _event_applies(self, event: RfDeviceEvent) -> bool:
        """Check if event applies to me."""
        if self._group_event(event):
            return (event.device.protocol == self._device_id.protocol) and (
                event.device.group_code == self._device_id.group_code
            )
        return event.device.id_string == self._device_id.id_string

    def _group_event(self, event: RfDeviceEvent) -> bool:
        return False

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply a received event."""
        self._event_data = event_data
        return True

    @callback
    def _handle_event(self, event: RfDeviceEvent) -> None:
        """Check if event applies to me and update."""
        if not self._event_applies(event):
            return

        if self._apply_event(event.data):
            _LOGGER.debug("%s updated", self.entity_id)
            self.async_write_ha_state()
        elif self._verbose:
            _LOGGER.debug("%s not updated", self.entity_id)

    @callback
    def _handle_availability(self, available: bool) -> None:
        self._attr_available = available
        if self._verbose:
            _LOGGER.debug("%s availability updated %s", self.entity_id, str(available))
        self.async_write_ha_state()

    async def _send_command(self, command: str):
        client = cast(RfPlayerClient, self.hass.data[DOMAIN][RFPLAYER_CLIENT])
        await self.hass.async_add_executor_job(client.send_raw_command, command)

    def _command_parameters(self, **kwargs) -> dict:
        params = {
            "protocol": self._device_id.protocol,
            "address": self._device_id.address,
            "group_code": self._device_id.group_code,
            "unit_code": self._device_id.unit_code,
        }
        params.update(kwargs)
        return params
