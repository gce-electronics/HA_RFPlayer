"""Short-lived RFPlayer connection checks used before an entry exists."""

import json
import logging

from custom_components.rfplayer.const import DOMAIN
from custom_components.rfplayer.rfplayerlib import SIMULATOR_PORT, RfPlayerClient, RfPlayerException

_LOGGER = logging.getLogger(__name__)


async def async_get_rfplayer_unique_id(device_port: str) -> str | None:
    """Connect briefly and resolve the RFPlayer's stable unique ID."""
    if device_port == SIMULATOR_PORT:
        return f"{DOMAIN}_simulator".lower()

    client: RfPlayerClient | None = None
    try:
        client = RfPlayerClient(
            event_callback=lambda _: None,
            disconnect_callback=lambda _: None,
            port=device_port,
            receiver_protocols=[],
            init_commands=[],
            verbose=True,
        )
        await client.connect()
        raw_status = await client.send_raw_request("STATUS SYSTEM JSON")
        mac = _extract_mac_from_system_status(raw_status)
    except RfPlayerException as exc:
        _LOGGER.warning("RFPlayer %s check failed: %s", device_port, str(exc))
        return None
    else:
        _LOGGER.info("Connection to %s successful: found MAC address %s", device_port, mac)
        return f"{DOMAIN}_{mac}".lower()
    finally:
        if client is not None:
            client.close()


def _extract_mac_from_system_status(raw_status: str) -> str:
    """Extract the RFPlayer MAC suffix from its system status response."""
    status = json.loads(raw_status)
    all_info = status["systemStatus"]["info"]
    mac_info = next((item for item in all_info if str(item.get("n", "")).lower() == "mac"), None)
    if mac_info:
        return str(mac_info["v"])[-8:]
    raise RfPlayerException("Mac address not found")
