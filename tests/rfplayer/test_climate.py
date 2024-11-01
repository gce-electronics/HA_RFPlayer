import json
from typing import cast
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.rfplayer.const import ATTR_EVENT_DATA, DOMAIN, RFPLAYER_CLIENT
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData, RfplayerProtocol
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    Platform,
)
from homeassistant.core import HomeAssistant, State
from tests.rfplayer.conftest import create_rfplayer_test_cfg, setup_rfplayer_test_cfg
from tests.rfplayer.constants import (
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


@pytest.mark.asyncio
async def test_climate(serial_connection_mock: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    tr = cast(Mock, test_protocol.transport)

    entry_data = create_rfplayer_test_cfg(
        devices={
            X2D_ID_STRING: X2D_DEVICE_INFO,
        }
    )

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == "heat"
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == X2D_FRIENDLY_NAME

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_PRESET_MODE] is None
    tr.write.assert_called_once_with(f"ZIA++OFF X2DELEC ID {X2D_UNIT_CODE} %0\n\r".encode())
    tr.write.reset_mock()

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == HVACMode.HEAT
    assert state.attributes.get(ATTR_PRESET_MODE) is None
    tr.write.assert_called_once_with(f"ZIA++ON X2DELEC ID {X2D_UNIT_CODE} %0\n\r".encode())
    tr.write.reset_mock()

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID, ATTR_HVAC_MODE: STATE_OFF},
        blocking=True,
    )

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == STATE_OFF
    tr.write.assert_called_once_with(f"ZIA++OFF X2DELEC ID {X2D_UNIT_CODE} %0\n\r".encode())
    tr.write.reset_mock()

    await hass.services.async_call(
        Platform.CLIMATE,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: X2D_ENTITY_ID, ATTR_PRESET_MODE: "Comfort"},
        blocking=True,
    )

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_PRESET_MODE] == "Comfort"
    tr.write.assert_called_once_with(f"ZIA++ON X2DELEC ID {X2D_UNIT_CODE} %3\n\r".encode())


@pytest.mark.asyncio
async def test_automatic_add(serial_connection_mock: Mock, hass: HomeAssistant):
    await setup_rfplayer_test_cfg(hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True)

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="X2D", address=X2D_ADDRESS),
            data=RfPlayerEventData(X2D_ON_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_PRESET_MODE] is None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == X2D_FRIENDLY_NAME

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="X2D", address=X2D_ADDRESS),
            data=RfPlayerEventData(X2D_COMFORT_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_PRESET_MODE] == X2D_PRESET_MODE
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == X2D_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_state_restore(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """State restoration."""

    mock_restore_cache(
        hass,
        [
            State(
                X2D_ENTITY_ID,
                HVACMode.HEAT,
                attributes={ATTR_EVENT_DATA: json.dumps(X2D_ON_EVENT_DATA)},
            )
        ],
    )

    entry_data = create_rfplayer_test_cfg(
        devices={
            X2D_ID_STRING: X2D_DEVICE_INFO,
        }
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(X2D_ENTITY_ID)
    assert state
    assert state.state == HVACMode.HEAT
    # TODO Check we can restore both hvac mode and preset mode cause it can be on 2 different events
