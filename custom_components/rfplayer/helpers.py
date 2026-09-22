"""Helpers to handle RF device metadata."""

import json

from custom_components.rfplayer.config_options import RfPlayerDeviceInfo
from custom_components.rfplayer.const import DOMAIN
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData


def get_device_canonical_id_from_identifiers(
    identifiers: set[tuple[str, str]],
) -> str | None:
    """Retrieve the rf device canonical id from HA identifiers."""
    return next((x[1] for x in identifiers if x[0] == DOMAIN), None)


def get_identifiers_from_device_id(
    device: RfDeviceId,
) -> tuple[str, str]:
    """Calculate the device identifier from a device id."""
    return (DOMAIN, device.canonical_id)


def build_event_data_from_device_info(device_info: RfPlayerDeviceInfo) -> RfPlayerEventData | None:
    """Create an RF device event from a device info map."""
    event_json_data = device_info.event_data
    return RfPlayerEventData(json.loads(event_json_data)) if event_json_data else None
