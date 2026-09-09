"""Support for RfPlayer lights."""

import logging
from typing import Any

from custom_components.rfplayer.const import COMMAND_GROUP_LIST, COMMAND_OFF_LIST, COMMAND_ON_LIST
from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpLightConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.components.light import ATTR_BRIGHTNESS, STATE_ON, ColorMode, LightEntity, LightEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> LightEntityDescription:
    assert isinstance(config, RfpLightConfig)
    return LightEntityDescription(key=config.name)


def _builder(
    config_entry: RfPlayerConfigEntry,
    device_entry: dr.DeviceEntry,
    rf_device_id: RfDeviceId,
    platform_config: list[AnyRfpPlatformConfig],
    event_data: RfPlayerEventData | None,
) -> list[RfDeviceEntity]:
    return [RfPlayerLight(config_entry, device_entry, rf_device_id, config, event_data) for config in platform_config]


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
        Platform.LIGHT,
        _builder,
    )


class RfPlayerLight(RfDeviceEntity, LightEntity):
    """A representation of a RF light device."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_brightness: int = 0
    _attr_name = None

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config_entry: RfPlayerConfigEntry,
        device_entry: dr.DeviceEntry,
        rf_device_id: RfDeviceId,
        platform_config: AnyRfpPlatformConfig,
        event_data: RfPlayerEventData | None,
    ) -> None:
        """Initialize the RfPlayer light."""
        super().__init__(
            config_entry=config_entry,
            device_entry=device_entry,
            rf_device_id=rf_device_id,
            profile_name=platform_config.name,
            event_data=event_data,
        )
        self.entity_description = _get_entity_description(platform_config, event_data)
        assert isinstance(platform_config, RfpLightConfig)
        self._config = platform_config
        self._event_data = event_data

    async def async_added_to_hass(self) -> None:
        """Restore light device state (On/Off)."""
        await super().async_added_to_hass()

        if self._event_data is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._attr_is_on = old_state.state == STATE_ON
                if brightness := old_state.attributes.get(ATTR_BRIGHTNESS):
                    self._attr_brightness = int(brightness)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        self._attr_is_on = True
        if brightness is None or not self._config.cmd_set_level:
            _LOGGER.debug("turn on %s", self.entity_id)
            await self._send_command(self._config.make_cmd_turn_on(**self._command_parameters()))
            self._attr_brightness = 255
        else:
            brightness_pct = brightness * 100 // 255
            _LOGGER.debug("turn on %s with brightness %f", self.entity_id, brightness_pct)
            await self._send_command(
                self._config.make_cmd_set_level(**self._command_parameters(brightness=brightness_pct))
            )
            self._attr_brightness = brightness

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        _LOGGER.debug("turn off %s", self.entity_id)
        await self._send_command(self._config.make_cmd_turn_off(**self._command_parameters()))
        self._attr_is_on = False
        self._attr_brightness = 0
        self.async_write_ha_state()

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        status = self._config.status.get_value(event_data)
        command = status.lower() if status else None
        if command in COMMAND_ON_LIST:
            self._attr_is_on = True
            self._attr_brightness = 255
        elif command in COMMAND_OFF_LIST:
            self._attr_is_on = False
            self._attr_brightness = 0
        else:
            # Bright / Dim not supported cause we know neither the starting point not the increment value
            _LOGGER.info("Unsupported light command %s", command)
            return False

        return True

    def _group_event(self, event: RfDeviceEvent) -> bool:
        value = self._config.status.get_value(event.data)
        return value.lower() in COMMAND_GROUP_LIST if value else False
