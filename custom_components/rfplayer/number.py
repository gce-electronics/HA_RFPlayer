"""Support for Rfplayer number."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory

from . import EVENT_KEY_COMMAND, RfplayerDevice
from .const import DATA_ENTITY_LOOKUP, DOMAIN, EVENT_KEY_ID, RFPLAYER_PROTOCOL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Rfplayer platform."""
    _LOGGER.debug("Add jamming number entity")
    async_add_entities([RfplayerJammingNumber()])


class RfplayerJammingNumber(RfplayerDevice, NumberEntity):
    """Representation of a Rfplayer jamming number setting entity."""

    def __init__(self):
        """Init the number rfplayer entity."""
        self._attr_native_min_value = 0
        self._attr_native_max_value = 10
        self._attr_native_mode = "slider"
        self._attr_native_entity_category = EntityCategory.CONFIG
        super().__init__("JAMMING", device_id=0, name="Jamming detection level")

    async def async_added_to_hass(self):
        """Restore RFPlayer device state."""
        await super().async_added_to_hass()
        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._state = old_state.state

    @callback
    def _handle_event(self, event):
        self._state = int(event["value"])

    @property
    def native_value(self):
        """Return the current setting."""
        return self._state

    async def async_set_native_value(self, value) -> None:
        """Update the current value."""
        rfplayer = self.hass.data[DOMAIN][RFPLAYER_PROTOCOL]
        await rfplayer.send_command_ack(command=int(value), protocol=self._protocol)
        self._state = value
