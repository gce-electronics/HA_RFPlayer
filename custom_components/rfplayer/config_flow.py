"""Config flow for RfPlayer integration."""

import ipaddress
import logging
import os
from typing import TYPE_CHECKING, Any, cast

from serialx.tools import list_ports

if TYPE_CHECKING:
    # HA 2026.10+ types its APIs with probatio and aliases voluptuous to it at runtime
    import probatio as vol
else:
    import voluptuous as vol

from custom_components.rfplayer.config_options import RfPlayerConfigData, RfPlayerDeviceInfo, RfPlayerOptions
from custom_components.rfplayer.const import (
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_SERIAL,
    CONF_DEVICE_SIMULATOR,
    CONF_INIT_COMMANDS,
    CONF_RECEIVER_PROTOCOLS,
    CONF_RECONNECT_INTERVAL,
    CONF_REDIRECT_ADDRESS,
    CONF_SEND_PAIRING_COMMAND,
    CONF_VERBOSE_MODE,
    DOMAIN,
)
from custom_components.rfplayer.device_profiles import UNDEFINED_PROFILE, ProfileRegistry, async_get_profile_registry
from custom_components.rfplayer.helpers import get_device_canonical_id
from custom_components.rfplayer.probe import async_get_rfplayer_unique_id
from custom_components.rfplayer.rfplayerlib import (
    COMMAND_PROTOCOLS,
    DEVICE_PROTOCOLS,
    RECEIVER_MODES,
    SIMULATOR_PORT,
    RfPlayerException,
)
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from homeassistant.config_entries import (
    HANDLERS,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE, CONF_IP_ADDRESS, CONF_PORT, CONF_PROFILE_NAME, CONF_PROTOCOL
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntry

if TYPE_CHECKING:
    from custom_components.rfplayer.runtime import RfPlayerConfigEntry

_LOGGER = logging.getLogger(__name__)

SELECT_DEVICE_EXCLUSION = "select_device"
DEFAULT_VALID_ADDRESS = "0"


@HANDLERS.register(DOMAIN)
class RfplayerConfigFlow(ConfigFlow):
    """Handle a rfplayer config flow."""

    VERSION = 2
    MINOR_VERSION = 0

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Config flow started from UI."""
        return self.async_show_menu(
            step_id="user",
            menu_options={
                "serial": "Serial device",
                "network": "Network device",
                "simulator": "Simulator",
            },
        )

    async def async_step_serial(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure a serial connection."""
        return await self._async_setup_device(
            "serial",
            user_input,
            vol.Schema({vol.Required(CONF_DEVICE_SERIAL): vol.In(await self._list_ports())}),
        )

    async def async_step_network(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure a network connection."""
        return await self._async_setup_device(
            "network",
            user_input,
            vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS): str,
                    vol.Required(CONF_PORT): int,
                }
            ),
        )

    async def async_step_simulator(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure a simulator connection."""
        return await self._async_setup_device("simulator", user_input, vol.Schema({}))

    async def _async_setup_device(
        self, step_id: str, user_input: dict[str, Any] | None, data_schema: vol.Schema
    ) -> ConfigFlowResult:
        errors: dict[str, Any] = {}
        if user_input is not None:
            if step_id == "simulator":
                user_input = {CONF_DEVICE_SIMULATOR: True}
            device_port, unique_id, errors = await self._async_validate_user_input(user_input)
            if device_port is not None and unique_id is not None:
                data = RfPlayerConfigData(device=device_port).to_json()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=device_port, data=data)

        return self.async_show_form(step_id=step_id, data_schema=data_schema, errors=errors)

    async def _async_validate_user_input(
        self, user_input: dict[str, Any]
    ) -> tuple[str | None, str | None, dict[str, str]]:
        """Resolve the selected gateway and verify its connection."""
        device_fields = (CONF_DEVICE_SERIAL, CONF_IP_ADDRESS, CONF_DEVICE_SIMULATOR)
        selected_fields = [field for field in device_fields if user_input.get(field)]
        if len(selected_fields) != 1:
            if not selected_fields:
                return None, None, {CONF_DEVICE_SERIAL: "device_missing"}
            error_field = selected_fields[0]
            error = "multiple_device" if len(selected_fields) > 1 else "device_missing"
            return None, None, {error_field: error}

        selected_field = selected_fields[0]
        if selected_field == CONF_DEVICE_SERIAL:
            device_port = await self.hass.async_add_executor_job(get_serial_by_id, user_input[selected_field])
        elif selected_field == CONF_IP_ADDRESS:
            try:
                ipaddress.ip_address(user_input[selected_field])
            except ValueError:
                return None, None, {selected_field: "invalid_ip_address"}
            device_port = f"tcp://{user_input[selected_field]}:{user_input[CONF_PORT]}"
        else:
            device_port = SIMULATOR_PORT

        unique_id = await async_get_rfplayer_unique_id(device_port)
        if unique_id is None:
            return None, None, {selected_field: "cannot_connect"}
        return device_port, unique_id, {}

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


class RfPlayerOptionsFlowHandler(OptionsFlowWithReload):
    """Handle a RFPLayer options flow."""

    device_registry: dr.DeviceRegistry
    _discovered_events: dict[str, RfDeviceEvent]
    _selected_discovered_id: str

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        self.device_registry = dr.async_get(self.hass)

        return self.async_show_menu(
            step_id="init",
            menu_options={
                "configure_gateway": "RfPlayer gateway options",
                "configure_rf_device": "RF device options",
                "add_rf_device": "Add RF device manually",
                "discover_rf_devices": "Discover sensors",
            },
        )

    async def async_step_discover_rf_devices(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Listen briefly for unknown RF devices."""
        if user_input is not None:
            return self.async_abort(reason="no_devices_found")

        gateway = self.config_entry.runtime_data.gateway
        gateway.start_discovery()
        return self.async_show_form(step_id="finish_discovery", data_schema=vol.Schema({}))

    async def async_step_finish_discovery(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Finish listening and show detected devices."""
        if user_input is None:
            return self.async_abort(reason="unknown")

        gateway = self.config_entry.runtime_data.gateway
        events = gateway.stop_discovery()
        profile_registry = await async_get_profile_registry(self.hass, False)
        self._discovered_events = {
            event.device.canonical_id: event
            for event in events
            if profile_registry.get_profile_name_from_event(event.data) != UNDEFINED_PROFILE
        }
        if not self._discovered_events:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="select_discovered_device",
            data_schema=vol.Schema({vol.Required("discovered_device"): vol.In(self._discovered_device_labels())}),
        )

    async def async_step_select_discovered_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose an event from this discovery session."""
        if user_input is not None:
            self._selected_discovered_id = user_input["discovered_device"]
            return self.async_show_menu(
                step_id="discovered_device_action", menu_options=["add_discovered_device", "replace_device"]
            )
        return self.async_abort(reason="unknown")

    async def async_step_discovered_device_action(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose how to handle the selected device."""
        if user_input is not None:
            next_step_id = user_input.get("next_step_id")
            if next_step_id == "add_discovered_device":
                return await self.async_step_add_discovered_device()
            if next_step_id == "replace_device":
                return await self.async_step_replace_device()

        return self.async_show_menu(
            step_id="discovered_device_action", menu_options=["add_discovered_device", "replace_device"]
        )

    async def async_step_add_discovered_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add the selected discovery result as a new configured device."""
        event = self._discovered_events[self._selected_discovered_id]
        profile_registry = await async_get_profile_registry(self.hass, False)
        if user_input is None:
            profile_name = profile_registry.get_profile_name_from_event(event.data)
            options = RfPlayerOptions.from_json(self.config_entry.options)
            device_info = RfPlayerDeviceInfo.from_event(profile_name, event)
            return self._save_and_reload(options.with_updated_device(event.device.canonical_id, device_info))
        return self.async_abort(reason="unknown")

    async def async_step_replace_device(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Map the discovered RF ID onto an existing device to preserve its entities."""
        options = RfPlayerOptions.from_json(self.config_entry.options)
        event = self._discovered_events[self._selected_discovered_id]
        profile_registry = await async_get_profile_registry(self.hass, False)
        discovered_profile = profile_registry.get_profile_name_from_event(event.data)
        compatible = {
            canonical_id: f"{info.protocol} {info.model or ''} {info.address}"
            for canonical_id, info in options.devices.items()
            if info.protocol == event.device.protocol
            and info.profile_name == discovered_profile
            and canonical_id != event.device.canonical_id
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            canonical_id = user_input["existing_device"]
            info = options.devices.get(canonical_id)
            if info is None:
                errors["existing_device"] = "unknown_device"
            elif any(
                other_id != canonical_id
                and other.protocol == info.protocol
                and other.redirect_address
                and RfDeviceId(protocol=other.protocol, address=other.redirect_address).canonical_id
                == event.device.canonical_id
                for other_id, other in options.devices.items()
            ):
                errors["existing_device"] = "duplicate_redirect"
            else:
                updated = info.update_from_json({CONF_REDIRECT_ADDRESS: event.device.address})
                return self._save_and_reload(options.with_updated_device(canonical_id, updated))
        if not compatible:
            return self.async_abort(reason="no_compatible_devices")
        return self.async_show_form(
            step_id="replace_device",
            data_schema=vol.Schema({vol.Required("existing_device"): vol.In(compatible)}),
            errors=errors,
        )

    def _discovered_device_labels(self) -> dict[str, str]:
        """Build labels for discovered IDs."""
        return {
            canonical_id: f"{event.device.protocol} {event.device.model or ''} {event.device.address}"
            for canonical_id, event in self._discovered_events.items()
        }

    async def async_step_configure_gateway(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Prompt for gateway options."""
        errors: dict[str, Any] = {}
        options = RfPlayerOptions.from_json(self.config_entry.options)

        if user_input is not None:
            # Detect errors
            if not user_input[CONF_RECEIVER_PROTOCOLS]:
                errors[CONF_RECEIVER_PROTOCOLS] = "no_receiver_protocol"

            if not errors:
                # Finalize
                return self._save_and_reload(options.with_updated_options_from_user_input(user_input))

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
        options = RfPlayerOptions.from_json(self.config_entry.options)

        if user_input is not None:
            # Detect errors
            if not RfDeviceId.is_valid_address(user_input.get(CONF_REDIRECT_ADDRESS, DEFAULT_VALID_ADDRESS)):
                errors[CONF_REDIRECT_ADDRESS] = "invalid_address"

            entry_id = user_input[CONF_DEVICE]
            entry = self.device_registry.async_get(entry_id)
            if not entry:
                errors[CONF_DEVICE] = "unknown_device"
            else:
                canonical_id = get_device_canonical_id(entry.identifiers)
                if not canonical_id:
                    errors[CONF_DEVICE] = "unknown_device"
                if canonical_id and canonical_id not in options.devices:
                    errors[CONF_DEVICE] = "unknown_device"

            # Remove CONF_DEVICE and set CONF_REDIRECT_ADDRESS to None if omitted
            cleaned_user_input = {CONF_REDIRECT_ADDRESS: user_input.get(CONF_REDIRECT_ADDRESS)}

            if not errors and canonical_id:
                # Finalize
                return self._save_and_reload(
                    options.with_updated_device_from_user_input(canonical_id, cleaned_user_input)
                )

        return self.async_show_form(step_id="configure_rf_device", data_schema=self._rf_device_schema(), errors=errors)

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
        canonical_id = None
        options = RfPlayerOptions.from_json(self.config_entry.options)

        profile_registry = await async_get_profile_registry(self.hass, False)

        if user_input is not None:
            # The pairing flag is an action, not a device option: keep it out of the saved device info
            device_input = {k: v for k, v in user_input.items() if k != CONF_SEND_PAIRING_COMMAND}
            send_pairing_command = user_input.get(CONF_SEND_PAIRING_COMMAND, False)

            # New device
            if not profile_registry.is_valid_protocol(device_input[CONF_PROFILE_NAME], device_input[CONF_PROTOCOL]):
                errors[CONF_PROTOCOL] = "incompatible_protocol"

            if not RfDeviceId.is_valid_address(device_input[CONF_ADDRESS]):
                errors[CONF_ADDRESS] = "invalid_address"

            if send_pairing_command and device_input[CONF_PROTOCOL] not in COMMAND_PROTOCOLS:
                errors[CONF_SEND_PAIRING_COMMAND] = "pairing_not_supported"

            if not errors:
                device_id = RfDeviceId(protocol=device_input[CONF_PROTOCOL], address=device_input[CONF_ADDRESS])
                canonical_id = device_id.canonical_id

                if options.has_device(canonical_id):
                    errors[CONF_ADDRESS] = "duplicate_device"
                # Pair before saving: saving the options reloads the gateway connection
                elif send_pairing_command:
                    errors.update(await self._async_send_pairing_command(device_id))

                if not errors:
                    return self._save_and_reload(options.with_added_device_from_user_input(canonical_id, device_input))

        data_schema = self._new_rf_device_schema(None, profile_registry)
        return self.async_show_form(step_id="add_rf_device", data_schema=data_schema, errors=errors)

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
                vol.Optional(CONF_SEND_PAIRING_COMMAND, default=False): bool,
            }
        )

    async def _async_send_pairing_command(self, device_id: RfDeviceId) -> dict[str, str]:
        """Send the pairing command and return the form errors."""
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return {"base": "cannot_connect"}

        gateway = cast("RfPlayerConfigEntry", self.config_entry).runtime_data.gateway
        try:
            await gateway.async_send_pairing_command(device_id)
        except (HomeAssistantError, RfPlayerException) as exc:
            _LOGGER.warning("Unable to send pairing command to %s: %s", device_id.canonical_id, exc)
            return {"base": "cannot_connect"}
        return {}

    @callback
    def _save_and_reload(self, options: RfPlayerOptions) -> ConfigFlowResult:
        return self.async_create_entry(title="", data=options.to_json())

    def _list_rf_devices(self) -> dict[str, str]:
        device_entries = dr.async_entries_for_config_entry(self.device_registry, self.config_entry.entry_id)
        # TODO should remove jamming device
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
