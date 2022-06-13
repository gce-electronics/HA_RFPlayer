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
    "tmp": "temperature",
    "temp": "SET_TEMPERATURE",
    "hyg": "hygrometry",
    "nrj": "energy",
    "pow": "power",
    "pw1": "P1",
    "pw2": "P2",
    "pw3": "P3",
}

UNITS = {
    "bat": None,
    "cmd": None,
    "dtc": None,
    "hyg": "%",
    "hygrometry": "%",
    "nrj": "Wh",
    "energy": "Wh",
    "pow": "W",
    "power": "W",
    "pw1": "W",
    "p1": "W",
    "pw2": "W",
    "p2": "W",
    "pw3": "W",    
    "p3": "W", 
    "sen": None,
    "sta": None,
    "tmp": "°C",
    "temperature": "°C",
#####
}

DTC_STATUS_LOOKUP = {
    "0": "closed",
    "2": "open",
    "8": "alive",
    "16": "assoc",
    "18": "test",

#    Pour intégration future EDISIO
    # "9": "open",
    # "96": "off",
    # "97": "hors_gel",
    # "98": "eco",
    # "99": "confort",
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


def decode_packet(packet: str) -> list:
    """Decode packet."""
    packets_found = []
    data = cast(PacketType, {"node": PacketHeader.gateway.name})

    # Welcome messages directly send
    if packet.startswith("ZIA--"):
        data["message"] = packet.replace("ZIA--", "")
        return [data]

 
    if packet.startswith("ZIA33"):
        message = json.loads(packet.replace("ZIA33", ""))["frame"]
    data["protocol"] = message["header"]["protocolMeaning"]

    if data["protocol"] in ["BLYSS", "CHACON", "JAMMING"]:
        data["id"] = message["infos"]["id"]
        data["command"] = message["infos"]["subType"]
        data["state"] = message["infos"]["subTypeMeaning"]
        packets_found.append(data)

#    """Decode packet X2D ajout @jaroslawp."""
#   Voir https://github.com/gce-electronics/HA_RFPlayer/pull/12

    elif data["protocol"] in ["X2D"]:
        data["id"] = message["infos"]["id"]
        if message["infos"]["subTypeMeaning"] == 'Detector/Sensor':
          value = VALUE_TRANSLATION['detector'](message["infos"]["qualifier"]) 
          data["command"] = value
          data["state"] = value
        else:
          data["command"] = message["infos"]["subTypeMeaning"]
          data["state"] = message["infos"]["qualifier"]
        packets_found.append(data)
#        

    elif data["protocol"] in ["OREGON", "OWL"]:
        data["id"] = message["infos"]["adr_channel"]
        data["hardware"] = message["infos"]["id_PHYMeaning"]
        for measure in message["infos"]["measures"]:
            measure_data = data.copy()
            measure_data["command"] = measure["value"]
            measure_data["state"] = measure["value"]
            measure_data["unit"] = measure["unit"]
            measure_data["type"] = measure["type"]
            measure_data["id"]  = message["infos"]["adr_channel"]
            measure_data["id"] += measure_data["type"]
            packets_found.append(measure_data)

    elif data["protocol"] in ["EDISIO"]:
        data["id"] = message["infos"]["id"]
        data["hardware"] = message["infos"]["infoMeaning"]
        data["state"] = message["infos"]["subTypeMeaning"]
        data["type"] = message["infos"]["subTypeMeaning"]
        if data["state"] in ["SET_TEMPERATURE"]:
            data["command"] = message["infos"]["add0"]
            data["unit"] = "°C"
        elif data["state"] in ["TOGGLE"]:
            data["command"] = message["infos"]["qualifier"]
        elif data["state"] in ["DIM-A"]:
            data["command"] = message["infos"]["qualifier"]
        else:
            data["command"] = message["infos"]["subType"]
            data["state"] = True #ajout pour state vide
        packets_found.append(data)

    elif data["protocol"] in ["RTS", "VISONIC"]:
        data["id"] = message["infos"]["id"]
        data["state"] = message["infos"]["subTypeMeaning"]
        data["command"] = message["infos"]["qualifierMeaning"]["flags"]
#    """Modification retour, voir pour supprimer [] ou se servir du qualifier et de translation 'detector'."""  
        if data["command"] == ['Down/Off']:
            data["command"] = "Down/Off"
        elif data["command"] == ['My']:
            data["command"] = "MY"
        elif data["command"] == ['Up/On']:
            data["command"] = "Up/On"
        elif data["command"] == ['Assoc']:
            data["command"] = "Assoc"
        elif data["command"] == ['Tamper','Alarm','LowBatt']:
            data["command"] = "Tamper, Alarm, LowBatt"
        elif data["command"] == ['Tamper','Alarm','LowBatt','Supervisor/Alive']:
            data["command"] = "Tamper, Alarm, LowBatt, Supervisor/Alive"
        elif data["command"] == ['LowBatt','Supervisor/Alive']:
            data["command"] = "LowBatt, Supervisor/Alive"
        elif data["command"] == ['button/command']:
            data["command"] = "button/command"
        packets_found.append(data)

    else:
        data["id"] = message["infos"].get("id")
        data["command"] = message["infos"].get("subType")
        packets_found.append(data)

    return packets_found


def encode_packet(packet: PacketType) -> str:
    """Construct packet string from packet dictionary."""
    command = str(packet["command"]).upper()
    protocol = str(packet["protocol"]).upper()
    if "id" in packet:
        return f"ZIA++{command} {protocol} ID {packet['id']}"
    if "address" in packet:
        return f"ZIA++{command} {protocol} {packet['address']}"
    else:
        return f"ZIA++{command} {protocol}"
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
    """Handle packet events."""
    field_abbrev = {
        v: k
        for k, v in sorted(
            PACKET_FIELDS.items(), key=lambda x: (x[1], x[0]), reverse=True
        )
    }

    packet_id = serialize_packet_id(packet)
    # pour récup unit remise à none
    unit = None
    events = {f: v for f, v in packet.items() if f in field_abbrev}
    for f, v in packet.items():
        log.debug("f:%s,v:%s", f, v)
#   Voir pour récup unité et type
        if f == "unit":
            unit = v
        if f == "type":
            type = v
###
    for s, v in events.items():
        log.debug("event: %s -> %s", s, v)

    for sensor, value in events.items():
        log.debug("packet_events, sensor:%s,value:%s", sensor, value)
    
        yield {
            "id": packet_id + PACKET_ID_SEP + field_abbrev[sensor],
            "sensor": sensor,
            "value": value,
            "unit": unit,
        }

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
