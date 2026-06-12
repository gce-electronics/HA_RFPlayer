"""Config flow for RfPlayer integration."""

import copy
import ipaddress
import os
from typing import Any, cast

from serialx.tools import list_ports
import voluptuous as vol

from custom_components.rfplayer.const import (
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_SERIAL,
    CONF_DEVICE_SIMULATOR,
    CONF_INIT_COMMANDS,
    CONF_RECEIVER_PROTOCOLS,
    CONF_RECONNECT_INTERVAL,
    CONF_REDIRECT_ADDRESS,
    CONF_VERBOSE_MODE,
    DEFAULT_RECEIVER_PROTOCOLS,
    DEFAULT_RECONNECT_INTERVAL,
    DOMAIN,
    INIT_COMMANDS_EMPTY,
)
from custom_components.rfplayer.device_profiles import async_get_profile_registry
from custom_components.rfplayer.helpers import build_device_id_from_device_info, get_device_id_string_from_identifiers
from custom_components.rfplayer.rfplayerlib import DEVICE_PROTOCOLS, RECEIVER_MODES, SIMULATOR_PORT
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from homeassistant.config_entries import HANDLERS, ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_DEVICE,
    CONF_DEVICES,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_PROFILE_NAME,
    CONF_PROTOCOL,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntry

SELECT_DEVICE_EXCLUSION = "select_device"
DEFAULT_VALID_ADDRESS = "0"


