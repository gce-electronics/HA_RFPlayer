"""Config flow for RfPlayer integration."""

import ipaddress
import os
from typing import Any

from serialx.tools import list_ports
import voluptuous as vol

from custom_components.rfplayer.config_options import RfPlayerDeviceInfo, RfPlayerOptions, save_options
from custom_components.rfplayer.const import (
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_SERIAL,
    CONF_DEVICE_SIMULATOR,
    CONF_INIT_COMMANDS,
    CONF_RECEIVER_PROTOCOLS,
    CONF_RECONNECT_INTERVAL,
    CONF_REDIRECT_ADDRESS,
    CONF_VERBOSE_MODE,
    DOMAIN,
)
from custom_components.rfplayer.device_profiles import ProfileRegistry, async_get_profile_registry
from custom_components.rfplayer.helpers import get_device_id_string_from_identifiers
from custom_components.rfplayer.rfplayerlib import DEVICE_PROTOCOLS, RECEIVER_MODES, SIMULATOR_PORT
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId
from homeassistant.config_entries import HANDLERS, ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE, CONF_IP_ADDRESS, CONF_PORT, CONF_PROFILE_NAME, CONF_PROTOCOL
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
                data = RfPlayerOptions(device=device_port).to_json()
                # TODO: Define RfPlayerConfig and store only the device port in entry.data
                # ConfigFlow controls entry.data: async_create_entry(data) => entry.data
                # OptionsFlow controlc entry.options: async_create_entry(data) => entry.options
                # RfPlayerOptions should be stored in entry.options from OptionsFlow
                return self.async_create_entry(title=device_port, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=await self._async_user_schema(),
            errors=schema_errors,
        )

    async def _async_user_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(CONF_DEVICE_SERIAL): vol.In(await self._list_ports()),
                vol.Optional(CONF_IP_ADDRESS): str,
                vol.Optional(CONF_PORT): int,
                vol.Optional(CONF_DEVICE_SIMULATOR): bool,
            }
        )

    async def _list_ports(self) -> dict[str, str]:
        ports = await self.hass.async_add_executor_job(list_ports.comports)
        list_of_ports = {}
        for port in ports:
            list_of_ports[port.device] = f"{port}, s/n: {port.serial_number or 'n/a'}" + (
                f" - {port.manufacturer}" if port.manufacturer else ""
            )
        return list_of_ports

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
        options = RfPlayerOptions.from_json(self.config_entry.data)

        if user_input is not None:
            # Detect errors
            if not user_input[CONF_RECEIVER_PROTOCOLS]:
                errors[CONF_RECEIVER_PROTOCOLS] = "no_receiver_protocol"

            if not errors:
                # Finalize
                return self._save_and_finish(options.update_from_json(user_input))

        return self.async_show_form(
            step_id="configure_gateway", data_schema=self._gateway_schema(options), errors=errors
        )

    def _gateway_schema(self, options: RfPlayerOptions) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_AUTOMATIC_ADD,
                    default=options.automatic_add,
                ): bool,
                vol.Required(
                    CONF_RECONNECT_INTERVAL,
                    default=options.reconnect_interval,
                ): int,
                vol.Required(
                    CONF_RECEIVER_PROTOCOLS,
                    default=options.receiver_protocols,
                ): cv.multi_select(RECEIVER_MODES),
                # Use suggested_value instead of default for optional because otherwise,
                # if the form field is empty, default value is set instead of an empty value.
                vol.Optional(CONF_INIT_COMMANDS, description={"suggested_value": options.init_commands}): str,
                vol.Required(CONF_VERBOSE_MODE, default=options.verbose_mode): bool,
            }
        )

    async def async_step_configure_rf_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage RF device options."""
        errors: dict[str, Any] = {}
        options = RfPlayerOptions.from_json(self.config_entry.data)

        if user_input is not None:
            # Detect errors
            if not RfDeviceId.is_valid_address(user_input.get(CONF_REDIRECT_ADDRESS, DEFAULT_VALID_ADDRESS)):
                errors[CONF_REDIRECT_ADDRESS] = "invalid_address"

            entry_id = user_input[CONF_DEVICE]
            entry = self.device_registry.async_get(entry_id)
            if not entry:
                errors[CONF_DEVICE] = "unknown_device"
            else:
                id_string = get_device_id_string_from_identifiers(entry.identifiers)
                if not id_string:
                    errors[CONF_DEVICE] = "unknown_device"
                if id_string and id_string not in options.devices:
                    errors[CONF_DEVICE] = "unknown_device"

            # Remove CONF_DEVICE and set CONF_REDIRECT_ADDRESS to None if omitted
            cleaned_user_input = {CONF_REDIRECT_ADDRESS: user_input.get(CONF_REDIRECT_ADDRESS)}

            if not errors and id_string:
                # Finalize
                return self._save_and_finish(options.update_device_from_json(id_string, cleaned_user_input))

        return self.async_show_form(
            step_id="configure_rf_device", data_schema=vol.Schema(self._rf_device_schema()), errors=errors
        )

    def _rf_device_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_DEVICE): vol.In(self._list_rf_devices()),
                vol.Optional(CONF_REDIRECT_ADDRESS): str,
            }
        )

    async def async_step_add_rf_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add manuall a RF device."""
        errors: dict[str, Any] = {}
        id_string = None
        options = RfPlayerOptions.from_json(self.config_entry.data)

        profile_registry = await async_get_profile_registry(self.hass, False)

        if user_input is not None:
            # New device
            if not profile_registry.is_valid_protocol(user_input[CONF_PROFILE_NAME], user_input[CONF_PROTOCOL]):
                errors[CONF_PROTOCOL] = "incompatible_protocol"

            if not RfDeviceId.is_valid_address(user_input[CONF_ADDRESS]):
                errors[CONF_ADDRESS] = "invalid_address"

            if not errors:
                id_string = RfDeviceId(protocol=user_input[CONF_PROTOCOL], address=user_input[CONF_ADDRESS]).id_string

                return self._save_and_finish(options.add_device_from_json(id_string, user_input))

        data_schema = self._new_rf_device_schema(None, profile_registry)
        return self.async_show_form(step_id="add_rf_device", data_schema=vol.Schema(data_schema), errors=errors)

    @callback
    def _new_rf_device_schema(
        self, options: RfPlayerDeviceInfo | None, profile_registry: ProfileRegistry
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_PROTOCOL, default=options.protocol if options else None): vol.In(DEVICE_PROTOCOLS),
                vol.Required(CONF_ADDRESS, default=options.address if options else None): str,
                vol.Required(CONF_PROFILE_NAME, default=options.profile_name if options else None): vol.In(
                    profile_registry.get_profile_names()
                ),
            }
        )

    @callback
    def _save_and_finish(self, options: RfPlayerOptions) -> ConfigFlowResult:
        save_options(self.hass, self.config_entry, options)
        return self.async_create_entry(title="", data={})

    @callback
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
