"""Unit tests for rfplayer client."""

import asyncio
from typing import cast
from unittest.mock import ANY, Mock

import pytest
from pytest_mock import MockerFixture

from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfplayerProtocol
from tests.rfplayer.constants import OREGON_ADDRESS, OREGON_EVENT_DATA

pytestmark = pytest.mark.unit


async def test_connect_serial(
    test_client: RfPlayerClient,
    test_protocol: RfplayerProtocol,
    mock_serial_connection: Mock,
):
    # GIVEN
    test_client.port = "/dev/ttyUSB0"

    # WHEN
    await test_client.connect()

    # THEN
    assert test_client.protocol == test_protocol
    assert test_client.connected
    mock_serial_connection.assert_called_with(asyncio.get_running_loop(), ANY, "/dev/ttyUSB0", 115200)


async def test_connect_tcp(
    test_client: RfPlayerClient,
    test_protocol: RfplayerProtocol,
    mock_tcp_connection: Mock,
):
    # GIVEN
    test_client.port = "tcp://localhost:1234"

    # WHEN
    await test_client.connect()

    # THEN
    assert test_client.protocol == test_protocol
    assert test_client.connected
    mock_tcp_connection.assert_called_once_with(ANY, "localhost", 1234)


def test_disconnect_callback_closes_client(
    test_client: RfPlayerClient,
    test_protocol: RfplayerProtocol,
    mocker: MockerFixture,
) -> None:
    """Test protocol disconnect closes the client before notifying."""
    callback = mocker.patch.object(test_client, "disconnect_callback")

    test_client._protocol = test_protocol  # noqa: SLF001

    test_client._disconnect_callback_internal(None)  # noqa: SLF001

    assert test_client.protocol is None
    callback.assert_called_once_with(None)


async def test_simulator(mocker: MockerFixture):
    # GIVEN
    logger_mock = mocker.patch("custom_components.rfplayer.rfplayerlib._LOGGER")
    event_callback = Mock()
    test_client = RfPlayerClient(
        event_callback=event_callback,
        disconnect_callback=Mock(),
        port="/simulator",
        receiver_protocols=[],
        init_commands=[],
        verbose=False,
    )
    assert not test_client.connected

    # WHEN
    await test_client.connect()
    await test_client.send_raw_command("a command")
    await test_client.simulate_event(OREGON_EVENT_DATA)

    # THEN
    assert test_client.connected
    assert logger_mock.info.call_args_list[0] == (("Connecting to RfPlayer simulator",),)
    assert logger_mock.info.call_args_list[1] == (("Simulate sending command %s", "a command"),)
    event = cast(RfDeviceEvent, event_callback.call_args.args[0])  # First argument of last call
    assert event.device == RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800")
    assert event.data == OREGON_EVENT_DATA


async def test_receiver_protocols(
    test_client: RfPlayerClient,
    test_protocol: RfplayerProtocol,
    mock_serial_connection: Mock,
):
    # GIVEN
    # test_client

    # WHEN
    await test_client.connect()

    # THEN
    protocol_factory = mock_serial_connection.call_args[0][1]
    protocol = protocol_factory()
    assert protocol.init_script == ["FORMAT JSON", "RECEIVER -* +X2D +RTS", "PING", "HELLO"]


async def test_send_command_connected(test_client: RfPlayerClient, test_protocol: RfplayerProtocol):
    # GIVEN
    await test_client.connect()

    # WHEN
    body = "FORMAT JSON"
    await test_client.send_raw_command(body)

    # THEN
    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(b"ZIA++FORMAT JSON\n\r")


async def test_send_command_disconnected(test_client: RfPlayerClient):
    # GIVEN
    assert not test_client.connected

    with pytest.raises(RfPlayerException):
        # WHEN
        await test_client.send_raw_command("")

        # THEN raise


async def test_send_request_connected(test_client: RfPlayerClient, test_protocol: RfplayerProtocol):
    # GIVEN
    await test_client.connect()

    # WHEN
    body = "HELLO"
    await test_client.send_raw_command(body)

    # THEN
    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(b"ZIA++HELLO\n\r")


async def test_send_request_disconnected(test_client: RfPlayerClient):
    # GIVEN
    assert not test_client.connected

    with pytest.raises(RfPlayerException):
        # WHEN
        await test_client.send_raw_command("")

        # THEN raise
