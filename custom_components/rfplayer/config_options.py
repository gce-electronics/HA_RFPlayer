"""Config flow for RfPlayer integration."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
import json
from typing import Any, cast

from custom_components.rfplayer.const import DEFAULT_RECEIVER_PROTOCOLS, DEFAULT_RECONNECT_INTERVAL, INIT_COMMANDS_EMPTY
from custom_components.rfplayer.device_profiles import UNDEFINED_PROFILE
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant

SELECT_DEVICE_EXCLUSION = "select_device"
DEFAULT_VALID_ADDRESS = "0"


@dataclass(frozen=True)
class RfPlayerDeviceInfo:
    """RfPlayer device info."""

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


@dataclass(frozen=True)
class RfPlayerOptions:
    """Configurable options for a RFPlayer gateway."""

    device: str
    automatic_add: bool = True
    reconnect_interval: int = DEFAULT_RECONNECT_INTERVAL
    receiver_protocols: list[str] = field(default_factory=lambda: list(DEFAULT_RECEIVER_PROTOCOLS))
    init_commands: str = INIT_COMMANDS_EMPTY
    verbose_mode: bool = False
    devices: dict[str, RfPlayerDeviceInfo] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Convert to JSON-serializable for HA persistence."""
        return asdict(self)

    def update_from_json(self, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Update gateway options from JSON-serializable data."""
        return replace(self, **data)

    def update_device_from_json(self, id_string: str, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Replace gateway device options from JSON-serializable data."""
        device_info = self.devices[id_string].update_from_json(data)
        return replace(self, devices={**self.devices, id_string: device_info})

    def update_device(self, id_string: str, device_info: RfPlayerDeviceInfo) -> RfPlayerOptions:
        """Replace gateway device options."""
        devices = {**self.devices, id_string: device_info}
        return replace(self, devices=devices)

    def add_device_from_json(self, id_string: str, data: Mapping[str, Any]) -> RfPlayerOptions:
        """Add a new rf device to the gateway."""
        device_info = RfPlayerDeviceInfo.from_json(data)
        return replace(self, devices={**self.devices, id_string: device_info})

    def remove_device(self, id_string: str) -> RfPlayerOptions:
        """Remove device from gateway."""
        devices = {k: v for k, v in self.devices.items() if k != id_string}
        return replace(self, devices=devices)

    def get_redirected_device(self, id_string: str) -> RfPlayerDeviceInfo | None:
        """Return device info with device id redirection if configured."""
        redirected_id_string = self._redirect_addresses.get(id_string, id_string)
        return self.devices.get(redirected_id_string)

    @property
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
        devices_data = data.get(CONF_DEVICES, {})
        if not isinstance(devices_data, Mapping):
            devices_data = {}
        return cls(
            device=cast(str, data["device"]),
            automatic_add=cast(bool, data.get("automatic_add", True)),
            reconnect_interval=cast(int, data.get("reconnect_interval", DEFAULT_RECONNECT_INTERVAL)),
            receiver_protocols=cast(list[str], data.get("receiver_protocols", DEFAULT_RECEIVER_PROTOCOLS)),
            init_commands=cast(str, data.get("init_commands", INIT_COMMANDS_EMPTY)),
            verbose_mode=cast(bool, data.get("verbose_mode", False)),
            devices={
                id_string: RfPlayerDeviceInfo.from_json(device)
                for id_string, device in devices_data.items()
                if isinstance(device, Mapping)
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
