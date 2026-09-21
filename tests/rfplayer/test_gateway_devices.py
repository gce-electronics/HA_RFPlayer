"""The tests for the RfPlayer component."""

import json
from typing import TypedDict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.rfplayer.const import DOMAIN, SIGNAL_RFPLAYER_EVENT
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.setup import async_setup_component
from tests.rfplayer.conftest import rfplayer_config_entry
from tests.rfplayer.constants import (
    BLYSS_ADDRESS,
    BLYSS_ID_STRING,
    BLYSS_OFF_EVENT_DATA,
    OREGON_ADDRESS,
    OREGON_EVENT_DATA,
    OREGON_ID_STRING,
)


class DeviceMetadata(TypedDict):
    """Expected metadata for a registered RFPlayer device."""

    model: str
    manufacturer: str
    name: str


def assert_device_metadata(
    device_registry: dr.DeviceRegistry,
    config_entry: ConfigEntry,
    id_string: str,
    *,
    expected: DeviceMetadata,
):
    device = device_registry.async_get_device_by_identifier(
        identifier=(DOMAIN, id_string), config_entry_id=config_entry.entry_id
    )
    assert device is not None
    assert device.model == expected["model"]
    assert device.manufacturer == expected["manufacturer"]
    assert device.name == expected["name"]


def assert_device_exists(
    device_registry: dr.DeviceRegistry, config_entry: ConfigEntry, id_string: str, *, exists: bool
) -> DeviceEntry | None:
    device = device_registry.async_get_device_by_identifier(
        identifier=(DOMAIN, id_string), config_entry_id=config_entry.entry_id
    )
    assert device is not None if exists else device is None
    return device


pytestmark = pytest.mark.integration


@pytest.mark.integration
async def test_device_discovery(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test fire event."""
    entry = await rfplayer_config_entry(hass, automatic_add=True)

    client = entry.runtime_data.gateway.client

    # Ensure only Jamming is present
    device_entries = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(device_entries) == 1
    assert_device_exists(device_registry, entry, "JAMMING-0", exists=True)

    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock) as async_reload:
        client.event_callback(
            RfDeviceEvent(
                device=RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800"),
                data=RfPlayerEventData(OREGON_EVENT_DATA),
            )
        )
        await hass.async_block_till_done()

    async_reload.assert_not_awaited()

    # Ensure Oregon is added automatically
    device_entries = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(device_entries) == 2

    assert_device_metadata(
        device_registry,
        entry,
        OREGON_ID_STRING,
        expected={
            "model": "PCR800",
            "manufacturer": "OREGON",
            "name": f"OREGON PCR800 {OREGON_ADDRESS}",
        },
    )


@pytest.mark.integration
async def test_remove_device(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test removing a device through device registry."""
    assert await async_setup_component(hass, "config", {})

    mock_entry = await rfplayer_config_entry(
        hass,
        devices={
            BLYSS_ID_STRING: {
                "protocol": "BLYSS",
                "address": BLYSS_ADDRESS,
                "profile_name": "X10|CHACON|KD101|BLYSS|FS20 On/Off",
                "event_data": json.dumps(BLYSS_OFF_EVENT_DATA),
            },
        },
    )

    assert len(mock_entry.data["devices"]) == 1

    device = assert_device_exists(device_registry, mock_entry, BLYSS_ID_STRING, exists=True)
    assert device

    # Ask to remove existing device
    client = await hass_ws_client(hass)
    response = await client.remove_device(device.id)
    assert response["success"]

    # Verify device entry is removed
    assert_device_exists(device_registry, mock_entry, BLYSS_ID_STRING, exists=False)

    # Verify that the config entry has removed the device
    assert len(mock_entry.data["devices"]) == 0


@pytest.mark.integration
async def test_fire_event(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test fire event."""
    entry = await rfplayer_config_entry(hass, automatic_add=True)

    calls: list[RfDeviceEvent] = []

    @callback
    def record_event(event: RfDeviceEvent):
        """Add recorded event to set."""
        calls.append(event)

    async_dispatcher_connect(hass, SIGNAL_RFPLAYER_EVENT, record_event)  # type: ignore[has-type]

    client = entry.runtime_data.gateway.client

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800"),
            data=RfPlayerEventData(OREGON_EVENT_DATA),
        )
    )

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="BLYSS", address=BLYSS_ADDRESS),
            data=RfPlayerEventData(BLYSS_OFF_EVENT_DATA),
        )
    )

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="BLYSS", address=BLYSS_ADDRESS),
            data=RfPlayerEventData(BLYSS_OFF_EVENT_DATA),
        )
    )

    # Ensure blyss is not duplicated
    device_entries = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert len(device_entries) == 3

    assert_device_metadata(
        device_registry,
        entry,
        "JAMMING-0",
        expected={
            "model": "",
            "manufacturer": "JAMMING",
            "name": "JAMMING 0",
        },
    )

    assert_device_metadata(
        device_registry,
        entry,
        OREGON_ID_STRING,
        expected={
            "model": "PCR800",
            "manufacturer": "OREGON",
            "name": f"OREGON PCR800 {OREGON_ADDRESS}",
        },
    )

    assert_device_metadata(
        device_registry,
        entry,
        BLYSS_ID_STRING,
        expected={
            "model": "",
            "manufacturer": "BLYSS",
            "name": f"BLYSS {BLYSS_ADDRESS}",
        },
    )

    assert calls[0].device.id_string == OREGON_ID_STRING
    assert calls[1].device.id_string == BLYSS_ID_STRING
    assert calls[2].device.id_string == BLYSS_ID_STRING
