"""Test the RfPlayer config flow."""

import json
import os
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch, sentinel

import probatio
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_mock import MockerFixture

from custom_components.rfplayer import config_flow
from custom_components.rfplayer.const import DOMAIN, INIT_COMMANDS_EMPTY
from custom_components.rfplayer.helpers import get_rf_device_identifiers
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData, RfplayerProtocol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import STATE_OFF, STATE_OPEN, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntry
from tests.rfplayer.conftest import create_rfplayer_test_config, create_rfplayer_test_options, rfplayer_config_entry
from tests.rfplayer.constants import (
    CHACON_BINARY_SENSOR_DEVICE_INFO,
    OREGON_ADDRESS,
    OREGON_BINARY_SENSOR_ENTITY_ID,
    OREGON_BINARY_SENSOR_FRIENDLY_NAME,
    OREGON_DEVICE_INFO,
    OREGON_EVENT_DATA,
    OREGON_ID_STRING,
    OREGON_REDIRECT_ADDRESS,
    RTS_DEVICE_INFO,
    RTS_ENTITY_ID,
    RTS_FRIENDLY_NAME,
    RTS_ID_STRING,
    SYSTEM_STATUS,
)

SOME_PROTOCOLS = ["ac", "arc"]
ALL_RECEIVER_PROTOCOLS = [
    "X10",
    "RTS",
    "VISONIC",
    "BLYSS",
    "CHACON",
    "OREGONV1",
    "OREGONV2",
    "OREGONV3/OWL",
    "DOMIA",
    "X2D",
    "KD101",
    "PARROT",
    "TIC",
    "FS20",
    "JAMMING",
    "EDISIO",
]


def com_port():
    """Mock of a serial port."""
    port = Mock()
    port.device = "/dev/ttyUSB1234"
    port.serial_number = "1234"
    port.manufacturer = "Virtual serial port"
    port.device = "/dev/ttyUSB1234"
    port.description = "Some serial port"

    return port


def assert_device_exists(
    device_registry: dr.DeviceRegistry, config_entry: ConfigEntry, rf_device_id: RfDeviceId
) -> DeviceEntry:
    identifier = list(get_rf_device_identifiers(rf_device_id))[0]
    device_entry = device_registry.async_get_device_by_identifier(
        identifier=identifier, config_entry_id=config_entry.entry_id
    )
    assert device_entry
    return device_entry


