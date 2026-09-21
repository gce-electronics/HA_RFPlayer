"""Config flow for RfPlayer integration."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
import json
from typing import Any

from custom_components.rfplayer.const import (
    CONF_AUTOMATIC_ADD,
    CONF_INIT_COMMANDS,
    CONF_RECEIVER_PROTOCOLS,
    CONF_RECONNECT_INTERVAL,
    CONF_VERBOSE_MODE,
    DEFAULT_RECEIVER_PROTOCOLS,
    DEFAULT_RECONNECT_INTERVAL,
    INIT_COMMANDS_EMPTY,
)
from custom_components.rfplayer.device_profiles import UNDEFINED_PROFILE
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, CONF_DEVICES
from homeassistant.core import HomeAssistant

SELECT_DEVICE_EXCLUSION = "select_device"
DEFAULT_VALID_ADDRESS = "0"


@dataclass(frozen=True)
class RfPlayerDeviceInfo:
    """Immutable configurable RfPlayer device info."""

    protocol: str
    address: str
    model: str | None = None
    redirect_address: str | None = None
    profile_name: str = UNDEFINED_PROFILE
    event_data: str | None = None

    @property
    def rf_device_id(self):
        """Build the corresponding RF Device Id."""
        return RfDeviceId(protocol=self.protocol, address=self.address, model=self.model)

    def to_json(self) -> dict[str, Any]:
        """Convert to JSON-serializable for HA persistence."""
        return asdict(self)

    def update_from_json(self, data: Mapping[str, Any]) -> RfPlayerDeviceInfo:
        """Update device info from JSON-serializable data."""
        return replace(self, **data)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> RfPlayerDeviceInfo:
        """Load device info from JSON-serializable data."""
        return cls(**data)

    @classmethod
    def from_event(cls, profile_name: str, event: RfDeviceEvent) -> RfPlayerDeviceInfo:
        """Load device info from incoming event."""
        return cls(
            protocol=event.device.protocol,
            address=event.device.address,
            model=event.device.model,
            profile_name=profile_name,
            event_data=json.dumps(event.data),
        )


DEFAULT_DEVICES = {"JAMMING_0": RfPlayerDeviceInfo(protocol="JAMMING", address="0", profile_name="Jamming Detector")}


@dataclass(frozen=True)
class RfPlayerOptions:
    """Immutable configuration options for a RFPlayer gateway."""

    device: str
    automatic_add: bool = True
    reconnect_interval: int = DEFAULT_RECONNECT_INTERVAL
    receiver_protocols: list[str] = field(
        default_factory=lambda: list(DEFAULT_RECEIVER_PROTOCOLS)
    )  # list is still mutable but tuple[str, ...] adds too much complexity
    init_commands: str = INIT_COMMANDS_EMPTY
    verbose_mode: bool = False
    devices: dict[str, RfPlayerDeviceInfo] = field(
        default_factory=dict
    )  # dict is still mutable but MappingProxy adds too much complexity

    @property
    def effective_devices(self) -> dict[str, RfPlayerDeviceInfo]:
        """User-configured devices + dafault devices."""
        # Defaults win, matching the previous startup behaviour.
        return {**self.devices, **DEFAULT_DEVICES}

    def has_device(self, id_string: str) -> bool:
        """Check if a device id string is already known."""
        # Fast lookup compared to using effective_devices aggregation
        return id_string in self.devices or id_string in DEFAULT_DEVICES

    def to_json(self) -> dict[str, Any]:
        """Convert to JSON-serializable for HA persistence."""
        return asdict(self)

    def with_updated_options_from_user_input(self, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Update gateway options from JSON-serializable data."""
        return replace(self, **data)

    def with_updated_device_from_user_input(self, id_string: str, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Replace gateway device options from JSON-serializable data."""
        device_info = self.devices[id_string].update_from_json(data)
        return replace(self, devices={**self.devices, id_string: device_info})

    def with_added_device_from_user_input(self, id_string: str, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Add a new rf device to the gateway."""
        device_info = RfPlayerDeviceInfo.from_json(data)
        return replace(self, devices={**self.devices, id_string: device_info})

    def with_updated_device(self, id_string: str, device_info: RfPlayerDeviceInfo) -> RfPlayerOptions:
        """Replace gateway device options."""
        devices = {**self.devices, id_string: device_info}
        return replace(self, devices=devices)

    def with_removed_device(self, id_string: str) -> RfPlayerOptions:
        """Remove device from gateway."""
        devices = {k: v for k, v in self.devices.items() if k != id_string}
        return replace(self, devices=devices)

    def get_redirected_device(self, id_string: str) -> RfPlayerDeviceInfo | None:
        """Return device info with device id redirection if configured."""
        redirected_id_string = self._redirect_addresses.get(id_string, id_string)
        return self.devices.get(redirected_id_string)

    @property  # Property not cached in case device is mutated. Assume number of devices is low.
    def _redirect_addresses(self) -> dict[str, str]:
        """Map a redirected device id to its configured device id."""
        return {
            RfDeviceId(protocol=device.protocol, address=device.redirect_address).id_string: id_string
            for id_string, device in self.devices.items()
            if device.redirect_address
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Load gateway options from JSON-serializable data."""
        return cls(
            device=data[CONF_DEVICE],
            automatic_add=data.get(CONF_AUTOMATIC_ADD, True),
            reconnect_interval=data.get(CONF_RECONNECT_INTERVAL, DEFAULT_RECONNECT_INTERVAL),
            receiver_protocols=data.get(CONF_RECEIVER_PROTOCOLS, DEFAULT_RECEIVER_PROTOCOLS),
            init_commands=data.get(CONF_INIT_COMMANDS, INIT_COMMANDS_EMPTY),
            verbose_mode=data.get(CONF_VERBOSE_MODE, False),
            devices={
                device_id: RfPlayerDeviceInfo.from_json(device)
                for device_id, device in data.get(CONF_DEVICES, {}).items()
            },
        )


def load_options(config_entry: ConfigEntry) -> RfPlayerOptions:
    """Load gateway options from a config entry persisted data."""
    return RfPlayerOptions.from_json(config_entry.data)


def save_options(
    hass: HomeAssistant, config_entry: ConfigEntry, options: RfPlayerOptions, *, reload: bool = True
) -> bool:
    """Persist gateway options into config entry and reload it."""

    updated = hass.config_entries.async_update_entry(
        config_entry,
        data=options.to_json(),
    )
    if updated and reload:
        hass.async_create_task(hass.config_entries.async_reload(config_entry.entry_id))
    return updated
