"""Support for Rfplayer sensors."""
import logging

from homeassistant.const import (
    CONF_DEVICES,CONF_DEVICES)
from homeassistant.helpers.entity import EntityCategory

from . import RfplayerDevice
from .const import (
    CONF_AUTOMATIC_ADD,
    DATA_DEVICE_REGISTER,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_KEY_ID,
    EVENT_KEY_SENSOR,
    EVENT_KEY_UNIT,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_ICONS = {
    "humidity": "mdi:water-percent",
    "battery": "mdi:battery",
    "temperature": "mdi:thermometer",
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Rfplayer platform."""

    config = entry.data
    options = entry.options

    # add jamming entity
    async_add_entities([RfplayerJammingSensor()])

    async def add_new_device(device_info):
        """Check if device is known, otherwise create device entity."""
        device_id = device_info[EVENT_KEY_ID]
        # create entity
        device = RfplayerSensor(
            protocol=device_id.split("_")[0],
            device_id=device_id.split("_")[1],
            unit_of_measurement=device_info[EVENT_KEY_UNIT],
            initial_event=device_info,
        )
        _LOGGER.debug("Add sensor entity %s", device_info)
        async_add_entities([device])
        

    if CONF_DEVICES in config:
        items_to_delete=[]
        for device_id, device_info in config[CONF_DEVICES].items():
            if EVENT_KEY_SENSOR in device_info:
                if((device_info.get("protocol")!=None) and (device_info.get("platform")!=None)):
                    await add_new_device(device_info)
                else :
                    _LOGGER.warning("Sensor entity not created %s - %s", device_id, device_info)
                    items_to_delete.append(device_id)

        for item in items_to_delete:
            config[CONF_DEVICES].pop(item)
                

    if options.get(CONF_AUTOMATIC_ADD, config[CONF_AUTOMATIC_ADD]):
        hass.data[DOMAIN][DATA_DEVICE_REGISTER][EVENT_KEY_SENSOR] = add_new_device


class RfplayerSensor(RfplayerDevice):
    """Representation of a Rfplayer sensor."""

    def __init__(
        self,
        protocol,
        device_id=None,
        unit_of_measurement=None,
        initial_event=None,
        name=None,
        **kwargs,
    ):
        """Handle sensor specific args and super init."""
        self._protocol = protocol
        self._device_id = device_id
        self._attr_name = name
        self._attr_unit_of_measurement = unit_of_measurement
        super().__init__(
            protocol, device_id=device_id, initial_event=initial_event, name=name
        )

    async def async_added_to_hass(self):
        """Register update callback."""
        # Register id and aliases
        await super().async_added_to_hass()

        if self._initial_event:
            self.hass.data[DOMAIN][DATA_ENTITY_LOOKUP][EVENT_KEY_SENSOR][
                self._initial_event[EVENT_KEY_ID]
            ] = self.entity_id

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()

    def _handle_event(self, event):
        """Domain specific event handler."""
        self._state = event["value"]

    @property
    def state(self):
        """Return value."""
        return self._state


class RfplayerJammingSensor(RfplayerDevice):
    """Representation of a Jamming Rfplayer sensor."""

    def __init__(self):
        """Handle sensor specific args and super init."""
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        super().__init__(
            "JAMMING", device_id=0, name="Jamming detection"
        )

    def _handle_event(self, event):
        """Domain specific event handler."""
        self._state = event["value"]

    @property
    def state(self):
        """Return value."""
        return self._state

    async def async_will_remove_from_hass(self):
        """Clean when entity removed."""
        _LOGGER.debug("Remove sensor entity %s", self._attr_unique_id)
        """
        await super().async_will_remove_from_hass()
        device_registry = await async_get_registry(self.hass)
        device = device_registry.async_get_device(
            (DOMAIN, self.hass.data[DOMAIN]
             [CONF_DEVICE] + "_" + self._attr_unique_id)
        )
        if device:
            device_registry.async_remove_device(device)
        """