from typing import cast
from unittest.mock import Mock

import pytest

from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData, RfplayerProtocol
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.light import ATTR_BRIGHTNESS, STATE_ON
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_OPEN,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant
from tests.rfplayer.conftest import assert_entity_state, rfplayer_config_entry
from tests.rfplayer.constants import (
    CHACON_ALL_ON_EVENT_DATA,
    CHACON_BINARY_SENSOR_DEVICE_INFO,
    CHACON_BINARY_SENSOR_ENTITY_ID,
    CHACON_BINARY_SENSOR_FRIENDLY_NAME,
    CHACON_GROUP_ADDRESS,
    CHACON_ID_STRING,
    CHACON_LIGHT_DEVICE_INFO,
    CHACON_LIGHT_ENTITY_ID,
    CHACON_SWITCH_DEVICE_INFO,
    CHACON_SWITCH_ENTITY_ID,
    CHACON_UNIT_CODE,
    RTS_DEVICE_INFO,
    RTS_ENTITY_ID,
    RTS_ID_STRING,
    RTS_UNIT_CODE,
    X2D_ADDRESS,
    X2D_COMFORT_EVENT_DATA,
    X2D_DEVICE_INFO,
    X2D_ENTITY_ID,
    X2D_FRIENDLY_NAME,
    X2D_ID_STRING,
    X2D_ON_EVENT_DATA,
    X2D_PRESET_MODE,
    X2D_UNIT_CODE,
)


@pytest.mark.integration
async def test_binary_sensor_group_command(mock_serial_connection: Mock, hass: HomeAssistant):
    entry = await rfplayer_config_entry(hass, devices={CHACON_ID_STRING: CHACON_BINARY_SENSOR_DEVICE_INFO})
    assert_entity_state(hass, CHACON_BINARY_SENSOR_ENTITY_ID, STATE_UNKNOWN, CHACON_BINARY_SENSOR_FRIENDLY_NAME)

    entry.runtime_data.gateway.client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="CHACON", address=CHACON_GROUP_ADDRESS),
            data=RfPlayerEventData(CHACON_ALL_ON_EVENT_DATA),
        )
    )
    await hass.async_block_till_done()
    assert_entity_state(hass, CHACON_BINARY_SENSOR_ENTITY_ID, STATE_ON)


@pytest.mark.integration
async def test_climate_automatic_add_preset(mock_serial_connection: Mock, hass: HomeAssistant):
    entry = await rfplayer_config_entry(hass, automatic_add=True)
    client = entry.runtime_data.gateway.client

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="X2D", address=X2D_ADDRESS),
            data=RfPlayerEventData(X2D_ON_EVENT_DATA),
        )
    )
    await hass.async_block_till_done()
    state = assert_entity_state(hass, X2D_ENTITY_ID, HVACMode.HEAT, X2D_FRIENDLY_NAME)
    assert state.attributes[ATTR_PRESET_MODE] is None

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="X2D", address=X2D_ADDRESS),
            data=RfPlayerEventData(X2D_COMFORT_EVENT_DATA),
        )
    )
    await hass.async_block_till_done()
    state = assert_entity_state(hass, X2D_ENTITY_ID, HVACMode.HEAT, X2D_FRIENDLY_NAME)
    assert state.attributes[ATTR_PRESET_MODE] == X2D_PRESET_MODE


@pytest.mark.integration
async def test_light_command(mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    transport = cast(Mock, test_protocol.transport)
    await rfplayer_config_entry(hass, devices={CHACON_ID_STRING: CHACON_LIGHT_DEVICE_INFO})

    await hass.services.async_call(
        Platform.LIGHT,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: CHACON_LIGHT_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, CHACON_LIGHT_ENTITY_ID, STATE_ON)
    transport.write.assert_called_once_with(bytearray(f"ZIA++ON CHACON ID {CHACON_UNIT_CODE}\n\r".encode()))
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.LIGHT,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: CHACON_LIGHT_ENTITY_ID, ATTR_BRIGHTNESS: 100},
        blocking=True,
    )
    state = assert_entity_state(hass, CHACON_LIGHT_ENTITY_ID, STATE_ON)
    assert state.attributes[ATTR_BRIGHTNESS] == 100
    transport.write.assert_called_once_with(bytearray(f"ZIA++DIM CHACON ID {CHACON_UNIT_CODE} %39\n\r".encode()))
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.LIGHT,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: CHACON_LIGHT_ENTITY_ID},
        blocking=True,
    )
    state = assert_entity_state(hass, CHACON_LIGHT_ENTITY_ID, STATE_OFF)
    assert state.attributes[ATTR_BRIGHTNESS] is None
    transport.write.assert_called_once_with(bytearray(f"ZIA++OFF CHACON ID {CHACON_UNIT_CODE}\n\r".encode()))


