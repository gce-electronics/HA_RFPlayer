"""Common test tools."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_mock import MockerFixture

from custom_components.rfplayer.const import (
    CONF_AUTOMATIC_ADD,
    CONF_INIT_COMMANDS,
    CONF_RECEIVER_PROTOCOLS,
    CONF_RECONNECT_INTERVAL,
    CONF_REDIRECT_ADDRESS,
    CONF_VERBOSE_MODE,
    INIT_COMMANDS_EMPTY,
)
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfplayerProtocol
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent
from custom_components.rfplayer.runtime import RfPlayerConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_DEVICE, CONF_DEVICES
from homeassistant.core import HomeAssistant, State


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: PT004
    """Automatically enable loading custom integrations in all tests."""
    return


@pytest.fixture
def test_protocol() -> RfplayerProtocol:
    """Create a rfclient protocol with patched event loop."""

    transport = Mock(spec=asyncio.WriteTransport)
    event_callback = Mock(spec=callable)
    disconnect_callback = Mock(spec=callable)
    protocol = RfplayerProtocol(
        event_callback=event_callback,
        disconnect_callback=disconnect_callback,
        init_script=["LEDACTIVITY 0", "JAMMING 10"],
        verbose=True,
    )
    protocol.transport = transport
    return protocol


@pytest.fixture
def mock_serial_connection(mocker: MockerFixture, test_protocol: RfplayerProtocol) -> Mock:
    """Patch create_serial_connection to return mock protocol."""

    return mocker.patch(
        "custom_components.rfplayer.rfplayerlib.create_serial_connection",
        return_value=(None, test_protocol),
    )


@pytest.fixture
def mock_tcp_connection(mocker: MockerFixture, test_client: RfPlayerClient, test_protocol: RfplayerProtocol) -> Mock:
    """Patch create_tcp_connection to return mock protocol."""
    loop = asyncio.get_event_loop()
    test_transport = Mock(spec=asyncio.WriteTransport)
    return mocker.patch.object(loop, "create_connection", return_value=(test_transport, test_protocol))


@pytest.fixture
def test_client(mock_serial_connection: Mock, test_protocol: RfplayerProtocol) -> RfPlayerClient:
    """Create a rfclient with patch serial connection."""

    return RfPlayerClient(
        event_callback=cast(Callable[[RfDeviceEvent], None], test_protocol.event_callback),
        disconnect_callback=test_protocol.disconnect_callback,
        port="/dev/ttyUSB0",
        receiver_protocols=["X2D", "RTS"],
        init_commands=["PING", "HELLO"],
        verbose=True,
    )


def create_rfplayer_test_options(
    device: str = "/dev/tty123",
    automatic_add: bool = False,
    protocols: list[str] | None = None,
    init_commands: str | None = INIT_COMMANDS_EMPTY,
    devices: dict[str, dict] | None = None,
) -> dict:
    """Create rfplayer config entry data."""
    return {
        CONF_DEVICE: device,
        CONF_AUTOMATIC_ADD: automatic_add,
        CONF_RECEIVER_PROTOCOLS: protocols or [],
        CONF_INIT_COMMANDS: init_commands,
        CONF_VERBOSE_MODE: True,
        CONF_RECONNECT_INTERVAL: 0.05,
        CONF_DEVICES: devices or {},
        CONF_REDIRECT_ADDRESS: {},  # Legacy persisted address redirection map. Now computed so must be ignored.
    }


async def rfplayer_config_entry(  # noqa: PLR0913
    hass: HomeAssistant,
    device: str = "/dev/ttyUSBfake",
    *,
    automatic_add: bool = False,
    devices: dict[str, dict] | None = None,
    protocols: list[str] | None = None,
    init_commands: str | None = INIT_COMMANDS_EMPTY,
    minor_version=2,
) -> RfPlayerConfigEntry:
    """Construct a rfplayer config entry."""
    serialized_options = create_rfplayer_test_options(
        device=device, automatic_add=automatic_add, devices=devices, protocols=protocols, init_commands=init_commands
    )
    mock_entry = MockConfigEntry(
        domain="rfplayer", unique_id="a_player", data=serialized_options, version=1, minor_version=minor_version
    )
    mock_entry.supports_remove_device = True
    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()
    return mock_entry


def assert_entity_state(
    hass: HomeAssistant, entity_id: str, expected_state: str, expected_friendly_name: str | None = None
) -> State:
    state = hass.states.get(entity_id)
    assert state
    assert state.state == expected_state
    if expected_friendly_name:
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == expected_friendly_name
    return state
