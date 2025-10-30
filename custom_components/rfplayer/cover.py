"""Support for RfPlayer covers."""

import logging
from typing import Any, cast

from custom_components.rfplayer.device_profiles import AnyRfpPlatformConfig, RfpCoverConfig, RfpPlatformConfig
from custom_components.rfplayer.entity import RfDeviceEntity, async_setup_platform_entry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.components.cover import CoverEntity, CoverEntityDescription, CoverEntityFeature, CoverState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


def _get_entity_description(
    config: AnyRfpPlatformConfig, event_data: RfPlayerEventData | None
) -> CoverEntityDescription:
    assert isinstance(config, RfpCoverConfig)
    return CoverEntityDescription(key=config.name)


def _builder(
    device: RfDeviceId, platform_config: list[AnyRfpPlatformConfig], event_data: RfPlayerEventData | None, verbose
) -> list[Entity]:
    return [
        RfPlayerCover(
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
        Platform.COVER,
        _builder,
    )


class RfPlayerCover(RfDeviceEntity, CoverEntity):
    """A representation of a RF cover device."""

    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
    _attr_is_closed = False  # Assume initial state is open
    _attr_name = None

    def __init__(
        self,
        device: RfDeviceId,
        entity_description: CoverEntityDescription,
        platform_config: RfpPlatformConfig,
        event_data: RfPlayerEventData | None,
        verbose: bool,
    ) -> None:
        """Initialize the RfPlayer cover."""
        super().__init__(device_id=device, name=platform_config.name, event_data=event_data, verbose=verbose)
        self.entity_description = entity_description
        assert isinstance(platform_config, RfpCoverConfig)
        self._config = cast(RfpCoverConfig, platform_config)
        self._event_data = event_data
        if self._config.cmd_stop:
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