async def start_options_flow(hass: HomeAssistant, entry: MockConfigEntry) -> ConfigFlowResult:
    """Start the options flow with the entry under test."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await hass.config_entries.options.async_init(entry.entry_id)


@pytest.mark.integration
@patch("serialx.tools.list_ports.comports", return_value=[com_port()])
async def test_setup_serial(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we can setup serial."""
    port = com_port()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "serial"})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "serial"

    with (
        patch("custom_components.rfplayer.async_setup_entry", return_value=True),
        patch(
            "custom_components.rfplayer.probe.RfPlayerClient",
            return_value=AsyncMock(send_raw_request=AsyncMock(return_value=json.dumps(SYSTEM_STATUS)), close=Mock()),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_serial": port.device,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "/dev/ttyUSB1234"
    assert result["data"] == {
        "device": port.device,
    }


@pytest.mark.integration
@patch("serialx.tools.list_ports.comports", return_value=[com_port()])
async def test_setup_serial_connection_failed(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we can setup serial."""
    port = com_port()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] is FlowResultType.MENU

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "serial"})

    with patch(
        "custom_components.rfplayer.probe.RfPlayerClient",
        return_value=AsyncMock(
            send_raw_request=AsyncMock(side_effect=RfPlayerException),
            close=Mock(),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"device_serial": port.device},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "serial"
    assert result["errors"] == {"device_serial": "cannot_connect"}


@pytest.mark.integration
async def test_setup_serial_simulator(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we can setup serial with manual entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "simulator"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "simulator"

    with patch("custom_components.rfplayer.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "/simulator"
    assert result["data"] == {
        "device": "/simulator",
    }


@pytest.mark.integration
async def test_setup_tcp(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we can setup serial with manual entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "network"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "network"

    with (
        patch("custom_components.rfplayer.async_setup_entry", return_value=True),
        patch(
            "custom_components.rfplayer.probe.RfPlayerClient",
            return_value=AsyncMock(send_raw_request=AsyncMock(return_value=json.dumps(SYSTEM_STATUS)), close=Mock()),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"ip_address": "192.168.1.100", "port": 1234}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "tcp://192.168.1.100:1234"
    assert result["data"] == {
        "device": "tcp://192.168.1.100:1234",
    }


@pytest.mark.integration
async def test_setup_tcp_connection_failed(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we can setup serial."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "network"})

    with patch(
        "custom_components.rfplayer.probe.RfPlayerClient",
        return_value=AsyncMock(
            send_raw_request=AsyncMock(side_effect=RfPlayerException),
            close=Mock(),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"ip_address": "192.168.1.100", "port": 1234}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"ip_address": "cannot_connect"}


@pytest.mark.integration
async def test_setup_tcp_invalid_ip_does_not_probe(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """An invalid IP should return a form error without attempting a connection."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "network"})

    with patch("custom_components.rfplayer.config_flow.async_get_rfplayer_unique_id") as probe:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"ip_address": "not-an-ip", "port": 1234}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"ip_address": "invalid_ip_address"}
    probe.assert_not_awaited()


@pytest.mark.unit
async def test_unique_id_probe_closes_client() -> None:
    """The temporary connection used for probing must be released."""
    client = Mock(
        connect=AsyncMock(),
        send_raw_request=AsyncMock(return_value=json.dumps(SYSTEM_STATUS)),
        close=Mock(),
    )

    with patch("custom_components.rfplayer.probe.RfPlayerClient", return_value=client):
        unique_id = await config_flow.async_get_rfplayer_unique_id("/dev/ttyUSB1234")

    assert unique_id
    client.close.assert_called_once_with()


@pytest.mark.integration
async def test_duplicate_gateway_mac_is_rejected(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "simulator"})

    with patch("custom_components.rfplayer.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "simulator"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.integration
@pytest.mark.parametrize("step_id", ["configure_gateway", "add_rf_device", "configure_rf_device"])
async def test_options_form_schema_serializable(
    mock_serial_connection: Mock, hass: HomeAssistant, step_id: str
) -> None:
    """Test options forms can be serialized for the frontend like the HA flow API does."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=create_rfplayer_test_config(),
        options=create_rfplayer_test_options(devices={OREGON_ID_STRING: OREGON_DEVICE_INFO}),
        unique_id=DOMAIN,
        version=2,
        minor_version=0,
    )
    result = await start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"next_step_id": step_id})

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == step_id
    assert probatio.to_field_list(result["data_schema"], custom_serializer=cv.custom_serializer)


@pytest.mark.integration
async def test_options_gateway(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test if we can set global options."""
    entry = await rfplayer_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "configure_gateway"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "configure_gateway"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "automatic_add": True,
            "reconnect_interval": 20,
            "receiver_protocols": ["RTS"],
            "init_commands": INIT_COMMANDS_EMPTY,
            "verbose_mode": True,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert entry.options["automatic_add"]
    assert entry.options["reconnect_interval"] == 20
    assert entry.options["receiver_protocols"] == ["RTS"]
    assert entry.options["init_commands"] == ""
    assert entry.options["verbose_mode"] is True


@pytest.mark.integration
async def test_options_gateway_no_receiver_protocols(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we set protocols to None if none are selected."""
    entry = await rfplayer_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "configure_gateway"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "configure_gateway"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "automatic_add": False,
            "reconnect_interval": 20,
            "receiver_protocols": [],
            "init_commands": INIT_COMMANDS_EMPTY,
            "verbose_mode": True,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"receiver_protocols": "no_receiver_protocol"}


@pytest.mark.integration
async def test_options_gateway_init_commands(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we set protocols to None if none are selected."""
    entry = await rfplayer_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert entry.options["init_commands"] == INIT_COMMANDS_EMPTY

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "configure_gateway"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "configure_gateway"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "automatic_add": False,
            "reconnect_interval": 20,
            "receiver_protocols": ["RTS"],
            "init_commands": "PING,HELLO",
            "verbose_mode": True,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert entry.options["init_commands"] == "PING,HELLO"


@pytest.mark.integration
async def test_options_discover_and_add_rf_device(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test discovering and adding a device from an RF event."""
    entry = await rfplayer_config_entry(hass)
    event = RfDeviceEvent(
        device=RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS, model="PCR800"),
        data=RfPlayerEventData(OREGON_EVENT_DATA),
    )
    gateway = entry.runtime_data.gateway

    with (
        patch.object(gateway, "start_discovery") as start_discovery,
        patch.object(gateway, "stop_discovery", return_value=[event]) as stop_discovery,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] is FlowResultType.MENU
        assert "discover_rf_devices" in result["menu_options"]

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "discover_rf_devices"}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "finish_discovery"
        start_discovery.assert_called_once_with()

        result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "select_discovered_device"
        stop_discovery.assert_called_once_with()

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"discovered_device": OREGON_ID_STRING}
        )

        assert result["type"] is FlowResultType.MENU
        assert result["step_id"] == "discovered_device_action"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "add_discovered_device"}
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert entry.options["devices"][OREGON_ID_STRING]["protocol"] == "OREGON"
    assert entry.options["devices"][OREGON_ID_STRING]["address"] == OREGON_ADDRESS
    assert entry.options["devices"][OREGON_ID_STRING]["profile_name"] == "Oregon Rain Sensor"


@pytest.mark.integration
async def test_options_discover_and_replace_rf_device(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test mapping a discovered ID to an existing configured device."""
    entry = await rfplayer_config_entry(hass, devices={OREGON_ID_STRING: OREGON_DEVICE_INFO})
    discovered_address = "59168"
    event = RfDeviceEvent(
        device=RfDeviceId(protocol="OREGON", address=discovered_address, model="PCR800"),
        data=RfPlayerEventData(OREGON_EVENT_DATA),
    )
    discovered_id = RfDeviceId(protocol="OREGON", address=discovered_address).canonical_id
    gateway = entry.runtime_data.gateway

    with (
        patch.object(gateway, "start_discovery"),
        patch.object(gateway, "stop_discovery", return_value=[event]),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "discover_rf_devices"}
        )
        result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"discovered_device": discovered_id}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "replace_device"}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "replace_device"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"existing_device": OREGON_ID_STRING}
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert entry.options["devices"][OREGON_ID_STRING]["address"] == OREGON_ADDRESS
    assert entry.options["devices"][OREGON_ID_STRING]["redirect_address"] == discovered_address


