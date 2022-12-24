"""Support for Rfplayer cover (V2)."""
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
    COMMAND_UP,
    COMMAND_MY,
    COMMAND_DOWN,
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_ADDRESS,
    CONF_ENTITY_TYPE,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_KEY_ID,
    ENTITY_TYPE_COVER
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
        #if device_info.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_COVER or device_info.get(CONF_ENTITY_TYPE) == "":
        _LOGGER.debug("Add cover entity %s", str(device_info))
        """Check if device is known, otherwise create device entity."""
        # create entity
        try:
            device = RfplayerCover(
                protocol=device_info[CONF_PROTOCOL],
                device_address=device_info.get(CONF_DEVICE_ADDRESS),
                device_id=device_info.get(CONF_DEVICE_ID),
                initial_event=device_info,
            )
            async_add_entities([device])
        except :
            _LOGGER.error("Cover %s creation error",device_info.get(CONF_DEVICE_ID))

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

        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._state = old_state.state == COMMAND_ON
    
    @callback
    def _handle_event(self, event):
        command = event["command"]
        if command in [COMMAND_ON, COMMAND_UP, "ALLON"]:
            self._state = STATE_OPEN
        elif command in [COMMAND_OFF, COMMAND_DOWN, "ALLOFF"]:
            self._state = STATE_CLOSED
        elif command in [COMMAND_DIM, COMMAND_MY, "ALLDIM"]:
            self._state = STATE_CLOSED

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    @property
    def is_opening(self):
        #_LOGGER.debug("Test is opening : %s", str(self))
        return self._attr_state == STATE_OPENING

    @property
    def is_closing(self):
        #_LOGGER.debug("Test is closing : %s", str(self))
        return self._attr_state == STATE_CLOSING

    @property
    def is_closed(self):
        #_LOGGER.debug("Test is closed : %s", str(self))
        return self._attr_state == STATE_CLOSED

    async def async_open_cover(self, **kwargs) :
        _LOGGER.debug("Open cover : %s", str(self))
        """Turn the device on."""
        await self._async_send_command(COMMAND_ON)
        self._attr_state=STATE_OPEN
        self.async_schedule_update_ha_state()


    async def async_close_cover(self, **kwargs):
        _LOGGER.debug("Close cover : %s", str(self))
        """Turn the device off."""
        await self._async_send_command(COMMAND_OFF)
        self._attr_state=STATE_CLOSED
        self.async_schedule_update_ha_state(False)

    async def async_stop_cover(self, **kwargs):
        _LOGGER.debug("Stop cover : %s", str(self))
        await self._async_send_command(COMMAND_DIM)
        self._attr_state=STATE_OPEN
        self.async_schedule_update_ha_state(False)
        
