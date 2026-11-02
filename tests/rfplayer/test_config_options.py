"""Tests for RfPlayer config options persistence."""

from custom_components.rfplayer.config_options import RfPlayerDeviceInfo, RfPlayerOptions


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


def test_options_from_json_with_legacy_device_entry() -> None:
    """Gateway options load when a device entry contains a legacy key."""
    options = RfPlayerOptions.from_json(
        {
            "device": "/dev/ttyUSB0",
            "devices": {
                "x10_1": {
                    "device": "0123456789abcdef0123456789abcdef",
                    "protocol": "X10",
                    "address": "1",
                    "profile_name": "X10 On/Off",
                    "redirect_address": None,
                }
            },
        }
    )

    assert options.devices["x10_1"] == RfPlayerDeviceInfo(protocol="X10", address="1", profile_name="X10 On/Off")
