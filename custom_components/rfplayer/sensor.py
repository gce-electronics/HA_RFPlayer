"""Support for Rfplayer sensors."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import RestoreSensor
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Rfplayer platform."""
    config = entry.data
    options = entry.options

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
        _LOGGER.debug("Add sensor entity %s", device_id)
        async_add_entities([device])

    if CONF_DEVICES in config:
        for device in config[CONF_DEVICES].values():
            if EVENT_KEY_SENSOR in device:
                await add_new_device(device)

    if options.get(CONF_AUTOMATIC_ADD, config[CONF_AUTOMATIC_ADD]):
        hass.data[DOMAIN][DATA_DEVICE_REGISTER][EVENT_KEY_SENSOR] = add_new_device


class RfplayerSensor(RfplayerDevice, RestoreSensor):
    """Representation of a Rfplayer sensor."""

    _attr_native_value: float | None = None

    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        protocol: str,
        device_id: str | None = None,
        initial_event: dict[str, Any] | None = None,
        name: str | None = None,
        unique_id: str | None = None,
        unit_of_measurement: str | None = None,
    ) -> None:
        """Handle sensor specific args and super init."""
        self._attr_native_unit_of_measurement = unit_of_measurement
        super().__init__(
            protocol=protocol,
            device_id=device_id,
            initial_event=initial_event,
            name=name,
            unique_id=unique_id,
        )

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        # Register id and aliases
        await super().async_added_to_hass()

        if self._initial_event:
            self.hass.data[DOMAIN][DATA_ENTITY_LOOKUP][EVENT_KEY_SENSOR][
                self._initial_event[EVENT_KEY_ID]
            ] = self.entity_id

    def _handle_event(self, event: dict[str, Any]) -> None:
        """Domain specific event handler."""
        self._attr_native_value = float(event["value"])
