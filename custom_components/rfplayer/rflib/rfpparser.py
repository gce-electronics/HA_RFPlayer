"""Parsers."""

import json
import logging
import re
from typing import Any

from .exception import RfPlayerException

log = logging.getLogger(__name__)


# command reply or json event
PACKET_HEADER_RE = r"^(ZIA--|ZIA33)"

packet_header_re = re.compile(PACKET_HEADER_RE)

# FIXME improve typing
PacketType = dict[str, Any]


def valid_packet(packet: str) -> bool:
    """Check if packet is valid."""
    return bool(packet_header_re.match(packet))


# pylint: disable-next=too-many-branches too-many-statements
def decode_packet(packet: str) -> list:
    """Decode packet."""
    packets_found = []
    data = {}

    # Response to any command
    if packet.startswith("ZIA--"):
        data["response"] = packet.replace("ZIA--", "")
        return [data]

    # Protocols
    message = json.loads(packet.replace("ZIA33", ""))["frame"]
    data["protocol"] = message["header"]["protocolMeaning"]

    # FIXME improve typing
    if data["protocol"] in ["JAMMING"]:
        data["device_id"] = message["infos"]["id"]
        data["command"] = "jamming_detection"
        data["state"] = message["infos"]["subType"]
        packets_found.append(data)
    if data["protocol"] in ["BLYSS", "CHACON"]:
        data["device_id"] = message["infos"]["id"]
        data["command"] = "cmd"
        data["state"] = message["infos"]["subTypeMeaning"]
        packets_found.append(data)
    elif data["protocol"] in ["X2D"]:
        data["device_id"] = message["infos"]["id"]
        data["sensor"] = message["infos"]["functionMeaning"]  # FIXME should be a number
        data["state"] = message["infos"]["state"]
        packets_found.append(data)
    elif data["protocol"] in ["OREGON"]:
        data["device_id"] = message["infos"]["adr_channel"]
        for measure in message["infos"]["measures"]:
            measure_data = data.copy()
            measure_data["sensor"] = measure["type"]
            measure_data["state"] = measure["value"]
            measure_data["unit"] = measure["unit"]
            packets_found.append(measure_data)
    else:
        log.warning("Unsupported protocol %s", data["protocol"])

    for p in packets_found:
        event_type = p["sensor"] if "sensor" in p else p["command"]
        p["id"] = "_".join([p["protocol"], p["device_id"], event_type])

    return packets_found


def encode_packet(packet: PacketType) -> str:
    """Construct packet string from packet dictionary."""
    command = str(packet["command"]).upper()
    protocol = str(packet["protocol"]).upper()
    if "id" in packet:
        return f"ZIA++{command} {protocol} ID {packet['id']}"
    if "address" in packet:
        return f"ZIA++{command} {protocol} {packet['address']}"
    raise RfPlayerException("No ID or Address found")
