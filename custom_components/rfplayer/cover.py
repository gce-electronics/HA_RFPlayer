"""Support for RfPlayer covers."""

import logging
from typing import Any

from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpCoverConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.components.cover import CoverEntity, CoverEntityDescription, CoverEntityFeature, CoverState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> CoverEntityDescription:
    assert isinstance(config, RfpCoverConfig)
    return CoverEntityDescription(key=config.name)


def _builder(
    config_entry: RfPlayerConfigEntry,
    device_entry: dr.DeviceEntry,
    rf_device_id: RfDeviceId,
    platform_config: list[AnyRfpPlatformConfig],
    event_data: RfPlayerEventData | None,
) -> list[RfDeviceEntity]:
    return [RfPlayerCover(config_entry, device_entry, rf_device_id, config, event_data) for config in platform_config]


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
        Platform.COVER,
        _builder,
    )


class RfPlayerCover(RfDeviceEntity, CoverEntity):
    """A representation of a RF cover device."""

    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
    _attr_is_closed = False  # Assume initial state is open
    _attr_name = None

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config_entry: RfPlayerConfigEntry,
        device_entry: dr.DeviceEntry,
        rf_device_id: RfDeviceId,
        platform_config: AnyRfpPlatformConfig,
        event_data: RfPlayerEventData | None,
    ) -> None:
        """Initialize the RfPlayer cover."""
        super().__init__(
            config_entry=config_entry,
            device_entry=device_entry,
            rf_device_id=rf_device_id,
            profile_name=platform_config.name,
            event_data=event_data,
        )
        self.entity_description = _get_entity_description(platform_config, event_data)
        assert isinstance(platform_config, RfpCoverConfig)
        self._config = platform_config
        self._event_data = event_data
        if self._config.cmd_stop:
            if self._attr_supported_features is None:
                self._attr_supported_features = CoverEntityFeature.STOP
            else:
                self._attr_supported_features |= CoverEntityFeature.STOP

    async def async_added_to_hass(self) -> None:
        """Restore device state."""
        await super().async_added_to_hass()

        if self._event_data is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._attr_is_closed = old_state.state != CoverState.OPEN

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        _LOGGER.debug("open %s cover", self.entity_id)
        await self._send_command(self._config.make_cmd_open(**self._command_parameters()))
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        _LOGGER.debug("close %s cover", self.entity_id)
        await self._send_command(self._config.make_cmd_close(**self._command_parameters()))
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop cover."""
        assert self._config.cmd_stop
        _LOGGER.debug("stop %s cover", self.entity_id)
        await self._send_command(self._config.make_cmd_stop(**self._command_parameters()))
        self._attr_is_closed = False  # Assume open if stopped
        self.async_write_ha_state()

    def _apply_event(self, event_data: RfPlayerEventData) -> bool:
        """Apply command from RfPlayer."""
        super()._apply_event(event_data)

        if not self._config.state:
            _LOGGER.debug("Device profile doesn't support cover state")
            return False

        state_code = self._config.state.get_value(event_data)
        if state_code not in self._config.states:
            _LOGGER.debug("Ignore unsupported state code %s", state_code)
            return False

        state = self._config.states[state_code]
        if state == CoverState.OPEN:
            self._attr_is_closed = False
        elif state == CoverState.CLOSED:
            self._attr_is_closed = True
        else:
            _LOGGER.warning("Unsupported cover state %s", state)
            return False

        return True
