"""Unit tests for rfplayer client."""

from typing import cast
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfplayerProtocol
from tests.rfplayer.constants import OREGON_ADDRESS, OREGON_EVENT_DATA


@pytest.mark.asyncio
async def test_connect(
    test_client: RfPlayerClient,
    test_protocol: RfplayerProtocol,
    serial_connection_mock: Mock,
):
    # GIVEN
    # test_client

    # WHEN
    await test_client.connect()

    # THEN
    assert test_client.protocol == test_protocol
    assert test_client.connected
    serial_connection_mock.assert_called_once()


@pytest.mark.asyncio
async def test_simulator(mocker: MockerFixture):
    # GIVEN
    logger_mock = mocker.patch("custom_components.rfplayer.rfplayerlib._LOGGER")
    event_callback = Mock()
    test_client = RfPlayerClient(
        event_callback=event_callback, disconnect_callback=Mock(), loop=Mock(), port="/simulator"
    )
    assert not test_client.connected

    # WHEN
    await test_client.connect()
    test_client.send_raw_command("a command")
    await test_client.simulate_event(OREGON_EVENT_DATA)

    # THEN
    assert test_client.connected
    assert logger_mock.info.call_args_list[0] == (("Connecting to RfPlayer simulator",),)
    assert logger_mock.info.call_args_list[1] == (("Simulate sending command %s", "a command"),)
    event = cast(RfDeviceEvent, event_callback.call_args.args[0])  # First argument of last call
    assert event.device == RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800")
    assert event.data == OREGON_EVENT_DATA


@pytest.mark.asyncio
async def test_receiver_protocols(
    test_client: RfPlayerClient,
    test_protocol: RfplayerProtocol,
    serial_connection_mock: Mock,
):
    # GIVEN
    # test_client

    # WHEN
    await test_client.connect()

    # THEN
    protocol_factory = serial_connection_mock.call_args[0][1]
    protocol = protocol_factory()
    assert protocol.init_script == ["FORMAT JSON", "RECEIVER -* +X2D +RTS", "PING", "HELLO"]


@pytest.mark.asyncio
async def test_send_command_connected(test_client: RfPlayerClient, test_protocol: RfplayerProtocol):
    # GIVEN
    await test_client.connect()

    # WHEN
    body = "FORMAT JSON"
    test_client.send_raw_command(body)

    # THEN
    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(b"ZIA++FORMAT JSON\n\r")


def test_send_command_disconnected(test_client: RfPlayerClient):
    # GIVEN
    assert not test_client.connected

    with pytest.raises(RfPlayerException):
        # WHEN
        test_client.send_raw_command("")

        # THEN raise


@pytest.mark.asyncio
async def test_send_request_connected(test_client: RfPlayerClient, test_protocol: RfplayerProtocol):
    # GIVEN
    await test_client.connect()

    # WHEN
    body = "HELLO"
    test_client.send_raw_command(body)

    # THEN
    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(b"ZIA++HELLO\n\r")


def test_send_request_disconnected(test_client: RfPlayerClient):
    # GIVEN
    assert not test_client.connected

    with pytest.raises(RfPlayerException):
        # WHEN
        test_client.send_raw_command("")

        # THEN raise
