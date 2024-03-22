"""Support for Rfplayer binary sensors."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RfplayerDevice
from .const import DATA_ENTITY_LOOKUP, DOMAIN, EVENT_KEY_JAMMING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Rfplayer platform."""
    # add jamming entity
    async_add_entities([RfplayerJammingBinarySensor()])


class RfplayerJammingBinarySensor(RfplayerDevice, BinarySensorEntity):
    """Representation of a Rfplayer jamming binary sensor."""

    entity_description = BinarySensorEntityDescription(
        key="jamming_detection",
        translation_key="jamming_detection",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:waveform",
    )
    _attr_is_on = False

    def __init__(self) -> None:
        """Init the jamming sensor rfplayer entity."""
        # Get Jamming events by simulating event id
        super().__init__(
            protocol="JAMMING",
            unique_id="jamming_detection",
            name="Jamming detection",
        )

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        # Register id and aliases
        await super().async_added_to_hass()

        self.hass.data[DOMAIN][DATA_ENTITY_LOOKUP][EVENT_KEY_JAMMING][
            "JAMMING_0_cmd"
        ] = self.entity_id

    def _handle_event(self, event):
        """Domain specific event handler."""
        self._attr_is_on = bool(event["value"] == "1")
