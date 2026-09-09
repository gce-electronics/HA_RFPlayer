"""HA services for the RfPlayer gateway."""

import voluptuous as vol

from custom_components.rfplayer.const import (
    ATTR_COMMAND,
    ATTR_EVENT_DATA,
    DOMAIN,
    SERVICE_SEND_PAIRING_COMMAND,
    SERVICE_SEND_RAW_COMMAND,
    SERVICE_SIMULATE_EVENT,
)
from custom_components.rfplayer.gateway import Gateway
from custom_components.rfplayer.rfplayerlib import COMMAND_PROTOCOLS
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL
from homeassistant.core import HomeAssistant

SERVICE_SEND_RAW_COMMAND_SCHEMA = vol.Schema({ATTR_COMMAND: str})
SERVICE_SEND_PAIRING_COMMAND_SCHEMA = vol.Schema({CONF_PROTOCOL: vol.In(COMMAND_PROTOCOLS), CONF_ADDRESS: str})
SERVICE_SIMULATE_EVENT_SCHEMA = vol.Schema({ATTR_EVENT_DATA: dict})


async def async_setup_services(hass: HomeAssistant, gateway: Gateway) -> None:
    """Register RFPlayer services."""

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_RAW_COMMAND,
        gateway.async_send_raw_command,
        schema=SERVICE_SEND_RAW_COMMAND_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_PAIRING_COMMAND,
        gateway.async_send_pairing_command,
        schema=SERVICE_SEND_PAIRING_COMMAND_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SIMULATE_EVENT,
        gateway.async_simulate_event,
        schema=SERVICE_SIMULATE_EVENT_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister RFPlayer services."""
    for service in (SERVICE_SEND_RAW_COMMAND, SERVICE_SEND_PAIRING_COMMAND, SERVICE_SIMULATE_EVENT):
        hass.services.async_remove(DOMAIN, service)
