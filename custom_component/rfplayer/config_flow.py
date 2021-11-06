"""Config flow to configure the rfplayer integration."""
import os

import serial
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_DEVICE, CONF_DEVICES

from .const import (
    CONF_AUTOMATIC_ADD,
    CONF_RECONNECT_INTERVAL,
    CONF_WAIT_FOR_ACK,
    DEFAULT_RECONNECT_INTERVAL,
    DOMAIN,
)


@config_entries.HANDLERS.register(DOMAIN)
class RfplayerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a rfplayer config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Config flow started from UI."""
        errors = {}

        if user_input is not None:
            user_input[CONF_DEVICES] = {}

            dev_path = await self.hass.async_add_executor_job(
                get_serial_by_id, user_input[CONF_DEVICE]
            )

            # try:
            #     # TODO test connection
            # except CannotConnect:
            #     errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(title=dev_path, data=user_input)

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = {}
        for port in ports:
            list_of_ports[
                port.device
            ] = f"{port}, s/n: {port.serial_number or 'n/a'}" + (
                f" - {port.manufacturer}" if port.manufacturer else ""
            )
        # list_of_ports[CONF_MANUAL_PATH] = CONF_MANUAL_PATH

        data = {
            vol.Required(CONF_DEVICE): vol.In(list_of_ports),
            vol.Required(CONF_AUTOMATIC_ADD, default=True): bool,
            vol.Required(CONF_WAIT_FOR_ACK, default=False): bool,
            vol.Required(
                CONF_RECONNECT_INTERVAL, default=DEFAULT_RECONNECT_INTERVAL
            ): int,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data),
            errors=errors,
        )


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
