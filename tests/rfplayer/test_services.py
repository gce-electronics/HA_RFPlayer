from typing import cast
from unittest.mock import Mock

import pytest

from custom_components.rfplayer.const import DOMAIN
from custom_components.rfplayer.rfplayerlib.protocol import RfplayerProtocol
from custom_components.rfplayer.services import (
    SERVICE_SEND_PAIRING_COMMAND,
    SERVICE_SEND_RAW_COMMAND,
    SERVICE_SIMULATE_EVENT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from tests.rfplayer.constants import OREGON_ADDRESS, OREGON_EVENT_DATA, OREGON_ID_STRING

from .conftest import rfplayer_config_entry


@pytest.mark.integration
async def test_setup_registers_services(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test setup registers all RFPlayer services."""
    await rfplayer_config_entry(hass)

    assert hass.services.has_service(
        DOMAIN,
        SERVICE_SEND_RAW_COMMAND,
    )
    assert hass.services.has_service(
        DOMAIN,
        SERVICE_SEND_PAIRING_COMMAND,
    )
    assert hass.services.has_service(
        DOMAIN,
        SERVICE_SIMULATE_EVENT,
    )


@pytest.mark.integration
async def test_unload_removes_services(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test unloading removes all RFPlayer services."""
    entry = await rfplayer_config_entry(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_COMMAND)
    assert hass.services.has_service(DOMAIN, SERVICE_SEND_PAIRING_COMMAND)
    assert hass.services.has_service(DOMAIN, SERVICE_SIMULATE_EVENT)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_COMMAND)
    assert not hass.services.has_service(DOMAIN, SERVICE_SEND_PAIRING_COMMAND)
    assert not hass.services.has_service(DOMAIN, SERVICE_SIMULATE_EVENT)


@pytest.mark.integration
async def test_send_raw_command(
    mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    """Test configuration."""
    await rfplayer_config_entry(hass, devices={})

    await hass.services.async_call("rfplayer", "send_raw_command", {"command": "ON A3 RTS QUALIFIER 1"}, blocking=True)

    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(bytearray(b"ZIA++ON A3 RTS QUALIFIER 1\n\r"))


@pytest.mark.integration
async def test_send_pairing_command(
    mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    await rfplayer_config_entry(hass, devices={})

    await hass.services.async_call(
        "rfplayer", "send_pairing_command", {"protocol": "CHACON", "address": "A1"}, blocking=True
    )

    tr = cast(Mock, test_protocol.transport)
    tr.write.assert_called_once_with(bytearray(b"ZIA++ASSOC CHACON ID 0\n\r"))


@pytest.mark.integration
async def test_send_pairing_command_bad_address(
    mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    await rfplayer_config_entry(hass, devices={})

    with pytest.raises(ValueError, match="Invalid address"):
        await hass.services.async_call(
            "rfplayer", "send_pairing_command", {"protocol": "CHACON", "address": "A17"}, blocking=True
        )


@pytest.mark.integration
async def test_simulate_event(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    test_protocol: RfplayerProtocol,
) -> None:
    """Test configuration."""
    entry = await rfplayer_config_entry(hass, automatic_add=True, devices={})

    await hass.services.async_call("rfplayer", "simulate_event", {"event_data": OREGON_EVENT_DATA}, blocking=True)

    device_oregon = device_registry.async_get_device_by_identifier(
        identifier=(DOMAIN, OREGON_ID_STRING), config_entry_id=entry.entry_id
    )
    assert device_oregon is not None
    assert device_oregon.model == "PCR800"
    assert device_oregon.manufacturer == "OREGON"
    assert device_oregon.name == f"OREGON PCR800 {OREGON_ADDRESS}"
