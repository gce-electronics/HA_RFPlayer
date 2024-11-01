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
)
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfplayerProtocol
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, CONF_DEVICES
from homeassistant.core import HomeAssistant


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
    loop = Mock()
    protocol = RfplayerProtocol(
        event_callback=event_callback,
        disconnect_callback=disconnect_callback,
        loop=loop,
        init_script=["LEDACTIVITY 0", "JAMMING 10"],
        verbose=True,
    )
    protocol.transport = transport
    return protocol


@pytest.fixture
def serial_connection_mock(mocker: MockerFixture, test_protocol: RfplayerProtocol) -> Mock:
    """Patch create_serial_connection to return mock protocol."""

    return mocker.patch(
        "custom_components.rfplayer.rfplayerlib.create_serial_connection",
        return_value=(None, test_protocol),
    )


@pytest.fixture
def test_client(serial_connection_mock: Mock, test_protocol: RfplayerProtocol) -> RfPlayerClient:
    """Create a rfclient with patch serial connection."""

    return RfPlayerClient(
        event_callback=cast(Callable[[RfDeviceEvent], None], test_protocol.event_callback),
        disconnect_callback=test_protocol.disconnect_callback,
        loop=Mock(spec=asyncio.AbstractEventLoop),
        port="/dev/ttyUSB0",
        baud=115200,
        receiver_protocols=["X2D", "RTS"],
        init_commands="PING\nHELLO",
    )


def create_rfplayer_test_cfg(
    device: str = "/dev/tty123",
    automatic_add: bool = False,
    protocols: list[str] | None = None,
    devices: dict[str, dict] | None = None,
):
    """Create rfplayer config entry data."""
    return {
        CONF_DEVICE: device,
        CONF_AUTOMATIC_ADD: automatic_add,
        CONF_RECEIVER_PROTOCOLS: protocols,
        CONF_INIT_COMMANDS: None,
        CONF_VERBOSE_MODE: True,
        CONF_RECONNECT_INTERVAL: 10,
        CONF_DEVICES: devices or {},
        CONF_REDIRECT_ADDRESS: {},
    }


async def setup_rfplayer_test_cfg(
    hass: HomeAssistant,
    device: str = "abcd",
    automatic_add: bool = False,
    devices: dict[str, dict] | None = None,
    protocols: list[str] | None = None,
) -> ConfigEntry:
    """Construct a rfplayer config entry."""
    entry_data = create_rfplayer_test_cfg(
        device=device,
        automatic_add=automatic_add,
        devices=devices,
        protocols=protocols,
    )
    mock_entry = MockConfigEntry(domain="rfplayer", unique_id="a_player", data=entry_data)
    mock_entry.supports_remove_device = True
    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()
    return mock_entry
