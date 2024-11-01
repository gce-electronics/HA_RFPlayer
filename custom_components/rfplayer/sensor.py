"""Support for RfPlayer sensors."""

import logging
from typing import cast

from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpPlatformConfig, RfpSensorConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> SensorEntityDescription:
    assert isinstance(config, RfpSensorConfig)
    return SensorEntityDescription(
        key=config.name,
        device_class=SensorDeviceClass(config.device_class) if config.device_class else None,
        state_class=SensorStateClass(config.state_class) if config.state_class else SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=config.event_unit(event_data),
    )


def _builder(
    device: RfDeviceId, platform_config: list[AnyRfpPlatformConfig], event_data: RfPlayerEventData | None, verbose: bool
) -> list[Entity]:
    return [
        RfPlayerSensor(
            device, _get_entity_description(config, event_data), config, event_data=event_data, verbose=verbose
        )
        for config in platform_config
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up config rf device entry."""

    await async_setup_platform_entry(
        hass,
        config_entry,
        async_add_entities,
        Platform.SENSOR,
        _builder,
    )


class RfPlayerSensor(RfDeviceEntity, SensorEntity):
    """A representation of a RfPlayer binary sensor.

    Since all repeated events have meaning, these types of sensors
    need to have force update enabled.
    """

    _attr_force_update = True
    _attr_name = None

    def __init__(
        self,
        device: RfDeviceId,
        entity_description: SensorEntityDescription,
        platform_config: RfpPlatformConfig,
        event_data: RfPlayerEventData | None,
        verbose: bool,
    ) -> None:
        """Initialize the RfPlayer sensor."""
        super().__init__(device_id=device, name=platform_config.name, event_data=event_data, verbose=verbose)
        self.entity_description = entity_description
        assert isinstance(platform_config, RfpSensorConfig)
        self._config = cast(RfpSensorConfig, platform_config)
        self._event_data = event_data

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        str_value = self._config.state.get_value(event_data)
        if not str_value:
            _LOGGER.info("Missing sensor value")
            return False

        try:
            self._attr_native_value = float(str_value)
        except ValueError:
            _LOGGER.info("Ignoring non numeric value %s", str_value)
            return False

        return True
