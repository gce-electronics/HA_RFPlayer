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
    assert device.group_code == str(0x7CED0100)
    assert device.unit_code == str(0x1)

    device = RfDeviceId(protocol="RTS", address=str(0x00000010))
    assert device.group_code == str(0x00000000)
    assert device.unit_code == str(0x00000010)