@pytest.mark.integration
async def test_switch_command(mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    transport = cast(Mock, test_protocol.transport)
    await rfplayer_config_entry(hass, devices={CHACON_ID_STRING: CHACON_SWITCH_DEVICE_INFO})

    await hass.services.async_call(
        Platform.SWITCH,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: CHACON_SWITCH_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, CHACON_SWITCH_ENTITY_ID, STATE_ON)
    transport.write.assert_called_once_with(bytearray(f"ZIA++ON CHACON ID {CHACON_UNIT_CODE}\n\r".encode()))
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.SWITCH,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: CHACON_SWITCH_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, CHACON_SWITCH_ENTITY_ID, STATE_OFF)
    transport.write.assert_called_once_with(bytearray(f"ZIA++OFF CHACON ID {CHACON_UNIT_CODE}\n\r".encode()))


@pytest.mark.integration
async def test_cover_commands(mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    transport = cast(Mock, test_protocol.transport)
    await rfplayer_config_entry(hass, devices={RTS_ID_STRING: RTS_DEVICE_INFO})

    await hass.services.async_call(
        Platform.COVER,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: RTS_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, RTS_ENTITY_ID, STATE_CLOSED)
    transport.write.assert_called_once_with(f"ZIA++OFF RTS ID {RTS_UNIT_CODE} QUALIFIER 0\n\r".encode())
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.COVER,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: RTS_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, RTS_ENTITY_ID, STATE_OPEN)
    transport.write.assert_called_once_with(f"ZIA++ON RTS ID {RTS_UNIT_CODE} QUALIFIER 0\n\r".encode())
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.COVER,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: RTS_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, RTS_ENTITY_ID, STATE_OPEN)
    transport.write.assert_called_once_with(f"ZIA++DIM RTS ID {RTS_UNIT_CODE} %4\n\r".encode())


@pytest.mark.integration
async def test_climate_commands(mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    transport = cast(Mock, test_protocol.transport)
    await rfplayer_config_entry(hass, devices={X2D_ID_STRING: X2D_DEVICE_INFO})

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID},
        blocking=True,
    )
    state = assert_entity_state(hass, X2D_ENTITY_ID, STATE_OFF)
    assert state.attributes[ATTR_PRESET_MODE] is None
    transport.write.assert_called_once_with(f"ZIA++OFF X2DELEC ID {X2D_UNIT_CODE} %0\n\r".encode())
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID},
        blocking=True,
    )
    assert_entity_state(hass, X2D_ENTITY_ID, HVACMode.HEAT)
    transport.write.assert_called_once_with(f"ZIA++ON X2DELEC ID {X2D_UNIT_CODE} %0\n\r".encode())
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID, ATTR_HVAC_MODE: STATE_OFF},
        blocking=True,
    )
    assert_entity_state(hass, X2D_ENTITY_ID, STATE_OFF)
    transport.write.assert_called_once_with(f"ZIA++OFF X2DELEC ID {X2D_UNIT_CODE} %0\n\r".encode())
    transport.write.reset_mock()

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID, ATTR_PRESET_MODE: "Comfort"},
        blocking=True,
    )
    state = assert_entity_state(hass, X2D_ENTITY_ID, STATE_OFF)
    assert state.attributes[ATTR_PRESET_MODE] == "Comfort"
    transport.write.assert_called_once_with(f"ZIA++ON X2DELEC ID {X2D_UNIT_CODE} %3\n\r".encode())
