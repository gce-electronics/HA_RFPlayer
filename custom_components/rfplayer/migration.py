"""Migration code for RFPlayer integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)


async def async_migrate_version_1_2(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate entities to new slugified unique_id."""

    _LOGGER.info("Migrating %s to version 1.2", entry.entry_id)
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)

    count = 0
    error_count = 0
    for entity in entries:
        new_unique_id = slugify(entity.unique_id)
        new_entity_id = ".".join([slugify(part) for part in entity.entity_id.split(".")])

        _LOGGER.debug(
            "Migrating id=%s, entity_id=%s, unique_id=%s",
            entity.id,
            entity.entity_id,
            entity.unique_id,
        )

        # Skip if the slugify function didn't actually change the string
        if entity.unique_id == new_unique_id and entity.entity_id == new_entity_id:
            _LOGGER.debug(
                "Entity %s already has a slugified unique_id and entity_id, skipping",
                entity.entity_id,
            )
            continue

        try:
            registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id, new_entity_id=new_entity_id)
            count += 1
        except ValueError:
            error_count += 1
            _LOGGER.warning(
                "Cannot migrate unique_id %s to %s because it already exists", entity.unique_id, new_unique_id
            )

    _LOGGER.info(
        "Migrated %d/%d entities for config entry %s (errors: %d)", count, len(entries), entry.entry_id, error_count
    )

    # Update config entry version to 1.2
    hass.config_entries.async_update_entry(entry, version=1, minor_version=2)

    return True
