"""Support for Rfplayer number."""
import logging

from homeassistant.components.number import (
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RfplayerDevice
from .const import DOMAIN, RFPLAYER_PROTOCOL
from .rflib.rfpprotocol import RfplayerProtocol

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Rfplayer platform."""
    _LOGGER.debug("Add jamming number entity")
    async_add_entities([RfplayerJammingNumber()])


class RfplayerJammingNumber(RfplayerDevice, RestoreNumber):
    """Representation of a Rfplayer jamming number setting entity."""

    entity_description = NumberEntityDescription(
        key="jamming_level",
        translation_key="jamming_level",
        entity_category=EntityCategory.CONFIG,
    )
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_native_value: float | None = None
    _attr_mode = NumberMode.SLIDER

    def __init__(self) -> None:
        """Init the jamming number rfplayer entity."""
        super().__init__(
            protocol="JAMMING",
            unique_id="jamming_level",
            name="Jamming detection level",
        )

    async def async_added_to_hass(self) -> None:
        """Restore RFPlayer device state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (
            last_number_data := await self.async_get_last_number_data()
        ):
            if last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                self._attr_native_value = last_number_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        value = int(max(0, min(10, value)))
        rfplayer: RfplayerProtocol = self.hass.data[DOMAIN][RFPLAYER_PROTOCOL]
        await rfplayer.send_command_ack(command=str(value), protocol=self._protocol)
        self._attr_native_value = value
        self.async_write_ha_state()
