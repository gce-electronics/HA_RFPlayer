"""Support for Rfplayer number."""
import logging

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EVENT_KEY_COMMAND, RfplayerDevice
from .const import DATA_ENTITY_LOOKUP, DOMAIN, EVENT_KEY_ID, RFPLAYER_PROTOCOL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Rfplayer platform."""
    _LOGGER.debug("Add jamming number entity")
    async_add_entities([RfplayerJammingNumber()])


class RfplayerJammingNumber(RfplayerDevice, RestoreNumber):
    """Representation of a Rfplayer jamming number setting entity."""

    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_mode = NumberMode.SLIDER

    def __init__(self) -> None:
        """Init the number rfplayer entity."""
        self._state: int | None = None
        super().__init__("JAMMING")

    async def async_added_to_hass(self) -> None:
        """Restore RFPlayer device state."""
        await super().async_added_to_hass()

        self.hass.data[DOMAIN][DATA_ENTITY_LOOKUP][EVENT_KEY_COMMAND][
            self._initial_event[EVENT_KEY_ID]
        ] = self.entity_id

        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._state = int(old_state.state)

    @callback
    def _handle_event(self, event):
        self._state = int(event["command"])

    @property
    def value(self):
        """Return the current setting."""
        return self._state

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        rfplayer = self.hass.data[DOMAIN][RFPLAYER_PROTOCOL]
        await rfplayer.send_command_ack(command=int(value), protocol=self._protocol)
        self._state = int(value)
