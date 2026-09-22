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
    canonical_id: str,
    *,
    expected: DeviceMetadata,
):
    device = device_registry.async_get_device_by_identifier(
        identifier=(DOMAIN, canonical_id), config_entry_id=config_entry.entry_id
    )
    assert device is not None
    assert device.model == expected["model"]
    assert device.manufacturer == expected["manufacturer"]
    assert device.name == expected["name"]


def assert_device_exists(
    device_registry: dr.DeviceRegistry, config_entry: ConfigEntry, canonical_id: str, *, exists: bool
) -> DeviceEntry | None:
    device = device_registry.async_get_device_by_identifier(
        identifier=(DOMAIN, canonical_id), config_entry_id=config_entry.entry_id
    )
    assert device is not None if exists else device is None
    return device


def assert_device_count(device_registry: dr.DeviceRegistry, config_entry: ConfigEntry, count: int):
    device_entries = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    assert len(device_entries) == count


@pytest.mark.integration
async def test_via_gateway(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test fire event."""
    config_entry = await rfplayer_config_entry(hass, automatic_add=True)

    # Ensure Gateway + Jamming is present
    assert_device_count(device_registry, config_entry, 2)
    # Gateway
    gateway = assert_device_exists(device_registry, config_entry, config_entry.entry_id, exists=True)
    assert gateway
    assert gateway.manufacturer == "GCE Electronics"
    assert gateway.model == "RFPlayer"
    assert gateway.via_device_id is None
    # Jamming
    rf_device = assert_device_exists(device_registry, config_entry, "JAMMING-0", exists=True)
    assert rf_device
    assert rf_device.manufacturer == "JAMMING"
    assert rf_device.model == ""
    assert rf_device.via_device_id == gateway.id


@pytest.mark.integration
async def test_device_discovery(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test fire event."""
    config_entry = await rfplayer_config_entry(hass, automatic_add=True)

    client = config_entry.runtime_data.gateway.client

    # Ensure Gateway + Jamming is present
    assert_device_count(device_registry, config_entry, 2)
    assert_device_exists(device_registry, config_entry, "JAMMING-0", exists=True)

    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock) as async_reload:
        client.event_callback(
            RfDeviceEvent(
                device=RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800"),
                data=RfPlayerEventData(OREGON_EVENT_DATA),
            )
        )
        await hass.async_block_till_done()

    # Discovery must not reload the config entry when the device is added
    async_reload.assert_not_awaited()

    # Ensure Oregon is added automatically
    assert_device_count(device_registry, config_entry, 3)

    assert_device_metadata(
        device_registry,
        config_entry,
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

    config_entry = await rfplayer_config_entry(
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

    assert_device_count(device_registry, config_entry, 3)

    device = assert_device_exists(device_registry, config_entry, BLYSS_ID_STRING, exists=True)
    assert device

    # Ask to remove existing device
    client = await hass_ws_client(hass)
    response = await client.remove_device(device.id)
    assert response["success"]

    # Verify device entry is removed
    assert_device_exists(device_registry, config_entry, BLYSS_ID_STRING, exists=False)

    # Verify that the config entry has removed the device
    assert len(config_entry.data["devices"]) == 0


@pytest.mark.integration
async def test_fire_event(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test fire event."""
    config_entry = await rfplayer_config_entry(hass, automatic_add=True)

    calls: list[RfDeviceEvent] = []

    @callback
    def record_event(event: RfDeviceEvent):
        """Add recorded event to set."""
        calls.append(event)

    async_dispatcher_connect(hass, SIGNAL_RFPLAYER_EVENT, record_event)  # type: ignore[has-type]

    client = config_entry.runtime_data.gateway.client

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
    # Gateway + Jammin + Blyss + Oregon
    assert_device_count(device_registry, config_entry, 4)

    assert_device_metadata(
        device_registry,
        config_entry,
        "JAMMING-0",
        expected={
            "model": "",
            "manufacturer": "JAMMING",
            "name": "JAMMING 0",
        },
    )

    assert_device_metadata(
        device_registry,
        config_entry,
        OREGON_ID_STRING,
        expected={
            "model": "PCR800",
            "manufacturer": "OREGON",
            "name": f"OREGON PCR800 {OREGON_ADDRESS}",
        },
    )

    assert_device_metadata(
        device_registry,
        config_entry,
        BLYSS_ID_STRING,
        expected={
            "model": "",
            "manufacturer": "BLYSS",
            "name": f"BLYSS {BLYSS_ADDRESS}",
        },
    )

    assert calls[0].device.canonical_id == OREGON_ID_STRING
    assert calls[1].device.canonical_id == BLYSS_ID_STRING
    assert calls[2].device.canonical_id == BLYSS_ID_STRING
