"""Asyncio protocol implementation of RFplayer."""

import asyncio
from collections.abc import Callable, Coroutine, Sequence
from datetime import timedelta
from fnmatch import fnmatchcase
from functools import partial
import logging
from typing import Any, cast

from serial_asyncio import create_serial_connection

from .rfpparser import (
    PacketType,
    RfPlayerException,
    decode_packet,
    encode_packet,
    packet_events,
    valid_packet,
)

log = logging.getLogger(__name__)

TIMEOUT = timedelta(seconds=5)


class ProtocolBase(asyncio.Protocol):
    """Manage low level rfplayer protocol."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        disconnect_callback: Callable[[Exception | None], None] | None = None,
    ) -> None:
        """Initialize class."""
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        self.transport: asyncio.WriteTransport | None = None
        self.packet = ""
        self.buffer = ""
        self.packet_callback: Callable[[PacketType], None] | None = None
        self.disconnect_callback = disconnect_callback

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Just logging for now."""

        self.transport = cast(asyncio.WriteTransport, transport)
        log.debug("connected")
        self.send_raw_packet("ZIA++HELLO")
        self.send_raw_packet("ZIA++RECEIVER + *")
        self.send_raw_packet("ZIA++FORMAT JSON")
        log.debug("initialized")

    def data_received(self, data: bytes) -> None:
        """Add incoming data to buffer."""
        try:
            decoded_data = data.decode()
        except UnicodeDecodeError:
            invalid_data = data.decode(errors="replace")
            log.warning("Error during decode of data, invalid data: %s", invalid_data)
        else:
            log.debug("received data: %s", decoded_data.strip())
            self.buffer += decoded_data
            self.handle_lines()

    def handle_lines(self) -> None:
        """Assemble incoming data into per-line packets."""
        while "\n\r" in self.buffer:
            line, self.buffer = self.buffer.split("\n\r", 1)
            if valid_packet(line):
                self.handle_raw_packet(line)
            else:
                log.warning("dropping invalid data: %s", line)

    def handle_raw_packet(self, raw_packet: str) -> None:
        """Handle one raw incoming packet."""
        raise NotImplementedError

    def send_raw_packet(self, packet: str) -> None:
        """Encode and put packet string onto write buffer."""
        data = bytes(packet + "\n\r", "utf-8")
        log.debug("writing data: %s", repr(data))
        assert self.transport is not None
        self.transport.write(data)

    def connection_lost(self, exc: Exception | None) -> None:
        """Log when connection is closed, if needed call callback."""
        if exc:
            log.exception("disconnected due to exception")
        else:
            log.info("disconnected because of close/abort.")
        if self.disconnect_callback:
            self.disconnect_callback(exc)


