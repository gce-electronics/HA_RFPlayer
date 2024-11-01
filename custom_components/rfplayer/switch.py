"""Support for RfPlayer lights."""

import logging
from typing import Any, cast

from custom_components.rfplayer.const import COMMAND_GROUP_LIST, COMMAND_OFF_LIST, COMMAND_ON_LIST
from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpPlatformConfig, RfpSwitchConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> SwitchEntityDescription:
    assert isinstance(config, RfpSwitchConfig)
    return SwitchEntityDescription(key=config.name)


def _builder(
    device: RfDeviceId, platform_config: list[AnyRfpPlatformConfig], event_data: RfPlayerEventData | None, verbose: bool
) -> list[Entity]:
    return [
        RfPlayerSwitch(
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
        Platform.SWITCH,
        _builder,
    )


class RfPlayerSwitch(RfDeviceEntity, SwitchEntity):
    """A representation of a RF switch device."""

    _attr_name = None

    def __init__(
        self,
        device: RfDeviceId,
        entity_description: SwitchEntityDescription,
        platform_config: RfpPlatformConfig,
        event_data: RfPlayerEventData | None,
        verbose: bool,
    ) -> None:
        """Initialize the RfPlayer switch."""
        super().__init__(device_id=device, name=platform_config.name, event_data=event_data, verbose=verbose)
        self.entity_description = entity_description
        assert isinstance(platform_config, RfpSwitchConfig)
        self._config = cast(RfpSwitchConfig, platform_config)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        _LOGGER.debug("turn on %s", self.entity_id)
        await self._send_command(self._config.make_cmd_turn_on(**self._command_parameters()))
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        _LOGGER.debug("turn off %s", self.entity_id)
        await self._send_command(self._config.make_cmd_turn_off(**self._command_parameters()))
        self._attr_is_on = False
        self.async_write_ha_state()

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        status = self._config.status.get_value(event_data)
        command = status.lower() if status else None
        if command in COMMAND_ON_LIST:
            self._attr_is_on = True
        elif command in COMMAND_OFF_LIST:
            self._attr_is_on = False
        else:
            _LOGGER.info("Unsupported switch command %s", command)
            return False

        return True

    def _group_event(self, event: RfDeviceEvent) -> bool:
        value = self._config.status.get_value(event.data)
        return value.lower() in COMMAND_GROUP_LIST if value else False