@pytest.mark.integration
async def test_options_discover_rf_devices_no_supported_devices(
    mock_serial_connection: Mock, hass: HomeAssistant
) -> None:
    """Test discovery aborts when no supported devices are captured."""
    entry = await rfplayer_config_entry(hass)
    gateway = entry.runtime_data.gateway

    with (
        patch.object(gateway, "start_discovery"),
        patch.object(gateway, "stop_discovery", return_value=[]),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "discover_rf_devices"}
        )
        result = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


@pytest.mark.integration
async def test_options_add_rf_device(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Test we can add a device."""
    entry = await rfplayer_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "add_rf_device"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_rf_device"

    device_options = RTS_DEVICE_INFO.copy()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=device_options,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    device_options = entry.options["devices"][RTS_ID_STRING]

    assert not device_options["redirect_address"]
    assert device_options["profile_name"] == RTS_DEVICE_INFO["profile_name"]

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_OPEN
    assert state.attributes.get("friendly_name") == RTS_FRIENDLY_NAME


@pytest.mark.integration
async def test_options_add_rf_device_bad_protocol(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    entry = await rfplayer_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "add_rf_device"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_rf_device"

    device_options = OREGON_DEVICE_INFO.copy()
    device_options.update({"profile_name": CHACON_BINARY_SENSOR_DEVICE_INFO["profile_name"]})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=device_options,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"protocol": "incompatible_protocol"}


@pytest.mark.integration
async def test_options_add_rf_device_bad_address(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    entry = await rfplayer_config_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "add_rf_device"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_rf_device"

    device_options = OREGON_DEVICE_INFO.copy()
    device_options["address"] = "A17"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=device_options,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"address": "invalid_address"}


async def start_add_rf_device_form(hass: HomeAssistant, entry: MockConfigEntry) -> ConfigFlowResult:
    """Open the options flow on the add RF device form."""
    result = await start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "add_rf_device"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_rf_device"
    return result


@pytest.mark.integration
async def test_options_add_rf_device_with_pairing(
    mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    """Test adding a device sends the pairing command and does not store the pairing flag."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=create_rfplayer_test_config(),
        options=create_rfplayer_test_options(),
        unique_id=DOMAIN,
        version=2,
        minor_version=0,
    )
    result = await start_add_rf_device_form(hass, entry)
    tr = cast(Mock, test_protocol.transport)
    tr.write.reset_mock()

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**RTS_DEVICE_INFO, "send_pairing_command": True},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    integer_address = RfDeviceId(protocol="RTS", address=RTS_DEVICE_INFO["address"]).integer_address
    tr.write.assert_called_once_with(bytearray(f"ZIA++ASSOC RTS ID {integer_address}\n\r".encode()))
    assert "send_pairing_command" not in entry.options["devices"][RTS_ID_STRING]


@pytest.mark.integration
async def test_options_add_rf_device_pairing_not_supported(
    mock_serial_connection: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol
) -> None:
    """Test pairing is refused for a receive-only protocol."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=create_rfplayer_test_config(),
        options=create_rfplayer_test_options(),
        unique_id=DOMAIN,
        version=2,
        minor_version=0,
    )
    result = await start_add_rf_device_form(hass, entry)
    tr = cast(Mock, test_protocol.transport)
    tr.write.reset_mock()

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**OREGON_DEVICE_INFO, "send_pairing_command": True},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"send_pairing_command": "pairing_not_supported"}
    tr.write.assert_not_called()
    assert OREGON_ID_STRING not in entry.options["devices"]


@pytest.mark.integration
async def test_options_add_rf_device_pairing_disconnected(
    mock_serial_connection: Mock, hass: HomeAssistant, mocker: MockerFixture
) -> None:
    """Test the device is not saved when the pairing command cannot be sent."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=create_rfplayer_test_config(),
        options=create_rfplayer_test_options(),
        unique_id=DOMAIN,
        version=2,
        minor_version=0,
    )
    result = await start_add_rf_device_form(hass, entry)
    mocker.patch.object(RfPlayerClient, "connected", new_callable=PropertyMock, return_value=False)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**RTS_DEVICE_INFO, "send_pairing_command": True},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert RTS_ID_STRING not in entry.options["devices"]


