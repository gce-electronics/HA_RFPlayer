"""HA services for the RfPlayer gateway."""

import voluptuous as vol

from custom_components.rfplayer.const import ATTR_COMMAND, ATTR_EVENT_DATA, DOMAIN
from custom_components.rfplayer.gateway import Gateway
from custom_components.rfplayer.rfplayerlib import COMMAND_PROTOCOLS
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL
from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_SEND_RAW_COMMAND = "send_raw_command"
SERVICE_SEND_PAIRING_COMMAND = "send_pairing_command"
SERVICE_SIMULATE_EVENT = "simulate_event"

SERVICE_SEND_RAW_COMMAND_SCHEMA = vol.Schema({ATTR_COMMAND: str})
SERVICE_SEND_PAIRING_COMMAND_SCHEMA = vol.Schema({CONF_PROTOCOL: vol.In(COMMAND_PROTOCOLS), CONF_ADDRESS: str})
SERVICE_SIMULATE_EVENT_SCHEMA = vol.Schema({ATTR_EVENT_DATA: dict})


async def async_setup_services(hass: HomeAssistant, gateway: Gateway) -> None:
    """Register RFPlayer services."""

    async def async_send_raw_command(call: ServiceCall) -> None:
        """Send a raw command to the RfPlayer gateway."""
        command = call.data[ATTR_COMMAND]
        await gateway.async_send_raw_command(command)

    async def async_send_pairing_command(call: ServiceCall) -> None:
        """Send a pairing command to the RfPlayer gateway."""
        device_id = RfDeviceId(protocol=call.data[CONF_PROTOCOL], address=call.data[CONF_ADDRESS])
        await gateway.async_send_raw_command(f"ASSOC {device_id.protocol} ID {device_id.integer_address}")

    async def async_simulate_event(call: ServiceCall) -> None:
        """Simulate an event from a device."""
        await gateway.async_simulate_event(call.data[ATTR_EVENT_DATA])

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_RAW_COMMAND,
        async_send_raw_command,
        schema=SERVICE_SEND_RAW_COMMAND_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_PAIRING_COMMAND,
        async_send_pairing_command,
        schema=SERVICE_SEND_PAIRING_COMMAND_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SIMULATE_EVENT,
        async_simulate_event,
        schema=SERVICE_SIMULATE_EVENT_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister RFPlayer services."""
    for service in (SERVICE_SEND_RAW_COMMAND, SERVICE_SEND_PAIRING_COMMAND, SERVICE_SIMULATE_EVENT):
        hass.services.async_remove(DOMAIN, service)
