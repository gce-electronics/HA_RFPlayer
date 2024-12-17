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


def test_valid_address():
    assert RfDeviceId.is_valid_address("123456789") is True
    assert RfDeviceId.is_valid_address("-1") is False

    assert RfDeviceId.is_valid_address("xABCDEF") is True
    assert RfDeviceId.is_valid_address("x123456789") is True
    assert RfDeviceId.is_valid_address("xG1") is False

    assert RfDeviceId.is_valid_address("A1") is True
    assert RfDeviceId.is_valid_address("A16") is True
    assert RfDeviceId.is_valid_address("A0") is False
    assert RfDeviceId.is_valid_address("Q1") is False
    assert RfDeviceId.is_valid_address("A17") is False


def test_integer_address():
    device = RfDeviceId(protocol="X2D", address="123456789")
    assert device.integer_address == 123456789
    assert device.id_string == "X2D-123456789"

    device = RfDeviceId(protocol="X2D", address="xABCD1234")
    assert device.integer_address == 0xABCD1234
    assert device.id_string == "X2D-2882343476"

    device = RfDeviceId(protocol="X2D", address="A1")
    assert device.integer_address == 0
    assert device.id_string == "X2D-0"

    device = RfDeviceId(protocol="X2D", address="A16")
    assert device.integer_address == 15
    assert device.id_string == "X2D-15"

    device = RfDeviceId(protocol="X2D", address="P16")
    assert device.integer_address == 255
    assert device.id_string == "X2D-255"

    device.address = "P1"
    assert device.integer_address == 240
    assert device.id_string == "X2D-240"


def test_group_unit_code():
    device = RfDeviceId(protocol="X2D", address=str(0x7CED0101))
    assert device.group_code == "2095907072"
    assert device.unit_code == "1"

    device = RfDeviceId(protocol="RTS", address="x00000010")
    assert device.group_code == "0"
    assert device.unit_code == "16"

    device = RfDeviceId(protocol="RTS", address="B1")
    assert device.group_code == "0"
    assert device.unit_code == "16"
