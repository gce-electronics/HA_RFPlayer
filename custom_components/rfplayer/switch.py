"""Support for Rfplayer switch."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_DEVICES, CONF_PROTOCOL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DATA_DEVICE_REGISTER, EVENT_KEY_COMMAND, RfplayerDevice
from .const import (
    COMMAND_OFF,
    COMMAND_ON,
    CONF_AUTOMATIC_ADD,
    CONF_DEVICE_ADDRESS,
    DATA_ENTITY_LOOKUP,
    DOMAIN,
    EVENT_KEY_ID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Rfplayer platform."""
    config = entry.data
    options = entry.options

    async def add_new_device(device_info):
        """Check if device is known, otherwise create device entity."""
        # create entity
        device = RfplayerSwitch(
            event_id=device_info[EVENT_KEY_ID],
            protocol=device_info[CONF_PROTOCOL],
            device_address=device_info.get(CONF_DEVICE_ADDRESS),
            device_id=device_info.get(CONF_DEVICE_ID),
            initial_event=device_info,
        )
        _LOGGER.debug("Add switch entity %s", device_info)
        async_add_entities([device])

    if CONF_DEVICES in config:
        for device in config[CONF_DEVICES].values():
            if EVENT_KEY_COMMAND in device:
                await add_new_device(device)

    if options.get(CONF_AUTOMATIC_ADD, config[CONF_AUTOMATIC_ADD]):
        hass.data[DOMAIN][DATA_DEVICE_REGISTER][EVENT_KEY_COMMAND] = add_new_device


class RfplayerSwitch(RfplayerDevice, SwitchEntity):
    """Representation of a Rfplayer switch."""

    # pylint: disable-next=too-many-arguments
    def __init__(
        self,
        event_id: str,
        protocol: str,
        device_id: str | None = None,
        device_address: str | None = None,
        initial_event: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        """Handle switch specific args and super init."""
        self._state: bool | None = None
        if not (name or device_address or device_id) or not (
            device_address or device_id
        ):
            raise TypeError("Incorrect arguments for RfplayerSwitch")
        super().__init__(
            unique_id=event_id,
            protocol=protocol,
            device_id=device_address or device_id,
            event_type="command",
            initial_event=initial_event,
            name=name,
        )

    async def async_added_to_hass(self) -> None:
        """Restore RFPlayer device state (ON/OFF)."""
        await super().async_added_to_hass()

        if self._initial_event:
            self.hass.data[DOMAIN][DATA_ENTITY_LOOKUP][EVENT_KEY_COMMAND][
                self._initial_event[EVENT_KEY_ID]
            ] = self.entity_id

        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                self._state = old_state.state == COMMAND_ON

    @callback
    def _handle_event(self, event):
        command = event["state"]
        if command in [COMMAND_ON, "ALLON"]:
            self._state = True
        elif command in [COMMAND_OFF, "ALLOFF"]:
            self._state = False

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self._async_send_command(COMMAND_ON)
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self._async_send_command(COMMAND_OFF)
        self._state = False
        self.async_write_ha_state()
