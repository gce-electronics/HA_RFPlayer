"""Support for Rfplayer switch."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_DEVICE_ID, CONF_DEVICES, CONF_PROTOCOL
from homeassistant.core import callback

from . import DATA_DEVICE_REGISTER, EVENT_KEY_COMMAND, RfplayerDevice
from .const import (
    COMMAND_OFF,
    COMMAND_ON,
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_ADDRESS,
    CONF_ENTITY_TYPE,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_KEY_ID,
    ENTITY_TYPE_SWITCH
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Rfplayer platform."""
    config = entry.data
    options = entry.options

    async def add_new_device(device_info):
        #if device_info.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_SWITCH or device_info.get(CONF_ENTITY_TYPE) == "":
        """Check if device is known, otherwise create device entity."""
        _LOGGER.debug("Add switch entity %s", device_info)
        # create entity
        try:
            device = RfplayerSwitch(
                protocol=device_info[CONF_PROTOCOL],
                device_address=device_info.get(CONF_DEVICE_ADDRESS),
                device_id=device_info.get(CONF_DEVICE_ID),
                initial_event=device_info,
            )
            async_add_entities([device])
        except Exception as err:
            _LOGGER.error("Switch %s creation error: %s",device_info.get(CONF_DEVICE_ID),str(err))

    if CONF_DEVICES in config:
        items_to_delete=[]
        for device_id, device_info in config[CONF_DEVICES].items():
            if EVENT_KEY_COMMAND in device_info:
                if((device_info.get("protocol")!=None) and (device_info.get("platform")=="switch")):
                    await add_new_device(device_info)
                else :
                    _LOGGER.warning("Switch entity not created %s - %s", device_id, device_info)
                    items_to_delete.append(device_id)
        for item in items_to_delete:
            config[CONF_DEVICES].pop(item)

    if options.get(CONF_AUTOMATIC_ADD, config[CONF_AUTOMATIC_ADD]):
        hass.data[DOMAIN][DATA_DEVICE_REGISTER][EVENT_KEY_COMMAND] = add_new_device


class RfplayerSwitch(RfplayerDevice, SwitchEntity):
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

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()

    @callback
    def _handle_event(self, event):
        command = event["command"]
        if command in [COMMAND_ON, "ALLON"]:
            self._state = True
        elif command in [COMMAND_OFF, "ALLOFF"]:
            self._state = False

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

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
