"""Connection lifecycle for an RFPlayer device."""

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import dataclass
import logging

from custom_components.rfplayer.const import CONNECTION_TIMEOUT
from custom_components.rfplayer.rfplayerlib import RfPlayerClient, RfPlayerException
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent
from homeassistant.core import CoreState, HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RfPlayerSessionConfig:
    """Connection settings for one RFPlayer session."""

    device: str
    receiver_protocols: list[str]
    init_commands: list[str]
    verbose_mode: bool
    reconnect_interval: int


@dataclass(frozen=True, slots=True)
class RfPlayerSessionCallbacks:
    """Callbacks connecting a session to its owner."""

    receive: Callable[[RfDeviceEvent], None]
    connected: Callable[[], None]
    disconnected: Callable[[], None]


class RfPlayerSession:
    """Own an active RFPlayer client connection and its reconnect lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: RfPlayerSessionConfig,
        callbacks: RfPlayerSessionCallbacks,
    ) -> None:
        """Create a session for one RFPlayer connection."""
        self.hass = hass
        self.reconnect_interval = config.reconnect_interval
        self.callbacks = callbacks
        self._reconnect_task: asyncio.Task[None] | None = None
        self._unloading = False
        self.client = RfPlayerClient(
            event_callback=callbacks.receive,
            disconnect_callback=self._handle_disconnect,
            port=config.device,
            receiver_protocols=config.receiver_protocols,
            init_commands=config.init_commands,
            verbose=config.verbose_mode,
        )

    async def async_setup(self) -> None:
        """Connect to the RFPlayer."""
        await self._connect_client()

    async def async_unload(self) -> None:
        """Close the client and cancel any pending reconnect."""
        self._unloading = True
        await self._cancel_reconnect_task()
        self.client.close()

    @property
    def is_stopping(self) -> bool:
        """Return whether Home Assistant or this session is stopping."""
        return self._unloading or self.hass.state is CoreState.stopping

    async def _connect_client(self) -> None:
        """Connect and notify the owner that the client is available."""
        _LOGGER.debug("Initiating RFPlayer connection")
        if self.is_stopping:
            _LOGGER.debug("Not connecting to RFPlayer because Home Assistant is stopping")
            return

        connect_task = self.hass.async_create_task(self.client.connect())
        await asyncio.wait_for(connect_task, timeout=CONNECTION_TIMEOUT)
        self.callbacks.connected()
        _LOGGER.debug("Connected to RFPlayer")

    @callback
    def _handle_disconnect(self, exc: Exception | None = None) -> None:
        """Notify the owner and schedule a reconnect after a disconnect."""
        if exc:
            _LOGGER.warning("Connection error %s", exc)
        else:
            _LOGGER.info("Connection explicitly closed")

        self.callbacks.disconnected()
        if self.is_stopping:
            return

        if self._reconnect_task is not None and not self._reconnect_task.done():
            return

        self._reconnect_task = self.hass.async_create_task(self._reconnect_after_delay())

    async def _reconnect_after_delay(self) -> None:
        """Retry the connection until it succeeds or shutdown begins."""
        try:
            while not self.is_stopping:
                await asyncio.sleep(self.reconnect_interval)
                if self.is_stopping:
                    return

                try:
                    await self._connect_client()
                except (RfPlayerException, TimeoutError) as exc:
                    _LOGGER.warning("Reconnect failed: %s", exc)
                    continue
                return
        except asyncio.CancelledError:
            _LOGGER.debug("Reconnect task cancelled")
        finally:
            self._reconnect_task = None

    async def _cancel_reconnect_task(self) -> None:
        """Cancel and await the reconnect task if one is pending."""
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None
