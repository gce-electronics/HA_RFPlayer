"""Helpers to handle RF device metadata."""

import json

from custom_components.rfplayer.device_profiles import ProfileRegistry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.const import CONF_ADDRESS, CONF_EVENT_DATA, CONF_MODEL, CONF_PROFILE_NAME, CONF_PROTOCOL

from .const import CONF_REDIRECT_ADDRESS, DOMAIN


def get_device_id_string_from_identifiers(
    identifiers: set[tuple[str, str]],
) -> str | None:
    """Calculate the device id from a device identifier."""
    return next((x[1] for x in identifiers if x[0] == DOMAIN), None)


def get_identifiers_from_device_id(
    device: RfDeviceId,
) -> set[tuple[str, str]]:
    """Calculate the device identifier from a device id."""
    return {(DOMAIN, device.id_string)}


def build_device_id_from_device_info(device_info: dict) -> RfDeviceId:
    """Create an RF device event from a device info map."""
    protocol = device_info[CONF_PROTOCOL]
    address = device_info[CONF_ADDRESS]
    model = device_info.get(CONF_MODEL)
    return RfDeviceId(protocol=protocol, address=address, model=model)


def build_event_data_from_device_info(device_info: dict) -> RfPlayerEventData | None:
    """Create an RF device event from a device info map."""
    event_json_data = device_info.get(CONF_EVENT_DATA)
    return RfPlayerEventData(json.loads(event_json_data)) if event_json_data else None


def build_device_info_from_event(profile_registy: ProfileRegistry, event: RfDeviceEvent) -> dict[str, str | None]:
    """Create a device info map from a RF device event."""

    device_info: dict[str, str | None] = {}
    device_info[CONF_PROTOCOL] = event.device.protocol
    device_info[CONF_ADDRESS] = event.device.address
    device_info[CONF_MODEL] = event.device.model
    device_info[CONF_REDIRECT_ADDRESS] = None
    device_info[CONF_PROFILE_NAME] = profile_registy.get_profile_name_from_event(event.data)
    device_info[CONF_EVENT_DATA] = json.dumps(event.data)
    return device_info
