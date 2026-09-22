"""Support for RfPlayer sensors."""

import logging

from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpSensorConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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
    config_entry: RfPlayerConfigEntry,
    device_entry: dr.DeviceEntry,
    rf_device_id: RfDeviceId,
    platform_config: list[AnyRfpPlatformConfig],
    event_data: RfPlayerEventData | None,
) -> list[RfDeviceEntity]:
    return [
        RfPlayerSensor(config_entry, device_entry, rf_device_id, config, event_data=event_data)
        for config in platform_config
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
        self.entity_description = _get_entity_description(platform_config, event_data)
        assert isinstance(platform_config, RfpSensorConfig)
        self._config = platform_config
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