@pytest.mark.integration
async def test_options_add_rf_device_duplicate(mock_serial_connection: Mock, hass: HomeAssistant) -> None:
    """Adding an already configured protocol/address must not replace its options."""
    entry = await rfplayer_config_entry(hass, devices={RTS_ID_STRING: RTS_DEVICE_INFO})
    original_device = entry.options["devices"][RTS_ID_STRING].copy()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "add_rf_device"}
    )

    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input=RTS_DEVICE_INFO.copy())

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"address": "duplicate_device"}
    assert entry.options["devices"][RTS_ID_STRING] == original_device


@pytest.mark.integration
async def test_options_configure_rf_device(
    mock_serial_connection: Mock, hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> None:
    """Test we can configure an already created device."""

    entry = await rfplayer_config_entry(hass, devices={OREGON_ID_STRING: OREGON_DEVICE_INFO})
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "configure_rf_device"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "configure_rf_device"
    fields = probatio.to_field_list(result["data_schema"])
    assert isinstance(fields, list)
    assert {field["name"] for field in fields} == {
        "device",
        "redirect_address",
    }

    device_id = RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS)
    device_entry = assert_device_exists(device_registry, entry, device_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"device": device_entry.id, "redirect_address": OREGON_REDIRECT_ADDRESS},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert entry.options["devices"][OREGON_ID_STRING]["redirect_address"] == OREGON_REDIRECT_ADDRESS
    assert entry.options["devices"][OREGON_ID_STRING]["profile_name"] == OREGON_DEVICE_INFO["profile_name"]

    state = hass.states.get(OREGON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get("friendly_name") == OREGON_BINARY_SENSOR_FRIENDLY_NAME

    client = entry.runtime_data.gateway.client

    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="OREGON", address=OREGON_REDIRECT_ADDRESS, model="PCR800"),
            data=RfPlayerEventData(OREGON_EVENT_DATA),
        )
    )

    state = hass.states.get(OREGON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_OFF

    # ----------------------------------------------------------------------------------

    device_entry = assert_device_exists(device_registry, entry, device_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "configure_rf_device"},
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "device": device_entry.id,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    assert not entry.options["devices"][OREGON_ID_STRING]["redirect_address"]
    assert entry.options["devices"][OREGON_ID_STRING]["profile_name"] == OREGON_DEVICE_INFO["profile_name"]


@pytest.mark.unit
def test_get_serial_by_id_no_dir() -> None:
    """Test serial by id conversion if there's no /dev/serial/by-id."""
    p1 = patch("os.path.isdir", MagicMock(return_value=False))
    p2 = patch("os.scandir")
    with p1 as is_dir_mock, p2 as scan_mock:
        res = config_flow.get_serial_by_id(sentinel.path)
        assert res is sentinel.path
        assert is_dir_mock.call_count == 1
        assert scan_mock.call_count == 0


@pytest.mark.unit
def test_get_serial_by_id() -> None:
    """Test serial by id conversion."""
    p1 = patch("os.path.isdir", MagicMock(return_value=True))
    p2 = patch("os.scandir")

    def _realpath(path):
        if path is sentinel.matched_link:
            return sentinel.path
        return sentinel.serial_link_path

    p3 = patch("os.path.realpath", side_effect=_realpath)
    with p1 as is_dir_mock, p2 as scan_mock, p3:
        res = config_flow.get_serial_by_id(sentinel.path)
        assert res is sentinel.path
        assert is_dir_mock.call_count == 1
        assert scan_mock.call_count == 1

        entry1 = MagicMock(spec_set=os.DirEntry)
        entry1.is_symlink.return_value = True
        entry1.path = sentinel.some_path

        entry2 = MagicMock(spec_set=os.DirEntry)
        entry2.is_symlink.return_value = False
        entry2.path = sentinel.other_path

        entry3 = MagicMock(spec_set=os.DirEntry)
        entry3.is_symlink.return_value = True
        entry3.path = sentinel.matched_link

        scan_mock.return_value = [entry1, entry2, entry3]
        res = config_flow.get_serial_by_id(sentinel.path)
        assert res is sentinel.matched_link
        assert is_dir_mock.call_count == 2
        assert scan_mock.call_count == 2