@HANDLERS.register(DOMAIN)
class RfplayerConfigFlow(ConfigFlow):
    """Handle a rfplayer config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Config flow started from UI."""

        # Only 1 RfPlayer gateway can be configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        schema_errors: dict[str, Any] = {}

        if user_input is not None:
            if len(user_input.keys() & {CONF_DEVICE_SERIAL, CONF_IP_ADDRESS, CONF_DEVICE_SIMULATOR}) > 1:
                schema_errors.update({CONF_DEVICE_SERIAL: "multiple_device"})
            if len(user_input.keys() & {CONF_DEVICE_SERIAL, CONF_IP_ADDRESS, CONF_DEVICE_SIMULATOR}) == 0:
                schema_errors.update({CONF_DEVICE_SERIAL: "device_missing"})

            if not schema_errors:
                if user_input.get(CONF_DEVICE_SERIAL):
                    device_port = await self.hass.async_add_executor_job(
                        get_serial_by_id, user_input[CONF_DEVICE_SERIAL]
                    )
                elif user_input.get(CONF_IP_ADDRESS):
                    try:
                        ipaddress.ip_address(user_input[CONF_IP_ADDRESS])
                        device_port = f"tcp://{user_input[CONF_IP_ADDRESS]}:{user_input[CONF_PORT]}"
                    except ValueError:
                        schema_errors.update({CONF_IP_ADDRESS: "invalid_ip_address"})
                elif user_input.get(CONF_DEVICE_SIMULATOR):
                    device_port = SIMULATOR_PORT

            if not schema_errors:
                entry_data = {
                    CONF_DEVICE: device_port,
                    CONF_AUTOMATIC_ADD: True,
                    CONF_RECONNECT_INTERVAL: DEFAULT_RECONNECT_INTERVAL,
                    CONF_RECEIVER_PROTOCOLS: DEFAULT_RECEIVER_PROTOCOLS,
                    CONF_INIT_COMMANDS: INIT_COMMANDS_EMPTY,
                    CONF_VERBOSE_MODE: False,
                    CONF_DEVICES: {},
                    CONF_REDIRECT_ADDRESS: {},
                }
                return self.async_create_entry(title=device_port, data=entry_data)

        ports = await self.hass.async_add_executor_job(list_ports.comports)
        list_of_ports = {}
        for port in ports:
            list_of_ports[port.device] = f"{port}, s/n: {port.serial_number or 'n/a'}" + (
                f" - {port.manufacturer}" if port.manufacturer else ""
            )

        data_schema = {
            vol.Optional(CONF_DEVICE_SERIAL): vol.In(list_of_ports),
            vol.Optional(CONF_IP_ADDRESS): str,
            vol.Optional(CONF_PORT): int,
            vol.Optional(CONF_DEVICE_SIMULATOR): bool,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=schema_errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Define the config flow to handle options."""
        return RfPlayerOptionsFlowHandler()


class RfPlayerOptionsFlowHandler(OptionsFlow):
    """Handle a RFPLayer options flow."""

    device_registry: dr.DeviceRegistry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        self.device_registry = dr.async_get(self.hass)

        return self.async_show_menu(
            step_id="init",
            menu_options={
                "configure_gateway": "RfPlayer gateway options",
                "configure_rf_device": "RF device options",
                "add_rf_device": "Add RF device",
            },
        )

    async def async_step_configure_gateway(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Prompt for gateway options."""
        errors: dict[str, Any] = {}

        if user_input is not None:
            global_options = {
                CONF_AUTOMATIC_ADD: user_input[CONF_AUTOMATIC_ADD],
                CONF_RECONNECT_INTERVAL: user_input[CONF_RECONNECT_INTERVAL],
                CONF_RECEIVER_PROTOCOLS: user_input[CONF_RECEIVER_PROTOCOLS],
                CONF_INIT_COMMANDS: user_input.get(CONF_INIT_COMMANDS, INIT_COMMANDS_EMPTY),
                CONF_VERBOSE_MODE: user_input[CONF_VERBOSE_MODE],
            }

            if not user_input[CONF_RECEIVER_PROTOCOLS]:
                errors.update({CONF_RECEIVER_PROTOCOLS: "no_receiver_protocol"})

            if not errors:
                self.update_config_data(global_options=global_options)

                return self.async_create_entry(title="", data={})

        data = self.config_entry.data

        options = {
            vol.Required(
                CONF_AUTOMATIC_ADD,
                default=data[CONF_AUTOMATIC_ADD],
            ): bool,
            vol.Required(
                CONF_RECONNECT_INTERVAL,
                default=data[CONF_RECONNECT_INTERVAL],
            ): int,
            vol.Required(
                CONF_RECEIVER_PROTOCOLS,
                default=data[CONF_RECEIVER_PROTOCOLS],
            ): cv.multi_select(RECEIVER_MODES),
            # Use suggested_value instead of default for optional because otherwise,
            # if the form field is empty, default value is set instead of an empty value.
            vol.Optional(CONF_INIT_COMMANDS, description={"suggested_value": data[CONF_INIT_COMMANDS]}): str,
            vol.Required(CONF_VERBOSE_MODE, default=data[CONF_VERBOSE_MODE]): bool,
        }

        return self.async_show_form(step_id="configure_gateway", data_schema=vol.Schema(options), errors=errors)

    async def async_step_configure_rf_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage RF device options."""
        errors: dict[str, Any] = {}

        if user_input is not None:
            if not RfDeviceId.is_valid_address(user_input.get(CONF_REDIRECT_ADDRESS, DEFAULT_VALID_ADDRESS)):
                errors.update({CONF_REDIRECT_ADDRESS: "invalid_address"})

            if not errors:
                entry_id = user_input[CONF_DEVICE]
                entry = self.device_registry.async_get(entry_id)
                assert entry

                id_string = get_device_id_string_from_identifiers(entry.identifiers)
                assert id_string

                devices: dict[str, dict[str, Any]] = {id_string: user_input}
                devices[id_string].setdefault(CONF_REDIRECT_ADDRESS, None)

                self.update_config_data(devices=devices)

                return self.async_create_entry(title="", data={})

        option_schema = {
            vol.Required(CONF_DEVICE): vol.In(self._list_rf_devices()),
            vol.Optional(CONF_REDIRECT_ADDRESS): str,
        }

        return self.async_show_form(step_id="configure_rf_device", data_schema=vol.Schema(option_schema), errors=errors)

    async def async_step_add_rf_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add manuall a RF device."""
        errors: dict[str, Any] = {}

        profile_registry = await async_get_profile_registry(self.hass, False)

        if user_input is not None:
            # New device
            if not profile_registry.is_valid_protocol(user_input[CONF_PROFILE_NAME], user_input[CONF_PROTOCOL]):
                errors.update({CONF_PROTOCOL: "incompatible_protocol"})

            if not RfDeviceId.is_valid_address(user_input[CONF_ADDRESS]):
                errors.update({CONF_ADDRESS: "invalid_address"})

            if not errors:
                id_string = RfDeviceId(protocol=user_input[CONF_PROTOCOL], address=user_input[CONF_ADDRESS]).id_string

                device_info = user_input.copy()
                device_info[CONF_REDIRECT_ADDRESS] = None
                self.update_config_data(devices={id_string: device_info})

                return self.async_create_entry(title="", data={})

        data = self.config_entry.data

        # New device
        option_schema = {
            vol.Required(CONF_PROTOCOL, default=data.get(CONF_PROTOCOL)): vol.In(DEVICE_PROTOCOLS),
            vol.Required(CONF_ADDRESS, default=data.get(CONF_ADDRESS)): str,
            vol.Required(CONF_PROFILE_NAME, default=data.get(CONF_PROFILE_NAME)): vol.In(
                profile_registry.get_profile_names()
            ),
        }

        return self.async_show_form(step_id="add_rf_device", data_schema=vol.Schema(option_schema), errors=errors)

    @callback
    def update_config_data(
        self,
        *,
        global_options: dict[str, Any] | None = None,
        devices: dict[str, Any] | None = None,
    ) -> None:
        """Update data in ConfigEntry."""
        entry_data = self.config_entry.data.copy()
        entry_data[CONF_DEVICES] = cast(dict[str, dict], copy.deepcopy(self.config_entry.data[CONF_DEVICES]))
        if global_options:
            entry_data.update(global_options)
        if devices:
            for id_string, device_options in devices.items():
                entry_data[CONF_DEVICES].setdefault(id_string, {}).update(device_options)

            entry_data[CONF_REDIRECT_ADDRESS].clear()
            for id_string, device_info in entry_data[CONF_DEVICES].items():
                if device_info.get(CONF_REDIRECT_ADDRESS):
                    redirect_device_info = device_info.copy()
                    redirect_device_info[CONF_ADDRESS] = device_info[CONF_REDIRECT_ADDRESS]
                    redirect_id_string = build_device_id_from_device_info(redirect_device_info).id_string
                    entry_data[CONF_REDIRECT_ADDRESS][redirect_id_string] = id_string
        self.hass.config_entries.async_update_entry(self.config_entry, data=entry_data)
        self.hass.async_create_task(self.hass.config_entries.async_reload(self.config_entry.entry_id))

    def _list_rf_devices(self) -> dict[str, str]:
        device_entries = dr.async_entries_for_config_entry(self.device_registry, self.config_entry.entry_id)

        return {entry.id: self._get_device_name(entry) for entry in device_entries}

    def _get_device_name(self, entry: DeviceEntry) -> str:
        return entry.name_by_user if entry.name_by_user else entry.name or "undefined"


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path
