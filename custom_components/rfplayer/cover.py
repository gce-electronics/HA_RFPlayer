"""Support for Rfplayer cover."""
import logging

from homeassistant.components.cover import (
    DOMAIN as PLATFORM_COVER,
    CoverEntity,
    ATTR_POSITION, ATTR_CURRENT_POSITION,
    STATE_OPEN, STATE_OPENING, STATE_CLOSED, STATE_CLOSING
)
from homeassistant.const import CONF_DEVICE_ID, CONF_DEVICES, CONF_PROTOCOL
from homeassistant.core import callback

from . import DATA_DEVICE_REGISTER, EVENT_KEY_COMMAND, RfplayerDevice
from .const import (
    COMMAND_OFF,
    COMMAND_ON,
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_ADDRESS,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_KEY_ID,
)

_LOGGER = logging.getLogger(__name__)

ICON_OPEN = "mdi:blinds-open"
ICON_CLOSE = "mdi:blinds"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Rfplayer platform."""
    config = entry.data
    options = entry.options

    async def add_new_device(device_info):
        """Check if device is known, otherwise create device entity."""
        # create entity
        device = RfplayerCover(
            protocol=device_info[CONF_PROTOCOL],
            device_address=device_info.get(CONF_DEVICE_ADDRESS),
            device_id=device_info.get(CONF_DEVICE_ID),
            initial_event=device_info,
            position=0,
        )
        _LOGGER.debug("Add cover entity %s", device_info)
        async_add_entities([device])

    if CONF_DEVICES in config:
        for device_id, device_info in config[CONF_DEVICES].items():
            if EVENT_KEY_COMMAND in device_info:
                await add_new_device(device_info)

    if options.get(CONF_AUTOMATIC_ADD, config[CONF_AUTOMATIC_ADD]):
        hass.data[DOMAIN][DATA_DEVICE_REGISTER][EVENT_KEY_COMMAND] = add_new_device


class RfplayerCover(RfplayerDevice, CoverEntity):
    """Representation of a Rfplayer sensor."""


    async def async_added_to_hass(self):
        """Restore RFPlayer device state (ON/OFF)."""
        await super().async_added_to_hass()

        self.hass.data[DOMAIN][DATA_ENTITY_LOOKUP][EVENT_KEY_COMMAND][
            self._initial_event[EVENT_KEY_ID]
        ] = self.entity_id

        """
        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._state = old_state.state == COMMAND_ON
        """
        state = await self.async_get_last_state()
        if state:
            _LOGGER.debug("last state of %s = %s", self._name, state)
            self._position = state.attributes.get('current_position', 50)

    @callback
    def _handle_event(self, event):
        command = event["command"]
        if command in [COMMAND_ON, "ALLON"]:
            self._state = True
        elif command in [COMMAND_OFF, "ALLOFF"]:
            self._state = False

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        _LOGGER.debug("set position %s = %s", str(self), position)

        #diff = self._position - position
        #if diff > 0:
        #    _LOGGER.debug("Close")
            #self._operate_cover(self._relay_down, diff * self._delay_time / 100)
        #elif diff < 0:
        #    _LOGGER.debug("Open")
            #self._operate_cover(self._relay_up, abs(diff) * self._delay_time / 100)
        #self._position = position
        self.async_schedule_update_ha_state(True)


    @property
    def should_poll(self):
        """Can't poll anything."""
        return False

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return "window" 

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._closed

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self.is_opening

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self._async_send_command(COMMAND_ON)
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self._async_send_command(COMMAND_OFF)
        self._state = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("async_close_cover (%s)", str(self))
        await self.async_set_cover_position(position=0)

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("async_open_cover (%s)", self._relay_up)
        await self.async_set_cover_position(position=100)
    
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        #relays = []
        if self._is_opening:
            _LOGGER.debug("Stop - is opening")
        elif self._is_closing:
            _LOGGER.debug("Stop - is closing")
        else:
            self._position = 50
            self._closed = False
            #self._timer = None
            self.async_schedule_update_ha_state(True)
        
