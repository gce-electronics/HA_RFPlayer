"""Tests for RFPlayer migration code."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_mock import MockerFixture

from custom_components.rfplayer import async_migrate_entry
from custom_components.rfplayer.config_options import RfPlayerConfigData, RfPlayerOptions
from custom_components.rfplayer.const import DOMAIN
from homeassistant.const import CONF_DEVICE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from tests.rfplayer.conftest import create_rfplayer_test_options, rfplayer_config_entry
from tests.rfplayer.constants import (
    BLYSS_ID_STRING,
    BLYSS_MOTION_DEVICE_INFO,
    BLYSS_MOTION_ID_STRING,
    BLYSS_SMOKE_DEVICE_INFO,
    BLYSS_SMOKE_ID_STRING,
    OREGON_DEVICE_INFO,
    OREGON_ID_STRING,
)


@pytest.mark.integration
async def test_async_migrate_version_from_1_1(
    hass: HomeAssistant,
    mocker: MockerFixture,
) -> None:

    # Create a mock config entry with version 1.1
    entry_data = create_rfplayer_test_options(
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
            slugify(BLYSS_MOTION_ID_STRING): BLYSS_MOTION_DEVICE_INFO,
            slugify(BLYSS_SMOKE_ID_STRING): BLYSS_SMOKE_DEVICE_INFO,
        },
    )
    entry_data[CONF_DEVICE] = "/dev/ttyUSBfake"
    mock_entry = MockConfigEntry(domain="rfplayer", data=entry_data, version=1, minor_version=1)
    mock_entry.add_to_hass(hass)
    mocker.patch(
        "custom_components.rfplayer.migration.async_get_rfplayer_unique_id",
        return_value="rfplayer_fd0cba71",
    )

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

    # Exercise migration directly
    assert await async_migrate_entry(hass, mock_entry)

    migrated_entity = all_entities[0]
    migrated_id = all_ids[0]
    conflicting_entity = all_entities[2]
    conflicting_id = all_ids[2]
    spy_async_update_entity.assert_any_call(
        migrated_entity.entity_id,
        new_unique_id=slugify(migrated_id),
        new_entity_id=f"{DOMAIN}.binary_sensor_{slugify(migrated_id)}",
    )
    spy_async_update_entity.assert_any_call(
        conflicting_entity.entity_id,
        new_unique_id=slugify(conflicting_id),
        new_entity_id=f"{DOMAIN}.binary_sensor_{slugify(conflicting_id)}",
    )
    assert spy_async_update_entity.call_count >= 2

    # Both migration steps run in sequence during the same setup.
    assert mock_entry.version == 2
    assert mock_entry.minor_version == 0


@pytest.mark.integration
async def test_async_migrate_version_from_1_2(
    hass: HomeAssistant,
    mocker: MockerFixture,
) -> None:

    # Create a mock config entry with version 1.2
    entry_data = create_rfplayer_test_options()
    entry_data[CONF_DEVICE] = "/dev/ttyUSBfake"
    mock_entry = MockConfigEntry(domain="rfplayer", data=entry_data, version=1, minor_version=2)
    mock_entry.add_to_hass(hass)
    mocker.patch(
        "custom_components.rfplayer.migration.async_get_rfplayer_unique_id",
        return_value="rfplayer_fd0cba71",
    )

    # Start the migration by setting up the config entry, which should trigger the migration code
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    # Exercise migration directly
    assert await async_migrate_entry(hass, mock_entry)

    entry = hass.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry is not None
    assert entry.unique_id == "rfplayer_fd0cba71"
    assert RfPlayerConfigData.from_json(entry.data) == RfPlayerConfigData(device="/dev/ttyUSBfake")
    assert RfPlayerOptions.from_json(entry.options) == RfPlayerOptions.from_json(entry_data)


@pytest.mark.integration
async def test_async_migrate_version_from_2_0(
    hass: HomeAssistant,
    mock_serial_connection: Mock,
    mocker: MockerFixture,
) -> None:

    migrate_12 = mocker.patch("custom_components.rfplayer.migration.async_migrate_version_1_2")
    migrate_20 = mocker.patch("custom_components.rfplayer.migration.async_migrate_version_2_0")

    entry = await rfplayer_config_entry(
        hass,
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
        },
        version=2,
        minor_version=0,
    )

    assert migrate_12.call_count == 0
    assert migrate_20.call_count == 0
    assert entry.version == 2
    assert entry.minor_version == 0
