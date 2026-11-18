"""Windows-Mediensteuerung. Die Aufrufe liegen nur hier, damit der Rest überall testbar bleibt."""

from __future__ import annotations

from datetime import datetime, timezone

from awtrix_itunes.log import once
from awtrix_itunes.sessions import collect_snapshot


def ensure_winrt() -> None:
    try:
        import winrt.windows.media.control  # noqa: F401
        import winrt.windows.storage.streams  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Die Windows-Pakete fehlen. Im Projektordner ausführen:\n"
            "  py -3 -m pip install -r requirements.txt"
        ) from exc


class SmtcClient:
    """Hält die Sitzungsliste und liest sie auf dem asyncio-Thread."""

    def __init__(self):
        self._manager = None

    async def read(self):
        try:
            await self.connect()
            sessions = list(self._manager.get_sessions() or [])
        except Exception:
            self._manager = None
            raise
        return await collect_snapshot(sessions, read_thumbnail, datetime.now(timezone.utc))

    async def connect(self) -> None:
        if self._manager is not None:
            return
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )

        self._manager = await Manager.request_async()


async def read_thumbnail(stream_ref) -> bytes | None:
    """Liest das Cover, das die Mediensteuerung mitliefert."""
    from winrt.windows.storage.streams import Buffer, InputStreamOptions

    try:
        stream = await stream_ref.open_read_async()
    except Exception:
        once("Cover von der Mediensteuerung nicht lesbar")
        return None
    try:
        size = int(stream.size)
        if size <= 0 or size > 8_000_000:
            return None
        buffer = Buffer(size)
        await stream.read_async(buffer, size, InputStreamOptions.READ_AHEAD)
        length = int(buffer.length) or size
        data = bytes(memoryview(buffer))[:length]
        return data or None
    except Exception:
        once("Cover von der Mediensteuerung nicht lesbar")
        return None
    finally:
        close = getattr(stream, "close", None)
        if close is not None:
            close()
