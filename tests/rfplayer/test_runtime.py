import pytest

from custom_components.rfplayer.runtime import Gateway, RfPlayerRuntimeData
from homeassistant.core import HomeAssistant

from .conftest import setup_rfplayer_test_cfg


@pytest.mark.asyncio
async def test_setup_entry_stores_runtime_data(
    hass: HomeAssistant,
) -> None:
    """Test runtime data is stored on the config entry."""
    config_entry = await setup_rfplayer_test_cfg(
        hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True
    )

    assert isinstance(
        config_entry.runtime_data,
        RfPlayerRuntimeData,
    )

    assert isinstance(
        config_entry.runtime_data.gateway,
        Gateway,
    )
