"""The tests for the RfPlayer component."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.rfplayer import async_unload_entry
from custom_components.rfplayer.runtime import RfPlayerRuntimeData
from homeassistant.core import HomeAssistant
from tests.rfplayer.conftest import rfplayer_config_entry


@pytest.mark.integration
async def test_setup_populates_runtime_data(
    mock_serial_connection: Mock,
    hass: HomeAssistant,
) -> None:
    """Test setup stores the gateway in config entry runtime data."""
    entry = await rfplayer_config_entry(hass)

    assert isinstance(entry.runtime_data, RfPlayerRuntimeData)
    assert entry.runtime_data.gateway is not None
    assert entry.runtime_data.gateway.entry is entry


@pytest.mark.integration
async def test_unload_entry_closes_gateway(
    hass: HomeAssistant,
) -> None:
    """Test unloading closes the gateway."""

    config_entry = await rfplayer_config_entry(hass, automatic_add=True)

    gateway = config_entry.runtime_data.gateway

    with patch.object(
        gateway,
        "async_unload",
        AsyncMock(),
    ) as unload:
        assert await async_unload_entry(hass, config_entry)

    unload.assert_awaited_once()
