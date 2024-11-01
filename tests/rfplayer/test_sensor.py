import json
from typing import cast
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.rfplayer.const import ATTR_EVENT_DATA, DOMAIN, RFPLAYER_CLIENT
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
    UnitOfPrecipitationDepth,
    UnitOfSoundPressure,
)
from homeassistant.core import HomeAssistant, State
from tests.rfplayer.conftest import create_rfplayer_test_cfg, setup_rfplayer_test_cfg
from tests.rfplayer.constants import (
    OREGON_ADDRESS,
    OREGON_DEVICE_INFO,
    OREGON_EVENT_DATA,
    OREGON_ID_STRING,
    OREGON_RAIN_SENSOR_ENTITY_ID,
    OREGON_RAIN_SENSOR_FRIENDLY_NAME,
    OREGON_RAIN_SENSOR_STATE,
    OREGON_RFLEVEL_SENSOR_ENTITY_ID,
    OREGON_RFLEVEL_SENSOR_FRIENDLY_NAME,
    OREGON_RFLEVEL_SENSOR_STATE,
)


async def test_sensor(serial_connection_mock: Mock, hass: HomeAssistant):
    entry_data = create_rfplayer_test_cfg(
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
        }
    )

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get(OREGON_RAIN_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == OREGON_RAIN_SENSOR_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_automatic_add(serial_connection_mock: Mock, hass: HomeAssistant):
    await setup_rfplayer_test_cfg(hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True)

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS),
            data=RfPlayerEventData(OREGON_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(OREGON_RAIN_SENSOR_ENTITY_ID)
    assert state
    assert state.state == OREGON_RAIN_SENSOR_STATE
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfPrecipitationDepth.MILLIMETERS
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == OREGON_RAIN_SENSOR_FRIENDLY_NAME

    state = hass.states.get(OREGON_RFLEVEL_SENSOR_ENTITY_ID)
    assert state
    assert state.state == OREGON_RFLEVEL_SENSOR_STATE
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfSoundPressure.DECIBEL
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == OREGON_RFLEVEL_SENSOR_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_state_restore(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """State restoration."""

    mock_restore_cache(
        hass,
        [
            State(
                OREGON_RAIN_SENSOR_ENTITY_ID,
                OREGON_RAIN_SENSOR_STATE,
                attributes={ATTR_EVENT_DATA: json.dumps(OREGON_EVENT_DATA)},
            )
        ],
    )

    entry_data = create_rfplayer_test_cfg(
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
        }
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(OREGON_RAIN_SENSOR_ENTITY_ID)
    assert state
    assert state.state == OREGON_RAIN_SENSOR_STATE
