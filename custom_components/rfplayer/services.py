"""HA services for the RfPlayer gateway."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # HA 2026.10+ types its APIs with probatio and aliases voluptuous to it at runtime
    import probatio as vol
else:
    import voluptuous as vol

from custom_components.rfplayer.const import ATTR_COMMAND, ATTR_EVENT_DATA, DOMAIN
from custom_components.rfplayer.gateway import Gateway
from custom_components.rfplayer.rfplayerlib import COMMAND_PROTOCOLS
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

SERVICE_SEND_RAW_COMMAND = "send_raw_command"
SERVICE_SEND_PAIRING_COMMAND = "send_pairing_command"
SERVICE_SIMULATE_EVENT = "simulate_event"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
DATA_GATEWAYS = f"{DOMAIN}_gateways"

SERVICE_SEND_RAW_COMMAND_SCHEMA = vol.Schema({ATTR_COMMAND: str, vol.Optional(ATTR_CONFIG_ENTRY_ID): str})
SERVICE_SEND_PAIRING_COMMAND_SCHEMA = vol.Schema(
    {CONF_PROTOCOL: vol.In(COMMAND_PROTOCOLS), CONF_ADDRESS: str, vol.Optional(ATTR_CONFIG_ENTRY_ID): str}
)
SERVICE_SIMULATE_EVENT_SCHEMA = vol.Schema({ATTR_EVENT_DATA: dict, vol.Optional(ATTR_CONFIG_ENTRY_ID): str})


async def async_setup_services(hass: HomeAssistant, gateway: Gateway) -> None:
    """Register RFPlayer services once and make the gateway available to them."""
    gateways: dict[str, Gateway] = hass.data.setdefault(DATA_GATEWAYS, {})
    gateways[gateway.entry.entry_id] = gateway

    if hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_COMMAND):
        return

    def get_gateway(call: ServiceCall) -> Gateway:
        """Resolve an explicitly selected gateway, or the only configured one."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        if entry_id is not None:
            selected_gateway = gateways.get(entry_id)
            if selected_gateway is None:
                raise HomeAssistantError(f"RFPlayer config entry {entry_id} is not loaded")
            return selected_gateway
        if len(gateways) == 1:
            return next(iter(gateways.values()))
        if not gateways:
            raise HomeAssistantError("No RFPlayer gateways are loaded")
        raise HomeAssistantError("Specify config_entry_id when more than one RFPlayer gateway is loaded")

    async def async_send_raw_command(call: ServiceCall) -> None:
        """Send a raw command to the RfPlayer gateway."""
        command = call.data[ATTR_COMMAND]
        await get_gateway(call).async_send_raw_command(command)

    async def async_send_pairing_command(call: ServiceCall) -> None:
        """Send a pairing command to the RfPlayer gateway."""
        device_id = RfDeviceId(protocol=call.data[CONF_PROTOCOL], address=call.data[CONF_ADDRESS])
        await get_gateway(call).async_send_pairing_command(device_id)

    async def async_simulate_event(call: ServiceCall) -> None:
        """Simulate an event from a device."""
        await get_gateway(call).async_simulate_event(call.data[ATTR_EVENT_DATA])

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


async def async_unload_services(hass: HomeAssistant, gateway: Gateway) -> None:
    """Remove an unloaded gateway and unregister services when none remain."""
    gateways: dict[str, Gateway] = hass.data.get(DATA_GATEWAYS, {})
    gateways.pop(gateway.entry.entry_id, None)
    if gateways:
        return

    hass.data.pop(DATA_GATEWAYS, None)
    for service in (SERVICE_SEND_RAW_COMMAND, SERVICE_SEND_PAIRING_COMMAND, SERVICE_SIMULATE_EVENT):
        hass.services.async_remove(DOMAIN, service)
