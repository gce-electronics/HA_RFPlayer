"""Tests for RfPlayer config options persistence."""

import pytest

from custom_components.rfplayer.config_options import RfPlayerDeviceInfo, RfPlayerOptions
from tests.rfplayer.conftest import rfplayer_config_entry


def test_device_info_from_json_ignores_unknown_keys() -> None:
    """Device entries persisted by v1.5.0 configure step contain the device registry id."""
    device_info = RfPlayerDeviceInfo.from_json(
        {
            "device": "0123456789abcdef0123456789abcdef",
            "protocol": "X10",
            "address": "1",
            "profile_name": "X10 On/Off",
            "redirect_address": "2",
        }
    )

    assert device_info == RfPlayerDeviceInfo(
        protocol="X10", address="1", profile_name="X10 On/Off", redirect_address="2"
    )
    assert "device" not in device_info.to_json()


@pytest.mark.integration
async def test_setup_entry_updates_legacy_device_entry(hass, mock_serial_connection) -> None:
    """Gateway setup removes invalid legacy keys from the config entry."""
    entry = await rfplayer_config_entry(
        hass,
        devices={
            "x10_1": {
                "device": "0123456789abcdef0123456789abcdef",
                "protocol": "X10",
                "address": "1",
                "profile_name": "X10 On/Off",
                "redirect_address": None,
            },
            "legacy_key": {
                "profile_name": "X10 On/Off",
            },
        },
    )

    assert entry.data["devices"] == {
        "x10_1": {
            "device": "0123456789abcdef0123456789abcdef",
            "protocol": "X10",
            "address": "1",
            "profile_name": "X10 On/Off",
            "redirect_address": None,
        }
    }


def test_options_from_json_recovers_missing_identity_and_skips_unusable_id(caplog) -> None:
    """Recover missing identity from canonical IDs and skip records without one."""
    options = RfPlayerOptions.from_json(
        {
            "device": "/dev/ttyUSB0",
            "devices": {
                "X10-0": {
                    "protocol": "X10",
                    "profile_name": "X10 On/Off",
                },
                "legacy_key": {
                    "profile_name": "X10 On/Off",
                },
            },
        }
    )

    assert options.devices == {"X10-0": RfPlayerDeviceInfo(protocol="X10", address="0", profile_name="X10 On/Off")}
    assert "Restoring missing RF device field(s) address from canonical ID X10-0" in caplog.text
    assert "Ignoring RF device legacy_key: missing required field(s): address, protocol" in caplog.text
