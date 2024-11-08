"""RfPlayer device info extraction."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from .protocol import RfPlayerEventData

_LOGGER = logging.getLogger(__name__)

UNKNOWN_INFO = "unknown"


@dataclass
class RfDeviceId:
    """Identifiers of a RF device or the RfPlayer gateway itself."""

    protocol: str
    address: str
    model: str | None

    def __init__(self, protocol: str, address: str, *, model: str | None = None):
        """Create a new RF device id."""

        self.protocol = protocol
        self.address = address
        self.model = model

    @property
    def id_string(self) -> str:
        """Build a unique device id for the device."""

        return f"{self.protocol}-{self.address}"

    @property
    def group_code(self) -> str | None:
        """Group code extracted from address for protocols supporting group commands."""

        # Assume that everything but the last 2 bytes is a housecode / pairing id for all protocols
        # and that any group command applies to the whole housecode
        return str(int(self.address) & 0xFFFFFF00)

    @property
    def unit_code(self) -> str | None:
        """Unit code extracted from address for protocols supporting group commands."""

        # RfPlayer ID for commands must be 0-255
        return str(int(self.address) & 0x000000FF)


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
