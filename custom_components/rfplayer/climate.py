"""Support for RfPlayer lights."""

import logging
from typing import cast

from custom_components.rfplayer.const import COMMAND_OFF_LIST, COMMAND_ON_LIST
from custom_components.rfplayer.device_profiles import (
    AnyRfpPlatformConfig,
    ClimateEventTypes,
    RfpClimateConfig,
    RfpPlatformConfig,
)
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.components.climate import (
    ATTR_PRESET_MODE,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode,
    UnitOfTemperature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> ClimateEntityDescription:
    assert isinstance(config, RfpClimateConfig)
    return ClimateEntityDescription(key=config.name)


def _builder(
    device: RfDeviceId, platform_config: list[AnyRfpPlatformConfig], event_data: RfPlayerEventData | None, verbose: bool
) -> list[Entity]:
    return [
        RfPlayerClimate(
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
        Platform.CLIMATE,
        _builder,
    )


class RfPlayerClimate(RfDeviceEntity, ClimateEntity):
    """A representation of a RfPlayer climate device."""

    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
    )
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_max_temp = 30.0
    _attr_min_temp = 0.0
    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    def __init__(
        self,
        device: RfDeviceId,
        entity_description: ClimateEntityDescription,
        platform_config: RfpPlatformConfig,
        event_data: RfPlayerEventData | None,
        verbose: bool,
    ) -> None:
        """Initialize the RfPlayer light."""
        super().__init__(device_id=device, name=platform_config.name, event_data=event_data, verbose=verbose)
        self.entity_description = entity_description
        assert isinstance(platform_config, RfpClimateConfig)
        self._config = cast(RfpClimateConfig, platform_config)
        self._event_data = event_data
        self._attr_preset_modes = list(self._config.preset_modes.values())
        self._attr_preset_mode = None

    async def async_added_to_hass(self) -> None:
        """Restore climate device state."""
        await super().async_added_to_hass()

        if self._event_data is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._attr_is_on = old_state.state == STATE_ON
                if preset_mode := old_state.attributes.get(ATTR_PRESET_MODE):
                    self._attr_preset_mode = preset_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            _LOGGER.debug("set %s to heat mode", self.entity_id)
            await self._send_command(
                self._config.make_cmd_turn_on(**self._command_parameters(preset_mode=self._attr_preset_mode))
            )
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()
        elif hvac_mode == HVACMode.OFF:
            _LOGGER.debug("set %s off mode", self.entity_id)
            await self._send_command(
                self._config.make_cmd_turn_off(**self._command_parameters(preset_mode=self._attr_preset_mode))
            )
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()
        else:
            _LOGGER.warning("Unsupported HVAC mode %s", hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        _LOGGER.debug("set %s to preset %s", self.entity_id, preset_mode)
        await self._send_command(self._config.make_cmd_set_mode(**self._command_parameters(preset_mode=preset_mode)))
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        event_code = self._config.event_code.get_value(event_data)
        if event_code not in self._config.event_types:
            _LOGGER.debug("Ignore unsupported event code %s", event_code)
            return False

        event_type = self._config.event_types[event_code]
        if event_type in (ClimateEventTypes.STATE, ClimateEventTypes.ALL):
            state = self._config.state.get_value(event_data)
            if not state:
                _LOGGER.warning("Missing state value")
                return False

            command = state.lower()
            if command in COMMAND_ON_LIST:
                self._attr_is_on = True
            elif command in COMMAND_OFF_LIST:
                self._attr_is_on = False
            else:
                _LOGGER.info("Unsupported climate state %s", command)

        if event_type in (ClimateEventTypes.PRESET_MODE, ClimateEventTypes.ALL):
            preset_code = self._config.preset_mode.get_value(event_data)
            if not preset_code:
                _LOGGER.warning("Missing preset mode value")
                return False

            if preset_code not in self._config.preset_modes:
                _LOGGER.info("Unsupported preset code %s", preset_code)
                return False

            self._attr_preset_mode = self._config.preset_modes[preset_code]

        return True
