from typing import cast
from unittest.mock import Mock

from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceEventAdapter, RfDeviceId
from tests.rfplayer.constants import BLYSS_ADDRESS, BLYSS_OFF_EVENT_DATA, OREGON_ADDRESS, OREGON_EVENT_DATA


def test_raw_event_callback_oregon():
    mock_callback = Mock()
    adapter = RfDeviceEventAdapter(mock_callback)
    adapter.raw_event_callback(OREGON_EVENT_DATA)

    event = cast(RfDeviceEvent, mock_callback.call_args[0][0])
    assert event.device == RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800")
    assert event.data == OREGON_EVENT_DATA


def test_raw_event_callback_blyss():
    mock_callback = Mock()
    adapter = RfDeviceEventAdapter(mock_callback)
    adapter.raw_event_callback(BLYSS_OFF_EVENT_DATA)

    event = cast(RfDeviceEvent, mock_callback.call_args[0][0])
    assert event.device == RfDeviceId(protocol="BLYSS", address=BLYSS_ADDRESS, model="switch")
    assert event.data == BLYSS_OFF_EVENT_DATA


def test_group_unit_code():
    device = RfDeviceId(protocol="X2D", address=str(0x7CED0101))
    assert device.pairing_code == str(0x7CED010)
    assert device.group_code is None
    assert device.unit_code == str(0x1)

    device = RfDeviceId(protocol="CHACON", address=str(0x304C9E87))
    assert device.pairing_code == str(0xC1327A)
    assert device.group_code == str(0x0)
    assert device.unit_code == str(0x7)

    device = RfDeviceId(protocol="X10", address=str(0x304C9E87))
    assert device.pairing_code == str(0x304C9E)
    assert device.group_code == str(0x8)
    assert device.unit_code == str(0x7)

    device = RfDeviceId(protocol="RTS", address=str(0x304C9E87))
    assert device.pairing_code == str(0x304C9E)
    assert device.group_code == str(0x8)
    assert device.unit_code == str(0x7)

    device = RfDeviceId(protocol="VISIONIC", address=str(0x304C9E87))
    assert device.pairing_code == str(0x304C)
    assert device.group_code == str(0x9E)
    assert device.unit_code == str(0x87)

    device = RfDeviceId(protocol="OREGON", address=str(0x304C9E87))
    assert device.pairing_code == str(0x304C9E87)
    assert device.group_code is None
    assert device.unit_code == str(0x304C9E87)
