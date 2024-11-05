"""Support for RfPlayer gateway."""

import logging
from typing import cast

from custom_components.rfplayer.const import DOMAIN, RFPLAYER_GATEWAY
from custom_components.rfplayer.gateway import Gateway
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

_LOGGER = logging.getLogger(__name__)


PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.LIGHT, Platform.CLIMATE, Platform.COVER, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the RfPlayer component."""
    hass.data.setdefault(
        DOMAIN,
        {},
    )

    gateway = Gateway(hass, entry)
    hass.data[DOMAIN][RFPLAYER_GATEWAY] = gateway
    await gateway.async_setup()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload RfPlayer component."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    gateway = cast(Gateway, hass.data[DOMAIN][RFPLAYER_GATEWAY])
    await gateway.async_unload()

    hass.data.pop(DOMAIN)

    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device.

    The actual cleanup is done in the device registry event
    """
    return True
