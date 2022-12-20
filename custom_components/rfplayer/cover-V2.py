"""Support for Rfplayer cover."""
import logging

from homeassistant.components.cover import (
    DOMAIN as PLATFORM_COVER,
    CoverEntity,
    ATTR_POSITION, ATTR_CURRENT_POSITION,
    STATE_OPEN, STATE_OPENING, STATE_CLOSED, STATE_CLOSING
)
try:
    from homeassistant.components.cover import CoverDeviceClass, CoverEntityFeature
    DEVICE_CLASS_GARAGE = CoverDeviceClass.GARAGEswitch
    DEVICE_CLASS_SHUTTER = CoverDeviceClass.SHUTTER
    SUPPORT_OPEN = CoverEntityFeature.OPEN
    SUPPORT_CLOSE = CoverEntityFeature.CLOSE
    SUPPORT_SET_POSITION = CoverEntityFeature.SET_POSITION
    SUPPORT_STOP = CoverEntityFeature.STOP
except:# fallback (pre 2022.5)
    from homeassistant.components.cover import (
        DEVICE_CLASS_GARAGE, DEVICE_CLASS_SHUTTER,
        SUPPORT_OPEN, SUPPORT_CLOSE,
        SUPPORT_SET_POSITION, SUPPORT_STOP,
    )
from homeassistant.const import CONF_DEVICE_ID, CONF_DEVICES, CONF_PROTOCOL
from homeassistant.core import callback

from . import DATA_DEVICE_REGISTER, EVENT_KEY_COMMAND, RfplayerDevice
from .const import (
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_DIM,
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_ADDRESS,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_KEY_ID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("Add cover entity - hass : %s", str(hass))
    _LOGGER.debug("Add cover entity - entry : %s", str(entry))
    _LOGGER.debug("Add cover entity - async_add_entities : %s", str(async_add_entities))
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
        )
        _LOGGER.debug("Add cover entity %s", str(device_info))
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

        #if self._event is None:
        #    old_state = await self.async_get_last_state()
        #    if old_state is not None:
        #        self._state = old_state.state == COMMAND_ON

    def set_state(self, params: dict):
        _LOGGER.debug("Set state : %s %s", str(self),str(params))
        # => command to cover from mobile app
        if len(params) == 1:
            if "switch" in params:
                # device receive command - on=open/off=close/pause=stop
                self._attr_is_opening = params["switch"] == "on"
                self._attr_is_closing = params["switch"] == "off"
            elif "setclose" in params:
                # device receive command - mode to position
                pos = 100 - params["setclose"]
                self._attr_is_closing = pos < self.current_cover_position
                self._attr_is_opening = pos > self.current_cover_position

        # BINTHEN BCM Series payload:
        #   {"sequence":"1652428259464","setclose":38}
        # KingArt KING-Q4 payloads:
        #   {"switch":"off","setclose":21} or {"switch":"on","setclose":0}
        elif "setclose" in params:
            # the device has finished the action
            # reversed position: HA closed at 0, eWeLink closed at 100
            
            self._attr_current_cover_position = 100 - params["setclose"]
            self._attr_is_closed = self.current_cover_position == 0
            self._attr_is_closing = False
            self._attr_is_opening = False
            _LOGGER.debug("Set close : %s %s", str(self),str(params))

    @callback
    def _handle_event(self, event):
        command = event["command"]
        if command in [COMMAND_ON, "ALLON"]:
            self._state = True
        elif command in [COMMAND_OFF, "ALLOFF"]:
            self._state = False

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION

    def is_on(self):
        """Return true if device is on."""
        _LOGGER.debug("Test is on : %s", str(self))
        return self._state

    def is_opening(self):
        _LOGGER.debug("Test is opening : %s", str(self))
        return self._attr_state == STATE_OPENING

    def is_closing(self):
        _LOGGER.debug("Test is closing : %s", str(self))
        return self._attr_state == STATE_CLOSING

    def is_closed(self):
        _LOGGER.debug("Test is closed : %s", str(self))
        return self._attr_state == STATE_CLOSED

    async def async_open_cover(self, **kwargs) :
        _LOGGER.debug("Open cover : %s", str(self))
        """Turn the device on."""
        await self._async_send_command(COMMAND_ON)
        params = {"switch": "on","setclose": 0}
        self.set_state(params)
        self._async_write_ha_state()


    async def async_close_cover(self, **kwargs):
        _LOGGER.debug("Close cover : %s", str(self))
        """Turn the device off."""
        await self._async_send_command(COMMAND_OFF)
        #params = {"switch": "off","setclose": 100}
        #self.set_state(params)
        #self._async_write_ha_state()
        #self._attr_is_closed = True
        #self._attr_is_closing = False
        #self._attr_is_opening = False
        #self.async_write_ha_state()
        self._attr_state=STATE_CLOSED
        self.async_schedule_update_ha_state(False)

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Turn On : %s", str(self))
        """Turn the device on."""
        await self._async_send_command(COMMAND_ON)
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Turn Off : %s", str(self))
        """Turn the device off."""
        await self._async_send_command(COMMAND_OFF)
        self._state = False
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        _LOGGER.debug("Stop cover : %s", str(self))
        await self._async_send_command(COMMAND_DIM)
        params = {"switch": "pause","setclose": 50}
        self.set_state(params)
        self._async_write_ha_state()
        
