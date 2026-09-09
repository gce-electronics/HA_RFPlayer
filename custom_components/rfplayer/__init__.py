"""Support for RfPlayer gateway."""

from custom_components.rfplayer.gateway import Gateway
from custom_components.rfplayer.migration import async_migrate_version_1_2
from custom_components.rfplayer.runtime import RfPlayerConfigEntry, RfPlayerRuntimeData
from custom_components.rfplayer.services import async_setup_services, async_unload_services
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.LIGHT, Platform.CLIMATE, Platform.COVER, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: RfPlayerConfigEntry) -> bool:
    """Set up the RfPlayer component."""

    gateway = Gateway(hass, entry)
    entry.runtime_data = RfPlayerRuntimeData(
        gateway=gateway,
    )
    await gateway.async_setup()
    await async_setup_services(hass, gateway)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RfPlayerConfigEntry) -> bool:
    """Unload RfPlayer component."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    await async_unload_services(hass)
    await entry.runtime_data.gateway.async_unload()

    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: RfPlayerConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device."""
    return await entry.runtime_data.gateway.async_remove_rf_device(device_entry)


async def async_migrate_entry(hass: HomeAssistant, entry: RfPlayerConfigEntry) -> bool:
    """Migrate old entry."""
    if entry.version == 1 and entry.minor_version <= 3:
        return await async_migrate_version_1_2(hass, entry)
    return True
