"""Support for RfPlayer lights."""

import logging
from typing import Any

from custom_components.rfplayer.const import COMMAND_GROUP_LIST, COMMAND_OFF_LIST, COMMAND_ON_LIST
from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpSwitchConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> SwitchEntityDescription:
    assert isinstance(config, RfpSwitchConfig)
    return SwitchEntityDescription(key=config.name)


def _builder(
    config_entry: RfPlayerConfigEntry,
    device_entry: dr.DeviceEntry,
    rf_device_id: RfDeviceId,
    platform_config: list[AnyRfpPlatformConfig],
    event_data: RfPlayerEventData | None,
) -> list[RfDeviceEntity]:
    return [
        RfPlayerSwitch(config_entry, device_entry, rf_device_id, config, event_data=event_data)
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
        Platform.SWITCH,
        _builder,
    )


class RfPlayerSwitch(RfDeviceEntity, SwitchEntity):
    """A representation of a RF switch device."""

    _attr_name = None

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config_entry: RfPlayerConfigEntry,
        device_entry: dr.DeviceEntry,
        rf_device_id: RfDeviceId,
        platform_config: AnyRfpPlatformConfig,
        event_data: RfPlayerEventData | None,
    ) -> None:
        """Initialize the RfPlayer switch."""
        super().__init__(
            config_entry=config_entry,
            device_entry=device_entry,
            rf_device_id=rf_device_id,
            entity_name=platform_config.name,
            event_data=event_data,
        )
        self.entity_description = _get_entity_description(platform_config, event_data)
        assert isinstance(platform_config, RfpSwitchConfig)
        self._config = platform_config

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
