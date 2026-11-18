"""Führt Mediensteuerung und, falls nötig, das klassische iTunes zusammen."""

from __future__ import annotations

import asyncio
import threading

from awtrix_itunes.log import log
from awtrix_itunes.media import ACTIVE, prefer
from awtrix_itunes.sessions import SmtcResult
from awtrix_itunes.windows_com import read_itunes_com


class WindowsMediaSource:
    def __init__(self, smtc=None, com=None):
        self._smtc = smtc
        self._com = read_itunes_com if com is None else com
        self._lock = threading.Lock()
        self._note = ""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client = None
        if smtc is None:
            from awtrix_itunes.windows_smtc import SmtcClient, ensure_winrt

            ensure_winrt()
            self._client = SmtcClient()
            self._start_loop()

    def read(self) -> Snapshot:
        with self._lock:
            smtc_result = self._safe_smtc()
            smtc_snap = smtc_result.snapshot
            detail = smtc_result.detail
            com_snap = None
            if smtc_snap is None or smtc_snap.state not in ACTIVE:
                com_snap = self._safe_com()
                if com_snap is not None and com_snap.state in ACTIVE:
                    detail = "Klassisches iTunes (COM)"
            chosen = prefer(smtc_snap, com_snap)
            self._say(detail)
            return chosen

    def _safe_smtc(self) -> SmtcResult:
        try:
            if self._smtc is not None:
                return self._smtc()
            return self._call_loop()
        except Exception:
            log.info("Mediensteuerung nicht erreichbar")
            return SmtcResult(None, "Mediensteuerung nicht erreichbar")

    def _safe_com(self) -> Snapshot | None:
        try:
            return self._com()
        except Exception:
            log.info("iTunes über COM nicht lesbar")
            return None

    def _say(self, detail: str) -> None:
        if detail and detail != self._note:
            self._note = detail
            log.info(detail)

    def _start_loop(self) -> None:
        ready = threading.Event()
        loop = asyncio.new_event_loop()

        def run() -> None:
            asyncio.set_event_loop(loop)
            ready.set()
            loop.run_forever()

        thread = threading.Thread(target=run, name="awtrix-smtc", daemon=True)
        thread.start()
        if not ready.wait(5):
            raise SystemExit("Die Mediensteuerung konnte nicht gestartet werden.")
        self._loop = loop
        try:
            asyncio.run_coroutine_threadsafe(self._client.connect(), loop).result(timeout=15)
        except Exception as exc:
            raise SystemExit(f"Die Mediensteuerung antwortet nicht: {exc}") from exc

    def _call_loop(self) -> SmtcResult:
        if self._loop is None or self._client is None:
            raise RuntimeError("Mediensteuerung ist nicht gestartet")
        future = asyncio.run_coroutine_threadsafe(self._client.read(), self._loop)
        return future.result(timeout=8)
