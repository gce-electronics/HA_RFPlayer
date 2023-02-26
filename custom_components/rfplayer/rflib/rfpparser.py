"""Parsers."""

from enum import Enum
import json
import logging
import re
from typing import Any, Callable, Dict, Generator, cast
from .protocols import *
import traceback

log = logging.getLogger(__name__)

PACKET_ID_SEP = "_"

PACKET_FIELDS = {
    "bat": "battery_level",
    "cmd": "command",
    "dtc": "detector",
    "sta": "status",
    "sen": "sensor",
    "cov": "cover",
    "swi":"switch",
    "tem":"temperature",
    "hyg":"hygrometry",
    "prs":"pressure",
    "alm":"alarm",
    "tmr":"tamper",
    "bt1":"button1",
    "bt2":"button2",
    "bt3":"button3",
    "bt4":"button4",
    "spd":"speed",
    "dir":"direction",
    "uv":"uv",
    "pow":"Power",
    "P1":"P1",
    "P2":"P2",
    "P3":"P3",
    "TRN":"TotalRain",
    "Rai":"Rain",
    "fnc":"functionMeaning",
    "sta":"stateMeaning",
    "mod":"modeMeaning",
    "d0":"d0",
    "d1":"d1",
    "d2":"d2",
    "d3":"d3",
}

RTS_ELEM = {
    "0": "shu",
    "1": "por",
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
    "18": "test",
}

RTS_STATUS_LOOKUP = {
    "1" : "DOWN", #Down /OFF
    "4" : "MY", #My
    "7" : "UP", #Up /ON
    "13" : "ASSOC",
    
    "5" : "LEFT", #Left button
    "6" : "RIGHT", #Right button
}


VALUE_TRANSLATION = cast(
    Dict[str, Callable[[str], str]],
    {
        "detector": lambda x: DTC_STATUS_LOOKUP.get(x, "unknown"),
        "rts_status": lambda x: RTS_STATUS_LOOKUP.get(x, "unknown"),
        "rts_elem": lambda x: RTS_ELEM.get(x, "unknown"),
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


def decode_packet(packet: str) -> list:
    """Decode packet."""
    packets_found = []
    data = cast(PacketType, {"node": PacketHeader.gateway.name})

    # Welcome messages directly send
    if packet.startswith("ZIA--"):
        data["message"] = packet.replace("ZIA--", "")
        return [data]

    # Protocols
    message = json.loads(packet.replace("ZIA33", ""))["frame"]
    data["protocol"] = message["header"]["protocolMeaning"]

    NewMotor=False


    try:
        packets_found.append(globals()["_".join([data["protocol"],"decode"])](data,message,PacketHeader.gateway.name))
        NewMotor=True
    except Exception as e:
        log.error("Protocol %s not implemented : %s", str(data["protocol"]),str(e))
        log.debug("Trace : %s",traceback.format_exc())
        log.debug("Message : %s", str(message))

    #if packets_found==[None]:
    #    log.error("No packets found in %s", str(message))
    #log.debug("Packets Found : %s", str(packets_found))
    return packets_found

def encode_packet(packet: PacketType) -> str:
    """Construct packet string from packet dictionary."""
    command = str(packet["command"]).upper()
    protocol = str(packet["protocol"]).upper()
    if "id" in packet:
        return f"ZIA++{command} {protocol} ID {packet['id']}"
    if "address" in packet:
        return f"ZIA++{command} {protocol} {packet['address']}"
    raise Exception("No ID or Address found")


def serialize_packet_id(packet: PacketType) -> str:
    """Serialize packet identifiers into one reversible string."""
    return PACKET_ID_SEP.join(
        filter(
            None,
            [
                packet.get("protocol", None),
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

    if packet_id.lower().startswith("chacon"):
        return {
            "protocol": "chacon",
            "address": packet_id.split(PACKET_ID_SEP)[1],
        }

    if packet_id.startswith("dooya_v4"):
        return {
            "protocol": "dooya_v4",
            "id": packet_id.replace("dooya_v4_", "").split(PACKET_ID_SEP)[0],
            "switch": packet_id.replace("dooya_v4_", "").split(PACKET_ID_SEP)[0],
        }

    packet_id_splited = packet_id.split(PACKET_ID_SEP)
    packet = {
        "protocol": packet_id_splited[0],
        "id": packet_id_splited[1],
    }
    if len(packet_id_splited) > 2:
        packet["switch"] = packet_id_splited[2]

    return packet


def packet_events(packet: PacketType) -> Generator[PacketType, None, None]:
    platform=None
    #log.debug("packet:%s", str(packet))
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
        #log.debug("f:%s,v:%s", f, v)
        if f == "platform":
            platform=v
        if f == "protocol":
            protocol=v
    for sensor, value in events.items():
        #log.debug("packet_events, sensor:%s,value:%s", sensor, value)
        unit = packet.get(sensor + "_unit", None)
        yield {
            "id": packet_id + field_abbrev[sensor] + PACKET_ID_SEP + field_abbrev[sensor],
            sensor: value,
            "value":value,
            "unit": unit,
            "platform": platform,
            "protocol": protocol
        }