class PacketHandling(ProtocolBase):
    """Handle translating rfplayer packets to/from python primitives."""

    def __init__(
        self,
        *args: Any,
        packet_callback: Callable[[PacketType], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Add packethandling specific initialization.

        packet_callback: called with every complete/valid packet
        received.
        """
        log.debug("PacketHandling")
        super().__init__(*args, **kwargs)
        if packet_callback:
            self.packet_callback = packet_callback

    def handle_raw_packet(self, raw_packet: str) -> None:
        """Parse raw packet string into packet dict."""
        packets = []
        try:
            packets = decode_packet(raw_packet)
        except RfPlayerException:
            log.exception("failed to parse packet data: %s", raw_packet)

        if packets:
            for packet in packets:
                log.debug("decoded packet: %s", packet)
                if "ok" in packet:
                    # handle response packets internally
                    log.debug("command response: %s", packet)
                    self.handle_response_packet(packet)
                else:
                    self.handle_packet(packet)
        else:
            log.warning("no valid packet")

    def handle_packet(self, packet: PacketType) -> None:
        """Process incoming packet dict and optionally call callback."""
        if self.packet_callback:
            # forward to callback
            self.packet_callback(packet)
        else:
            log.debug("packet %s", packet)

    def handle_response_packet(self, packet: PacketType) -> None:
        """Handle response packet."""
        raise NotImplementedError

    def send_packet(self, fields: PacketType) -> None:
        """Concat fields and send packet to gateway."""
        encoded_packet = encode_packet(fields)
        self.send_raw_packet(encoded_packet)

    def send_command(
        self,
        protocol: str,
        command: str,
        device_address: str | None = None,
        device_id: str | None = None,
    ) -> None:
        """Send device command to rfplayer gateway."""
        if device_id is not None:
            self.send_raw_packet(f"ZIA++{command} {protocol} ID {device_id}")
        elif device_address is not None:
            self.send_raw_packet(f"ZIA++{command} {protocol} {device_address}")
        else:
            self.send_raw_packet(f"ZIA++{protocol} {command}")


class CommandSerialization(PacketHandling):
    """Logic for ensuring asynchronous commands are sent in order."""

    def __init__(
        self,
        *args: Any,
        packet_callback: Callable[[PacketType], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Add packethandling specific initialization."""
        log.debug("CommandSerialization")
        super().__init__(*args, **kwargs)
        if packet_callback:
            self.packet_callback = packet_callback
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._last_ack: PacketType | None = None

    def handle_response_packet(self, packet: PacketType) -> None:
        """Handle response packet."""
        log.debug("handle_response_packet")
        self._last_ack = packet
        self._event.set()

    async def send_command_ack(
        self,
        protocol: str,
        command: str,
        device_address: str | None = None,
        device_id: str | None = None,
    ) -> bool:
        """Send command, wait for gateway to repond."""
        async with self._lock:
            self.send_command(protocol, command, device_address, device_id)
            self._event.clear()
            # await self._event.wait()
        return True


class EventHandling(PacketHandling):
    """Breaks up packets into individual events with ids'.

    Most packets represent a single event (light on, measured
    temperature), but some contain multiple events (temperature and
    humidity). This class adds logic to convert packets into individual
    events each with their own id based on packet details (protocol,
    switch, etc).
    """

    def __init__(
        self,
        *args: Any,
        event_callback: Callable[[PacketType], None] | None = None,
        ignore: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Add eventhandling specific initialization."""
        super().__init__(*args, **kwargs)
        self.event_callback = event_callback
        # suppress printing of packets
        log.debug("EventHandling")
        if not kwargs.get("packet_callback"):
            self.packet_callback = lambda x: None
        if ignore:
            log.debug("ignoring: %s", ignore)
            self.ignore = ignore
        else:
            self.ignore = []

    def _handle_packet(self, packet: PacketType) -> None:
        """Event specific packet handling logic."""
        events = packet_events(packet)

        for event in events:
            if self.ignore_event(event["id"]):
                log.debug("ignoring event with id: %s", event)
                continue
            log.debug("got event: %s", event)
            if self.event_callback:
                self.event_callback(event)
            else:
                self.handle_event(event)

    def handle_event(self, event: PacketType) -> None:
        """Handle of incoming event (print)."""
        log.debug("_handle_event")
        string = "{id:<32} "
        if "command" in event:
            string += "{command}"
        elif "version" in event:
            if "hardware" in event:
                string += "{hardware} {firmware} "
            string += "V{version} R{revision}"
        else:
            string += "{value}"
            if event.get("unit"):
                string += " {unit}"

        log.debug(string.format(**event))

    def handle_packet(self, packet: PacketType) -> None:
        """Apply event specific handling and pass on to packet handling."""
        self._handle_packet(packet)
        super().handle_packet(packet)

    def ignore_event(self, event_id: str) -> bool:
        """Verify event id against list of events to ignore."""
        log.debug("ignore_event")
        return any(fnmatchcase(event_id, ignore) for ignore in self.ignore)


class RfplayerProtocol(CommandSerialization, EventHandling):
    """Combine preferred abstractions that form complete Rflink interface."""


# pylint: disable-next=too-many-arguments
def create_rfplayer_connection(
    port: str,
    baud: int = 115200,
    packet_callback: Callable[[PacketType], None] | None = None,
    event_callback: Callable[[PacketType], None] | None = None,
    disconnect_callback: Callable[[Exception | None], None] | None = None,
    ignore: Sequence[str] | None = None,
    loop: asyncio.AbstractEventLoop | None = None,
) -> "Coroutine[Any, Any, tuple[asyncio.BaseTransport, ProtocolBase]]":
    """Create Rflink manager class, returns transport coroutine."""
    if loop is None:
        loop = asyncio.get_event_loop()
    # use default protocol if not specified
    protocol_factory = partial(
        RfplayerProtocol,
        loop=loop,
        packet_callback=packet_callback,
        event_callback=event_callback,
        disconnect_callback=disconnect_callback,
        ignore=ignore if ignore else [],
    )

    # setup serial connection
    conn = create_serial_connection(loop, protocol_factory, port, baud)

    return conn
