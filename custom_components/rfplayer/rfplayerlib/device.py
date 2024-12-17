"""RfPlayer device info extraction."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
import re
from typing import Any

from .protocol import RfPlayerEventData

_LOGGER = logging.getLogger(__name__)

UNKNOWN_INFO = "unknown"


@dataclass
class RfDeviceId:
    """Identifiers of a RF device or the RfPlayer gateway itself."""

    X10_PATTERN = re.compile("([A-P])(1[0-6]|[1-9])")
    HEX_PATTERN = re.compile("X([0-9A-F]+)")
    DEC_PATTERN = re.compile("[0-9]+")

    protocol: str
    model: str | None
    _address: str
    _integer_address: int

    def __init__(self, protocol: str, address: str, *, model: str | None = None):
        """Create a new RF device id."""

        self.protocol = protocol
        self.address = address
        self.model = model

    @property
    def address(self) -> str:
        """The device address."""

        return self._address

    @address.setter
    def address(self, value: str) -> None:
        self._address = value
        self._integer_address = self._address_to_integer(value)

    @property
    def integer_address(self) -> int:
        """Read-only integer device address."""

        return self._integer_address

    @property
    def id_string(self) -> str:
        """Build a unique device id for the device."""

        return f"{self.protocol}-{self.integer_address}"

    @property
    def group_code(self) -> str | None:
        """Group code extracted from address for protocols supporting group commands."""

        # Assume that everything but the last 2 bytes is a housecode / pairing id for all protocols
        # and that any group command applies to the whole housecode
        return str(self.integer_address & 0xFFFFFF00)

    @property
    def unit_code(self) -> str | None:
        """Unit code extracted from address for protocols supporting group commands."""

        # RfPlayer ID for commands must be 0-255
        return str(self.integer_address & 0x000000FF)

    @staticmethod
    def is_valid_address(address: str) -> bool:
        """Check if the address is valid."""

        try:
            RfDeviceId._address_to_integer(address)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def _address_to_integer(address: str) -> int:
        upper_address = address.upper()
        m = RfDeviceId.DEC_PATTERN.fullmatch(upper_address)
        if m:
            return int(upper_address)
        m = RfDeviceId.X10_PATTERN.fullmatch(upper_address)
        if m:
            return ((ord(m.group(1)) - ord("A")) * 16 + int(m.group(2))) - 1
        m = RfDeviceId.HEX_PATTERN.fullmatch(upper_address)
        if m:
            return int(m.group(1), 16)
        raise ValueError("Invalid address")


@dataclass
class RfDeviceEvent:
    """Device-oriented event after processing a raw RfPlayer event."""

    device: RfDeviceId
    data: RfPlayerEventData


@dataclass
class RfDeviceEventAdapter:
    """Extract RF device information from a raw RfPlayer event."""

    device_event_callback: Callable[[RfDeviceEvent], None]

    def raw_event_callback(self, event_data: RfPlayerEventData):
        """Convert raw RfPlayer event to RF Device event."""

        device = self._parse_json_device(event_data)
        self.device_event_callback(RfDeviceEvent(device=device, data=event_data))

    def _convert_raw_model(self, raw_model: str) -> str:
        if raw_model.lower() in ["on", "off"]:
            return "switch"

        return raw_model

    def _get_model(self, infos: dict[str, Any]) -> str:
        for key in ["id_PHYMeaning", "subTypeMeaning"]:
            if key in infos:
                return self._convert_raw_model(infos[key])
        return UNKNOWN_INFO

    def _get_address(self, infos: dict[str, Any]) -> str:
        for key in ["id", "id_channel", "adr_channel"]:
            if key in infos:
                return infos[key]
        return UNKNOWN_INFO

    def _parse_json_device(self, json_packet: dict[str, Any]) -> RfDeviceId:
        header = json_packet["frame"]["header"]
        infos = json_packet["frame"]["infos"]
        protocol = header["protocolMeaning"]
        return RfDeviceId(
            protocol=protocol,
            address=self._get_address(infos),
            model=self._get_model(infos),
        )
