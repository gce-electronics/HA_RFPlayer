"""Support for RfPlayer binary sensors."""

import logging

from custom_components.rfplayer.const import COMMAND_GROUP_LIST, COMMAND_OFF_LIST, COMMAND_ON_LIST
from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpSensorConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig,
) -> BinarySensorEntityDescription:
    return BinarySensorEntityDescription(
        key=config.name,
        device_class=BinarySensorDeviceClass(config.device_class) if config.device_class else None,
        entity_category=config.category,
    )


def _builder(
    config_entry: RfPlayerConfigEntry,
    device_entry: dr.DeviceEntry,
    rf_device_id: RfDeviceId,
    platform_configs: list[AnyRfpPlatformConfig],
    event_data: RfPlayerEventData | None,
) -> list[RfDeviceEntity]:
    return [
        RfPlayerBinarySensor(config_entry, device_entry, rf_device_id, config, event_data=event_data)
        for config in platform_configs
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RfPlayerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up config rf device entry."""

    await async_setup_platform_entry(
        hass,
        config_entry,
        async_add_entities,
        Platform.BINARY_SENSOR,
        _builder,
    )


class RfPlayerBinarySensor(RfDeviceEntity, BinarySensorEntity):
    """A representation of a RfPlayer binary sensor."""

    _attr_force_update = True
    _attr_name = None

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config_entry: RfPlayerConfigEntry,
        device_entry: dr.DeviceEntry,
        rf_device_id: RfDeviceId,
        platform_config: AnyRfpPlatformConfig,
        event_data: RfPlayerEventData | None,
    ) -> None:
        """Initialize the RfPlayer sensor."""
        super().__init__(
            config_entry=config_entry,
            device_entry=device_entry,
            rf_device_id=rf_device_id,
            entity_name=platform_config.name,
            event_data=event_data,
        )
        self.entity_description = _get_entity_description(platform_config)
        assert isinstance(platform_config, RfpSensorConfig)
        self._config = platform_config
        self._event_data = event_data

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        state = self._config.state.get_value(event_data)
        command = state.lower() if state else None
        if command in COMMAND_ON_LIST:
            self._attr_is_on = True
        elif command in COMMAND_OFF_LIST:
            self._attr_is_on = False
        else:
            _LOGGER.info("Unsupported binary sensor command %s", command)
            return False

        return True

    def _group_event(self, event: RfDeviceEvent) -> bool:
        value = self._config.state.get_value(event.data)
        return value.lower() in COMMAND_GROUP_LIST if value else False
