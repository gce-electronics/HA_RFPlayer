"""Config flow to configure the rfplayer integration."""
import os

import serial
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_DEVICE, CONF_DEVICES
from homeassistant.core import callback

from .const import (
    CONF_AUTOMATIC_ADD,
    CONF_RECONNECT_INTERVAL,
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

            user_input[CONF_DEVICE] = await self.hass.async_add_executor_job(
                get_serial_by_id, user_input[CONF_DEVICE]
            )

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE], data=user_input
                )

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = {}
        for port in ports:
            list_of_ports[
                port.device
            ] = f"{port}, s/n: {port.serial_number or 'n/a'}" + (
                f" - {port.manufacturer}" if port.manufacturer else ""
            )

        data = {
            vol.Required(CONF_DEVICE): vol.In(list_of_ports),
            vol.Required(CONF_AUTOMATIC_ADD, default=True): bool,
            vol.Required(
                CONF_RECONNECT_INTERVAL, default=DEFAULT_RECONNECT_INTERVAL
            ): int,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return RfPlayerOptionsFlowHandler(config_entry)


class RfPlayerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a RFPLayer options flow."""

    def __init__(self, config_entry):
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict = None):
        """Manage the options."""
        if user_input is None:
            config = self.config_entry.data
            options = self.config_entry.options
            auto_add = options.get(CONF_AUTOMATIC_ADD, config[CONF_AUTOMATIC_ADD])

            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {vol.Required(CONF_AUTOMATIC_ADD, default=auto_add): bool}
                ),
            )
        data = self.config_entry.data.copy()
        data[CONF_AUTOMATIC_ADD] = user_input[CONF_AUTOMATIC_ADD]
        return self.async_create_entry(title=data[CONF_DEVICE], data=data)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path
