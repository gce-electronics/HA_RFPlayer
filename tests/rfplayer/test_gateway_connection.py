from __future__ import annotations

from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from pytest_mock import MockerFixture
from serialx import SerialException

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from tests.rfplayer.conftest import rfplayer_config_entry
from tests.rfplayer.constants import JAMMING_BINARY_SENSOR_ENTITY_ID, SOME_INIT_COMMANDS, SOME_PROTOCOLS


@pytest.mark.integration
async def test_unload_closes_client(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test unloading closes the RFPlayer client."""
    entry = await rfplayer_config_entry(hass)

    client = entry.runtime_data.gateway.client
    assert client.connected

    with patch.object(client, "close", Mock()) as close:
        assert await hass.config_entries.async_unload(entry.entry_id)

    close.assert_called_once()


@pytest.mark.integration
async def test_unload_does_not_schedule_reconnect(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test unloading prevents reconnect scheduling."""
    entry = await rfplayer_config_entry(hass)

    gateway = entry.runtime_data.gateway

    with patch.object(
        gateway.client,
        "connect",
        AsyncMock(),
    ) as connect:
        await gateway.async_unload()

        # Simulate disconnect callback call to ensure we don't
        # schedule a reconnect when the gateway is unloaded.
        gateway.client.disconnect_callback(None)

        await hass.async_block_till_done()

    connect.assert_not_awaited()


@pytest.mark.integration
async def test_disconnect_schedules_reconnect(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test an unexpected disconnect schedules a reconnect."""
    entry = await rfplayer_config_entry(hass)

    gateway = entry.runtime_data.gateway

    with patch.object(
        gateway.client,
        "connect",
        AsyncMock(),
    ) as connect:
        gateway.client.disconnect_callback(RuntimeError("connection lost"))

        await hass.async_block_till_done()

    connect.assert_awaited_once()


@pytest.mark.integration
async def test_disconnect_only_schedules_one_reconnect(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test concurrent disconnects only schedule one reconnect."""
    entry = await rfplayer_config_entry(hass)
    gateway = entry.runtime_data.gateway

    with patch.object(gateway.client, "connect", AsyncMock()) as connect:
        gateway.client.disconnect_callback(ConnectionError())
        gateway.client.disconnect_callback(ConnectionError())
        gateway.client.disconnect_callback(ConnectionError())

        await hass.async_block_till_done()

    connect.assert_awaited_once()


@pytest.mark.integration
async def test_unload_cancels_pending_reconnect(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    entry = await rfplayer_config_entry(hass)
    gateway = entry.runtime_data.gateway

    with patch.object(gateway.client, "connect", AsyncMock()) as connect:
        gateway.client.disconnect_callback(ConnectionError())

        assert gateway._reconnect_task is not None  # noqa: SLF001

        await gateway.async_unload()

        await hass.async_block_till_done()

    connect.assert_not_awaited()


@pytest.mark.integration
async def test_connect(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to the device."""

    config_entry = await rfplayer_config_entry(hass)
    client = config_entry.runtime_data.gateway.client

    mock_serial_connection.assert_called_once_with(hass.loop, ANY, "/dev/ttyUSBfake", 115200)
    assert client.receiver_protocols == []
    assert client.init_commands == []
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.integration
async def test_connect_simulator(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to a simulated device without using a serial port."""

    config_entry = await rfplayer_config_entry(hass, device="/simulator")
    mock_serial_connection.assert_not_called()
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.integration
async def test_connect_with_protocols(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to set protocols."""

    config_entry = await rfplayer_config_entry(hass, protocols=SOME_PROTOCOLS)
    client = config_entry.runtime_data.gateway.client

    mock_serial_connection.assert_called_once_with(hass.loop, ANY, "/dev/ttyUSBfake", 115200)

    assert client.receiver_protocols == SOME_PROTOCOLS
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.integration
async def test_connect_with_init_commands(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    config_entry = await rfplayer_config_entry(hass, init_commands=SOME_INIT_COMMANDS)
    client = config_entry.runtime_data.gateway.client

    assert client.init_commands == ["PING", "HELLO"]
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.integration
async def test_connect_timeout(mock_serial_connection: Mock, mocker: MockerFixture, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to the device."""

    mocker.patch("custom_components.rfplayer.gateway.asyncio.wait_for").side_effect = TimeoutError

    config_entry = await rfplayer_config_entry(hass)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.integration
async def test_connect_failed(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test that we attempt to connect to the device."""

    mock_serial_connection.side_effect = SerialException

    config_entry = await rfplayer_config_entry(hass)
    mock_serial_connection.assert_called_with(hass.loop, ANY, "/dev/ttyUSBfake", 115200)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.integration
async def test_reconnect(mock_serial_connection, hass: HomeAssistant) -> None:
    """Test that we reconnect on connection loss."""

    # GIVEN
    config_entry = await rfplayer_config_entry(hass)
    client = config_entry.runtime_data.gateway.client

    assert client is not None
    assert config_entry.state is ConfigEntryState.LOADED
    mock_serial_connection.call_count = 1

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
    mock_serial_connection.call_count = 2
