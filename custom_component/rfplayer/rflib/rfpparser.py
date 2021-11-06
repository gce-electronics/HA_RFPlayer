"""Parsers."""

from enum import Enum
import json
import logging
import re
from typing import Any, Callable, Dict, Generator, cast

log = logging.getLogger(__name__)

PACKET_ID_SEP = "_"

PACKET_FIELDS = {
    "bat": "battery",
    "cmd": "command",
    "dtc": "detector",
    "sta": "status",
    "sen": "sensor",
}

UNITS = {
    "bat": None,
    "cmd": None,
    "detector": None,
    "sta": None,
}

DTC_STATUS_LOOKUP = {
    "0": "closed",
    "2": "open",
    "8": "alive",
    "16": "assoc",
}

VALUE_TRANSLATION = cast(
    Dict[str, Callable[[str], str]],
    {
        "detector": lambda x: DTC_STATUS_LOOKUP.get(x, "unknown"),
    },
)

PACKET_HEADER_RE = (
    "^("
    + "|".join(
        [
            "ZIA--",  # command reply
            "ZIA33",  # json reply
        ]
    )
    + ")"
)

packet_header_re = re.compile(PACKET_HEADER_RE)

PacketType = Dict[str, Any]


class PacketHeader(Enum):
    """Packet source identification."""

    master = "10"
    echo = "11"
    gateway = "20"


def valid_packet(packet: str) -> bool:
    """Check if packet is valid."""
    return bool(packet_header_re.match(packet))


def decode_packet(packet: str) -> PacketType:
    """Decode packet."""
    data = cast(PacketType, {"node": PacketHeader.gateway.name})

    # Welcome messages directly send
    if packet.startswith("ZIA--"):
        data["message"] = packet.replace("ZIA--", "")
        return data

    # Protocols
    message = json.loads(packet.replace("ZIA33", ""))["frame"]
    data["protocol"] = message["header"]["protocolMeaning"]

    if data["protocol"] in ["BLYSS", "CHACON"]:
        data["id"] = message["infos"]["id"]
        data["command"] = message["infos"]["subType"]
        data["state"] = message["infos"]["subTypeMeaning"]
    else:
        data["id"] = message["infos"].get("id")
        data["command"] = message["infos"].get("subType")

    return data


def encode_packet(packet: PacketType) -> str:
    """Construct packet string from packet dictionary."""
    # TODO testing for rfplayer
    if packet["protocol"] == "rfdebug":
        return "10;RFDEBUG=%s;" % packet["command"]
    elif packet["protocol"] == "rfudebug":
        return "10;RFUDEBUG=%s;" % packet["command"]
    elif packet["protocol"] == "qrfdebug":
        return "10;QRFDEBUG=%s;" % packet["command"]
    else:
        return "{node};{protocol};{id};{switch};{command};".format(
            node=PacketHeader.master.value, **packet
        )


def serialize_packet_id(packet: PacketType) -> str:
    """Serialize packet identifiers into one reversible string."""

    return PACKET_ID_SEP.join(
        filter(
            None,
            [
                packet.get("protocol", None),  #  "rfplayer"),
                packet.get("id", None),
                packet.get("switch", None),
            ],
        )
    )


def deserialize_packet_id(packet_id: str) -> Dict[str, str]:
    """Deserialize packet id."""
    if packet_id == "rfplayer":
        return {"protocol": "unknown"}

    if packet_id == "ZIA":
        return {"protocol": "ZIA++"}

    if packet_id.startswith("dooya_v4"):
        protocol = "dooya_v4"
        id_switch = packet_id.replace("dooya_v4_", "").split(PACKET_ID_SEP)
    else:
        protocol, *id_switch = packet_id.split(PACKET_ID_SEP)

    assert len(id_switch) < 3

    packet_identifiers = {
        "protocol": protocol,
    }
    if id_switch:
        packet_identifiers["id"] = id_switch[0]
    if len(id_switch) > 1:
        packet_identifiers["switch"] = id_switch[1]

    return packet_identifiers


def packet_events(packet: PacketType) -> Generator[PacketType, None, None]:
    """Handle packet events."""
    field_abbrev = {
        v: k
        for k, v in sorted(
            PACKET_FIELDS.items(), key=lambda x: (x[1], x[0]), reverse=True
        )
    }

    packet_id = serialize_packet_id(packet)
    events = {f: v for f, v in packet.items() if f in field_abbrev}
    for f, v in packet.items():
        log.debug("f:%s,v:%s", f, v)
    for s, v in events.items():
        log.debug("event: %s -> %s", s, v)

    # try:
    #   packet["message"]
    #   yield { "id": packet_id, "message": packet["message"] }
    # except KeyError:
    for sensor, value in events.items():
        log.debug("packet_events, sensor:%s,value:%s", sensor, value)
        unit = packet.get(sensor + "_unit", None)
        yield {
            "id": packet_id + PACKET_ID_SEP + field_abbrev[sensor],
            "sensor": sensor,
            "value": value,
            "unit": unit,
        }
