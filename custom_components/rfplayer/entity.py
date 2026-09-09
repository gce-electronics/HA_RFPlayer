"""Support for RF devices."""

from collections.abc import Callable
from functools import partial
import json
import logging
from typing import cast

from custom_components.rfplayer.device_profiles import (
    UNDEFINED_PROFILE,
    AnyRfpPlatformConfig,
    ProfileRegistry,
    async_get_profile_registry,
)
from custom_components.rfplayer.helpers import (
    build_device_id_from_device_info,
    build_device_info_from_event,
    build_event_data_from_device_info,
    get_identifiers_from_device_id,
)
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.const import CONF_DEVICES, CONF_PROFILE_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    ATTR_EVENT_DATA,
    CONF_AUTOMATIC_ADD,
    CONF_VERBOSE_MODE,
    SIGNAL_RFPLAYER_AVAILABILITY,
    SIGNAL_RFPLAYER_EVENT,
)

_LOGGER = logging.getLogger(__name__)

type RfDeviceEntityBuilder = Callable[
    [
        RfPlayerConfigEntry,
        dr.DeviceEntry,
        RfDeviceId,
        list[AnyRfpPlatformConfig],
        RfPlayerEventData | None,
    ],
    list[RfDeviceEntity],
]


async def async_setup_platform_entry(
    hass: HomeAssistant,
    config_entry: RfPlayerConfigEntry,
    async_add_entities: AddEntitiesCallback,
    platform: Platform,
    builder: RfDeviceEntityBuilder,
) -> None:
    """Set up config entry."""
    entry_data = config_entry.data
    verbose = entry_data.get(CONF_VERBOSE_MODE, False)
    automatic_add = entry_data.get(CONF_AUTOMATIC_ADD, False)

    device_registry = dr.async_get(hass)
    profile_registry = await async_get_profile_registry(hass, verbose)

    entity_manager = RfPlayerPlatformEntityManager(config_entry, device_registry, profile_registry, platform, builder)
    entity_manager.add_config_entities(async_add_entities, verbose)
    if automatic_add:
        config_entry.async_on_unload(
            async_dispatcher_connect(
                hass,
                SIGNAL_RFPLAYER_EVENT,
                partial(
                    entity_manager.async_listen_for_new_entities,
                    async_add_entities=async_add_entities,
                    verbose=verbose,
                ),
            )  # type: ignore[has-type]
        )


class RfDeviceEntity(RestoreEntity):
    """Represents a RfPlayer device.

    Contains the common logic for RfPlayer lights and switches.
    """

    _attr_assumed_state = True
    _attr_has_entity_name = True
    _attr_should_poll = False
    rf_device_id: RfDeviceId
    _event_data: RfPlayerEventData | None

    def __init__(
        self,
        config_entry: RfPlayerConfigEntry,
        device_entry: dr.DeviceEntry,
        rf_device_id: RfDeviceId,
        profile_name: str,
        event_data: RfPlayerEventData | None,
    ) -> None:
        """Initialize the device.

        profile_name must be a stable identifier from the device profile to ensure correct behavior
        for unique_id generation and device registry. It is not intended to be user modified.
        """
        self.gateway = config_entry.runtime_data.gateway
        self.device_entry = device_entry
        self._attr_name = profile_name
        self._attr_unique_id = slugify(f"{rf_device_id.id_string}_{profile_name}")
        # HA will generate the entity_id
        self._event_data = event_data
        self.rf_device_id = rf_device_id
        self._verbose = config_entry.data.get(CONF_VERBOSE_MODE, False)

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
            return (event.device.protocol == self.rf_device_id.protocol) and (
                event.device.group_code == self.rf_device_id.group_code
            )
        return event.device.id_string == self.rf_device_id.id_string

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

    async def _send_command(self, command: str) -> None:
        """Send a command to the RfPlayer gateway."""
        await self.gateway.client.send_raw_command(command)

    def _command_parameters(self, **kwargs) -> dict:
        params = {
            "protocol": self.rf_device_id.protocol,
            "address": self.rf_device_id.address,
            "group_code": self.rf_device_id.group_code,
            "unit_code": self.rf_device_id.unit_code,
        }
        params.update(kwargs)
        return params


class RfPlayerPlatformEntityManager:
    """Manages RfPlayer entities for a given platform."""

    def __init__(
        self,
        config_entry: RfPlayerConfigEntry,
        device_registry: dr.DeviceRegistry,
        profile_registry: ProfileRegistry,
        platform: Platform,
        builder: RfDeviceEntityBuilder,
    ) -> None:
        """Initialize the entity manager."""
        self.config_entry = config_entry
        self.device_registry = device_registry
        self.profile_registry = profile_registry
        self.platform = platform
        self.builder = builder
        self.rf_device_ids: set[str] = set()

    def add_config_entities(self, async_add_entities: AddEntitiesCallback, verbose: bool) -> None:
        """Add entities to the manager."""
        entities = []
        entry_data = self.config_entry.data
        for id_string, device_info in entry_data[CONF_DEVICES].items():
            if id_string in self.rf_device_ids:
                _LOGGER.info(
                    "Device %s already configured for platform %s",
                    id_string,
                    self.platform,
                )
                continue

            event_data = build_event_data_from_device_info(device_info)
            self.build_entities(device_info, event_data, async_add_entities, verbose)

        async_add_entities(entities)

    async def async_listen_for_new_entities(
        self, event: RfDeviceEvent, async_add_entities: AddEntitiesCallback, verbose: bool
    ):
        """Listen for new entities to be added to the manager."""
        if event.device.id_string in self.rf_device_ids:
            return

        # Add the device to the list of already processed devices
        # so that we don't try to match a device profile again
        # regardless of whether the platform is supported or not
        self.rf_device_ids.add(event.device.id_string)

        device_info = build_device_info_from_event(self.profile_registry, event)

        self.build_entities(device_info, event.data, async_add_entities, verbose)

    def build_entities(
        self,
        device_info: dict,
        event_data: RfPlayerEventData | None,
        async_add_entities: AddEntitiesCallback,
        verbose: bool,
    ) -> None:
        """Build entities for a given device info and event data."""
        rf_device_id = build_device_id_from_device_info(device_info)
        profile_name = device_info.get(CONF_PROFILE_NAME, UNDEFINED_PROFILE)
        platform_config = self.profile_registry.get_platform_config(profile_name, self.platform)
        if not platform_config:
            _LOGGER.debug("Device %s does not support platform %s", rf_device_id.id_string, self.platform)
            return

        device_entry = self.device_registry.async_get_or_create(  # TODO: need to run this in the hass event loop
            config_entry_id=self.config_entry.entry_id,
            identifiers={get_identifiers_from_device_id(rf_device_id)},
            manufacturer=rf_device_id.protocol,
            model=rf_device_id.model,
            name=f"{rf_device_id.protocol} {rf_device_id.model} {rf_device_id.address}"
            if rf_device_id.model
            else f"{rf_device_id.protocol} {rf_device_id.address}",
            # TODO add via_device to link to the gateway device entry
        )
        entities = self.builder(self.config_entry, device_entry, rf_device_id, platform_config, event_data)
        async_add_entities(entities)
