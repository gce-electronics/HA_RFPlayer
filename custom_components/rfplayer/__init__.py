"""Support for RfPlayer gateway."""

from collections.abc import Mapping
import logging
from typing import Any

from custom_components.rfplayer.config_options import RfPlayerDeviceInfo
from custom_components.rfplayer.gateway import Gateway
from custom_components.rfplayer.migration import async_migrate_version_1_2
from custom_components.rfplayer.runtime import RfPlayerConfigEntry, RfPlayerRuntimeData
from custom_components.rfplayer.services import async_setup_services, async_unload_services
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.LIGHT, Platform.CLIMATE, Platform.COVER, Platform.SWITCH]


def is_valid_rf_device(device_id: str, device: Mapping[str, Any]) -> bool:
    """Validate a device config entry, recovering legacy values when possible."""
    return RfPlayerDeviceInfo.from_json(device, device_id=device_id) is not None


async def async_setup_entry(hass: HomeAssistant, entry: RfPlayerConfigEntry) -> bool:
    """Set up the RfPlayer component."""

    data = dict(entry.data)
    devices = dict(data.get("devices", {}))

    invalid_ids = [device_id for device_id, device in devices.items() if not is_valid_rf_device(device_id, device)]

    if invalid_ids:
        for device_id in invalid_ids:
            devices.pop(device_id)

        data["devices"] = devices
        hass.config_entries.async_update_entry(entry, data=data)

        _LOGGER.warning(
            "Removed %d invalid legacy RF device entries from configuration",
            len(invalid_ids),
        )

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
