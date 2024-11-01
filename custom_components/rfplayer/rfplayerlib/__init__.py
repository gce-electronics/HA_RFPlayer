"""Async RfPlayer client."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
import logging
from typing import cast

from serial import SerialException
from serial_asyncio import create_serial_connection

from .device import RfDeviceEvent, RfDeviceEventAdapter
from .protocol import RfPlayerEventData, RfplayerProtocol

_LOGGER = logging.getLogger(__name__)

SIMULATOR_PORT = "/simulator"

RECEIVER_MODES = [
    "*",
    "X10",
    "RTS",
    "VISONIC",
    "BLYSS",
    "CHACON",
    "OREGONV1",
    "OREGONV2",
    "OREGONV3/OWL",
    "DOMIA",
    "X2D",
    "KD101",
    "PARROT",
    "TIC",
    "FS20",
    "JAMMING",
    "EDISIO",
]
"""List of receiver modes."""

DEVICE_PROTOCOLS = [
    "BLYSS",
    "CHACON",
    "DOMIA",
    "EDISIO",
    "FS20",
    "KD101",
    "OREGON",
    "PARROT",
    "RTS",
    "TIC",
    "VISONIC",
    "VISONIC433",
    "VISONIC868",
    "X10",
    "X2D",
    "X2D433",
    "X2D868",
    "X2DELEC",
    "X2DGAS",
    "X2DSHUTTER",
]
"""List of protocol names that could appear either in an incoming JSON packet or as a outgoing command parameter."""

COMMAND_PROTOCOLS = [
    "BLYSS",
    "CHACON",
    "DOMIA",
    "EDISIO",
    "FS20",
    "KD101",
    "PARROT",
    "RTS",
    "VISONIC433",
    "VISONIC868",
    "X10",
    "X2D433",
    "X2D868",
    "X2DELEC",
    "X2DGAS",
    "X2DSHUTTER",
]
"""List of protocol names allowed for outgoing commands."""


class RfPlayerException(Exception):
    """Generic RfPlayer exception."""


@dataclass
class RfPlayerClient:
    """Client to RfPlayer gateway."""

    event_callback: Callable[[RfDeviceEvent], None]
    disconnect_callback: Callable[[Exception | None], None]
    loop: asyncio.AbstractEventLoop
    port: str = "/dev/ttyUSB0"
    baud: int = 115200
    receiver_protocols: list[str] | None = None
    init_commands: str | None = None
    verbose: bool = False
    _protocol: RfplayerProtocol | None = None
    _adapter: RfDeviceEventAdapter | None = None

    async def connect(self) -> None:
        """Open connection with RfPlayer gateway."""

        self._adapter = RfDeviceEventAdapter(device_event_callback=self.event_callback)

        if self.port == SIMULATOR_PORT:
            _LOGGER.info("Connecting to RfPlayer simulator")
            return

        protocol_factory = partial(
            RfplayerProtocol,
            loop=self.loop,
            event_callback=self._adapter.raw_event_callback,
            disconnect_callback=self._disconnect_callback_internal,
            init_script=self._init_script(),
            verbose=self.verbose,
        )
        try:
            (_, protocol) = await create_serial_connection(self.loop, protocol_factory, self.port, self.baud)
        except (SerialException, OSError) as err:
            raise RfPlayerException("Failed to create serial connection") from err
        self._protocol = cast(RfplayerProtocol, protocol)

    def close(self) -> None:
        """Close connection if open."""

        if self._protocol and self._protocol.transport:
            self._protocol.transport.close()
        self._protocol = None

    def send_raw_command(self, command: str) -> None:
        """Send a raw command."""

        if self.port == SIMULATOR_PORT:
            _LOGGER.info("Simulate sending command %s", command)
            return

        if not self._protocol or not self._protocol.transport:
            raise RfPlayerException("Not connected")

        self._protocol.send_raw_command(command)

    async def send_raw_request(self, command: str) -> str:
        """Send a raw request and return response."""

        if not self._protocol or not self._protocol.transport:
            raise RfPlayerException("Not connected")

        return await self._protocol.send_raw_request(command)

    async def simulate_event(self, event_data: dict) -> None:
        """Send an event to the client callback."""
        if not self.connected:
            raise RfPlayerException("Not connected")

        assert self._adapter
        self._adapter.raw_event_callback(RfPlayerEventData(event_data))

    @property
    def connected(self) -> bool:
        """True if the client is connected."""

        return self._protocol is not None or (self.port == SIMULATOR_PORT and self._adapter is not None)

    @property
    def protocol(self):
        """The underlying asyncio protocol."""

        return self._protocol

    def _disconnect_callback_internal(self, ex: Exception | None) -> None:
        self.close()
        self.disconnect_callback(ex)

    def _init_script(self) -> list[str]:
        result = []
        if self.receiver_protocols:
            result.append(f"RECEIVER -* +{' +'.join(self.receiver_protocols)}")
        if self.init_commands:
            result.extend(self.init_commands.splitlines())

        return result
