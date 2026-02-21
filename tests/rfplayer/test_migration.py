"""Tests for RFPlayer migration code."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_mock import MockerFixture

from custom_components.rfplayer.const import DOMAIN
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from tests.rfplayer.conftest import create_rfplayer_test_cfg, setup_rfplayer_test_cfg
from tests.rfplayer.constants import (
    BLYSS_ID_STRING,
    BLYSS_MOTION_DEVICE_INFO,
    BLYSS_MOTION_ID_STRING,
    BLYSS_SMOKE_DEVICE_INFO,
    BLYSS_SMOKE_ID_STRING,
    OREGON_DEVICE_INFO,
    OREGON_ID_STRING,
)


@pytest.mark.asyncio
async def test_async_migrate_version_from_1_1(
    hass: HomeAssistant,
    serial_connection_mock: Mock,
    mocker: MockerFixture,
) -> None:

    # Create a mock config entry with version 1.1
    entry_data = create_rfplayer_test_cfg(
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
            slugify(BLYSS_MOTION_ID_STRING): BLYSS_MOTION_DEVICE_INFO,
            slugify(BLYSS_SMOKE_ID_STRING): BLYSS_SMOKE_DEVICE_INFO,
        },
    )
    mock_entry = MockConfigEntry(domain="rfplayer", unique_id="a_player", data=entry_data, version=1, minor_version=1)
    mock_entry.add_to_hass(hass)

    # Get the actual registry
    registry = er.async_get(hass)

    all_ids = [
        f"{OREGON_ID_STRING}_low_battery",  # "illegal/old" ID format
        f"{slugify(BLYSS_ID_STRING)}_motion",  # "legal/new" ID format
        f"{BLYSS_ID_STRING}_smoke",  # conflicting ID format that will cause a migration error when trying to migrate
    ]

    all_entities = [
        registry.async_get_or_create(
            domain=DOMAIN,
            platform=Platform.BINARY_SENSOR,
            unique_id=one_id,
            config_entry=mock_entry,
        )
        for one_id in all_ids
    ]

    # Spy on entity registry to capture update calls
    spy_async_update_entity = mocker.spy(registry, "async_update_entity")
    mocker.patch("custom_components.rfplayer.migration.er.async_get", return_value=registry)

    # Verify initial state before migration
    assert mock_entry.version == 1
    assert mock_entry.minor_version == 1

    # Start the migration by setting up the config entry, which should trigger the migration code
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    migrated_entity = all_entities[0]
    migrated_id = all_ids[0]
    conflicting_entity = all_entities[2]
    conflicting_id = all_ids[2]
    spy_async_update_entity.assert_has_calls(
        [
            mocker.call(  # Migrated entity
                migrated_entity.entity_id,
                new_unique_id=slugify(migrated_id),
                new_entity_id=f"{DOMAIN}.binary_sensor_{slugify(migrated_id)}",
            ),
            mocker.call(  # Conflicting entity
                conflicting_entity.entity_id,
                new_unique_id=slugify(conflicting_id),
                new_entity_id=f"{DOMAIN}.binary_sensor_{slugify(conflicting_id)}",
            ),
        ],
        any_order=True,
    )
    assert spy_async_update_entity.call_count == 2

    # Test that the config entry version was updated to 1.2
    assert mock_entry.version == 1
    assert mock_entry.minor_version == 2


@pytest.mark.asyncio
async def test_async_migrate_version_from_1_2(
    hass: HomeAssistant,
    serial_connection_mock: Mock,
    mocker: MockerFixture,
) -> None:

    migrate_mock = mocker.patch("custom_components.rfplayer.migration.async_migrate_version_1_2")

    await setup_rfplayer_test_cfg(
        hass,
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
        },
        minor_version=2,
    )

    assert migrate_mock.call_count == 0
