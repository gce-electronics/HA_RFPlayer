"""Async RfPlayer low-level protocol."""

import asyncio
from collections.abc import Callable
import json
import logging
from typing import cast

_LOGGER = logging.getLogger(__name__)

END_OF_LINE = "\n\r"
PACKET_HEADER_LEN = 5
MINIMUM_SCRIPT = ["FORMAT JSON"]


class RfPlayerEventData(dict):
    """RfPlayer JSON packet event data."""


def _valid_packet(line: str):
    return len(line) >= PACKET_HEADER_LEN


def _command_error(line: str):
    return line.startswith(("error request number", "Syntax error:"))


class RfplayerProtocol(asyncio.Protocol):
    """Manage low level rfplayer protocol."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        event_callback: Callable[[RfPlayerEventData], None],
        disconnect_callback: Callable[[Exception | None], None],
        init_script: list[str] | None,
        verbose: bool,
    ) -> None:
        """Initialize class."""

        self.loop = loop
        self.transport: asyncio.WriteTransport | None = None
        self.event_callback = event_callback
        self.disconnect_callback = disconnect_callback
        complete_init_script = list(MINIMUM_SCRIPT)
        complete_init_script.extend(init_script or [])
        self.init_script = complete_init_script
        self._init_tasks: set[asyncio.Task] = set()
        self.verbose = verbose
        self.buffer = ""
        self.command_lock = asyncio.Lock()
        self.command_event = asyncio.Event()
        self.response_message = ""

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Just logging for now."""
        self.transport = cast(asyncio.WriteTransport, transport)
        for command in self.init_script:
            task = self.loop.create_task(self.send_raw_command(command))
            self._init_tasks.add(task)
            task.add_done_callback(self._init_tasks.discard)

    def data_received(self, data: bytes) -> None:
        """Add incoming data to buffer."""
        try:
            decoded_data = data.decode()
        except UnicodeDecodeError:
            invalid_data = data.decode(errors="replace")
            _LOGGER.warning("Failed to decode received data: %s", invalid_data)
        else:
            if self.verbose:
                _LOGGER.debug("data received: %s", decoded_data)
            self.buffer += decoded_data
            self.handle_lines()

    def handle_lines(self) -> None:
        """Assemble incoming data into per-line packets."""
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip("\0 \t\r")
            if _valid_packet(line):
                _LOGGER.debug("packet received: %s", line)
                self.handle_raw_packet(line)
            elif line:
                _LOGGER.warning("dropping invalid data: %s", line)

    def handle_raw_packet(self, raw_packet: str) -> None:
        """Handle one raw incoming packet."""
        header = raw_packet[0:5]
        body = raw_packet[5:]
        if header == "ZIA--":
            self.response_message = body
            self.command_event.set()
        elif header == "ZIA33":
            try:
                self.event_callback(cast(RfPlayerEventData, json.loads(body)))
            except json.JSONDecodeError as e:
                _LOGGER.warning("Invalid JSON packet: %s", e)
        elif header in ["ZIA00", "ZIA11", "ZIA22", "ZIA44", "ZIA66"]:
            _LOGGER.warning("unsupported packet format: %s", header)
            _LOGGER.debug("packet body: %s", body)
        elif _command_error(raw_packet):
            _LOGGER.warning("Command error: %s", raw_packet)
        else:
            _LOGGER.warning("dropping invalid packet: %s", raw_packet)

    async def _do_send_raw_command(self, command: str) -> None:
        """Encode and put packet string onto write buffer."""
        self.response_message = ""
        self.command_event.clear()
        data = bytes(f"ZIA++{command}{END_OF_LINE}", "utf-8")
        _LOGGER.debug("sending raw packet: %s", repr(data))
        if self.transport:
            self.transport.write(data)
        else:
            _LOGGER.warning("Command not sent: not connected")

    async def send_raw_command(self, command: str) -> None:
        """Send a command but expect no response."""
        async with self.command_lock:
            await self._do_send_raw_command(command)
            # A command has no ack packet.
            # RfPlayer only sends an error packet if the command is invalid.
            # We could have waited before returning to try to catch the error packet.
            # But the required delay to make sure we always receive
            # the errors is too long to be usable (~5s)

    async def send_raw_request(self, request: str) -> str:
        """Send a request and wait for a response."""
        async with self.command_lock:
            await self._do_send_raw_command(command=request)
            async with asyncio.timeout(60):
                await self.command_event.wait()
                return self.response_message[:]

    def connection_lost(self, exc: Exception | None) -> None:
        """Forward to disconnect callback."""
        self.disconnect_callback(exc)
