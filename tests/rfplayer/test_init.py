"""The tests for the RfPlayer component."""

from __future__ import annotations

import json
from typing import cast
from unittest.mock import ANY, Mock

import pytest
from pytest_homeassistant_custom_component.typing import WebSocketGenerator
from pytest_mock import MockerFixture
from serial import SerialException

from custom_components.rfplayer.const import DOMAIN, RFPLAYER_CLIENT, SIGNAL_RFPLAYER_EVENT
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData, RfplayerProtocol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.setup import async_setup_component
from tests.rfplayer.constants import (
    BLYSS_ADDRESS,
    BLYSS_ID_STRING,
    BLYSS_OFF_EVENT_DATA,
    JAMMING_BINARY_SENSOR_ENTITY_ID,
    JAMMING_ID_STRING,
    OREGON_ADDRESS,
    OREGON_EVENT_DATA,
    OREGON_ID_STRING,
    SOME_INIT_COMMANDS,
    SOME_PROTOCOLS,
)

from .conftest import setup_rfplayer_test_cfg


@pytest.mark.asyncio
async def test_fire_event(
    serial_connection_mock: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test fire event."""
    entry = await setup_rfplayer_test_cfg(hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True)

    calls: list[RfDeviceEvent] = []

    @callback
    def record_event(event: RfDeviceEvent):
        """Add recorded event to set."""
        calls.append(event)

    async_dispatcher_connect(hass, SIGNAL_RFPLAYER_EVENT, record_event)  # type: ignore[has-type]

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])

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

    device_jamming = device_registry.async_get_device(identifiers={(DOMAIN, "JAMMING-0")})
    assert device_jamming is not None
    assert device_jamming.manufacturer == "JAMMING"
    assert device_jamming.name == "JAMMING 0"

    device_oregon = device_registry.async_get_device(identifiers={(DOMAIN, OREGON_ID_STRING)})
    assert device_oregon is not None
    assert device_oregon.model == "PCR800"
    assert device_oregon.manufacturer == "OREGON"
    assert device_oregon.name == f"OREGON PCR800 {OREGON_ADDRESS}"

    device_blyss = device_registry.async_get_device(identifiers={(DOMAIN, BLYSS_ID_STRING)})
    assert device_blyss is not None
    assert device_blyss.model is None
    assert device_blyss.manufacturer == "BLYSS"
    assert device_blyss.name == f"BLYSS {BLYSS_ADDRESS}"

    assert calls[0].device.id_string == OREGON_ID_STRING
    assert calls[1].device.id_string == BLYSS_ID_STRING
    assert calls[2].device.id_string == BLYSS_ID_STRING


@pytest.mark.asyncio
async def test_send_raw_command(
    serial_connection_mock: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    """Test configuration."""
    await setup_rfplayer_test_cfg(hass, device="/dev/null", devices={})

    await hass.services.async_call("rfplayer", "send_raw_command", {"command": "ON A3 RTS QUALIFIER 1"}, blocking=True)

    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(bytearray(b"ZIA++ON A3 RTS QUALIFIER 1\n\r"))


@pytest.mark.asyncio
async def test_send_pairing_command(
    serial_connection_mock: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    """Test configuration."""
    await setup_rfplayer_test_cfg(hass, device="/dev/null", devices={})

    await hass.services.async_call(
        "rfplayer", "send_pairing_command", {"protocol": "CHACON", "address": "1"}, blocking=True
    )

    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(bytearray(b"ZIA++ASSOC CHACON ID 1\n\r"))


@pytest.mark.asyncio
async def test_simulate_event(
    serial_connection_mock: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    test_protocol: RfplayerProtocol,
) -> None:
    """Test configuration."""
    await setup_rfplayer_test_cfg(hass, device="/dev/null", automatic_add=True, devices={})

    await hass.services.async_call("rfplayer", "simulate_event", {"event_data": OREGON_EVENT_DATA}, blocking=True)

    device_oregon = device_registry.async_get_device(identifiers={(DOMAIN, OREGON_ID_STRING)})
    assert device_oregon is not None
    assert device_oregon.model == "PCR800"
    assert device_oregon.manufacturer == "OREGON"
    assert device_oregon.name == f"OREGON PCR800 {OREGON_ADDRESS}"


@pytest.mark.asyncio
async def test_ws_device_remove(
    serial_connection_mock: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test removing a device through device registry."""
    assert await async_setup_component(hass, "config", {})

    mock_entry = await setup_rfplayer_test_cfg(
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

    device_entry = device_registry.async_get_device(identifiers={("rfplayer", BLYSS_ID_STRING)})
    assert device_entry

    # Ask to remove existing device
    client = await hass_ws_client(hass)
    response = await client.remove_device(device_entry.id, mock_entry.entry_id)
    assert response["success"]

    # Verify device entry is removed
    assert device_registry.async_get_device(identifiers={("rfplayer", BLYSS_ID_STRING)}) is None

    # Verify that the config entry has removed the device
    assert len(mock_entry.data["devices"]) == 1
    assert JAMMING_ID_STRING in mock_entry.data["devices"]


@pytest.mark.asyncio
async def test_connect(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to the device."""

    config_entry = await setup_rfplayer_test_cfg(hass, device="/dev/ttyUSBfake")
    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])

    serial_connection_mock.assert_called_once_with(hass.loop, ANY, "/dev/ttyUSBfake", 115200)
    assert client.receiver_protocols == []
    assert client.init_commands == []
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_connect_simulator(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to a simulated device without using a serial port."""

    config_entry = await setup_rfplayer_test_cfg(hass, device="/simulator")
    serial_connection_mock.assert_not_called()
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_connect_with_protocols(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to set protocols."""

    config_entry = await setup_rfplayer_test_cfg(hass, device="/dev/ttyUSBfake", protocols=SOME_PROTOCOLS)
    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])

    serial_connection_mock.assert_called_once_with(hass.loop, ANY, "/dev/ttyUSBfake", 115200)

    assert client.receiver_protocols == SOME_PROTOCOLS
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_connect_with_init_commands(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    config_entry = await setup_rfplayer_test_cfg(hass, device="/dev/ttyUSBfake", init_commands=SOME_INIT_COMMANDS)
    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])

    assert client.init_commands == ["PING", "HELLO"]
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_connect_timeout(serial_connection_mock: Mock, mocker: MockerFixture, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to the device."""

    mocker.patch("custom_components.rfplayer.gateway.asyncio.timeout").side_effect = TimeoutError

    config_entry = await setup_rfplayer_test_cfg(hass, device="/dev/ttyUSBfake")

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_connect_failed(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to the device."""

    serial_connection_mock.side_effect = SerialException

    config_entry = await setup_rfplayer_test_cfg(hass, device="/dev/ttyUSBfake")
    serial_connection_mock.assert_called_once_with(hass.loop, ANY, "/dev/ttyUSBfake", 115200)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_reconnect(serial_connection_mock, hass: HomeAssistant) -> None:
    """Test that we reconnect on connection loss."""

    # GIVEN
    config_entry = await setup_rfplayer_test_cfg(hass, device="/dev/ttyUSBfake")
    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])

    assert client is not None
    assert config_entry.state is ConfigEntryState.LOADED
    serial_connection_mock.call_count = 1

    # WHEN
    client.disconnect_callback(None)

    # THEN
    state = hass.states.get(JAMMING_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNAVAILABLE

    await hass.async_block_till_done()

    state = hass.states.get(JAMMING_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN

    assert config_entry.state is ConfigEntryState.LOADED
    serial_connection_mock.call_count = 2
