"""Config flow to configure the rfplayer integration."""
import os
from typing import Any

import serial
import voluptuous as vol

from homeassistant import exceptions
from homeassistant.config_entries import HANDLERS, ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_DEVICE, CONF_DEVICES
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult

from .const import (
    CONF_AUTOMATIC_ADD,
    CONF_RECONNECT_INTERVAL,
    DEFAULT_RECONNECT_INTERVAL,
    DOMAIN,
)


@HANDLERS.register(DOMAIN)
class RfplayerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a rfplayer config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Config flow started from UI."""
        schema_errors: dict[str, Any] = {}

        if user_input is not None:
            user_input[CONF_DEVICES] = {}

            user_input[CONF_DEVICE] = await self.hass.async_add_executor_job(
                get_serial_by_id, user_input[CONF_DEVICE]
            )

            if not schema_errors:
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE], data=user_input
                )

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = {}
        for port in ports:
            list_of_ports[port.device] = (
                f"{port}, s/n: {port.serial_number or 'n/a'}"
                + (f" - {port.manufacturer}" if port.manufacturer else "")
            )

        if not list_of_ports:
            raise AbortFlow("no_devices_found")

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
            errors=schema_errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Define the config flow to handle options."""
        return RfPlayerOptionsFlowHandler(config_entry)


class RfPlayerOptionsFlowHandler(OptionsFlow):
    """Handle a RFPLayer options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
