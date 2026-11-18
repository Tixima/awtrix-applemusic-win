"""Fragt den Player höchstens einmal pro Sekunde und merkt sich die Cover."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from awtrix_itunes.log import log
from awtrix_itunes.media import ACTIVE, OFF, PAUSED, PLAYING, Snapshot, art_key

NOTE_TTL = 30.0
CACHE_LIMIT = 32


@dataclass
class CachedImage:
    png: bytes
    cacheable: bool
    until: float | None

    def fresh(self, now: float) -> bool:
        if self.cacheable:
            return True
        return self.until is not None and now < self.until


class Player:
    def __init__(self, source, artwork, interval: float = 1.0, now=time.monotonic):
        self.source = source
        self.artwork = artwork
        self.interval = interval
        self._now = now
        self._read_at: float | None = None
        self.snap = Snapshot(OFF)
        self._pending: dict[str, Snapshot] = {}
        self._cache: dict[str, CachedImage] = {}
        self._order: list[str] = []
        self._label = ""
        self._lock = threading.Lock()

    def current(self) -> dict:
        with self._lock:
            return self._current()

    def _current(self) -> dict:
        snap = self._fresh()
        self._announce(snap)
        if snap.state not in ACTIVE:
            return {"s": snap.state}
        key = art_key(snap.artist, snap.album, snap.title)
        cached = self._cache.get(key)
        if cached is None or not cached.cacheable:
            self._pending[key] = snap
        return {
            "s": snap.state,
            "t": snap.title,
            "a": snap.artist,
            "al": snap.album,
            "p": snap.position,
            "d": snap.duration,
            "art": f"/art/{key}.png",
        }

    def artwork_for(self, key: str) -> tuple[bytes, bool] | None:
        with self._lock:
            now = self._now()
            cached = self._cache.get(key)
            if cached is not None and cached.fresh(now):
                return cached.png, cached.cacheable
            snap = self._pending.get(key)
        if snap is None:
            return None
        png, cacheable = self.artwork.render(snap)
        until = None if cacheable else self._now() + NOTE_TTL
        with self._lock:
            self._store(key, CachedImage(png, cacheable, until))
            if cacheable:
                self._pending.pop(key, None)
        return png, cacheable

    def _fresh(self) -> Snapshot:
        now = self._now()
        if self._read_at is not None and now - self._read_at < self.interval:
            return self.snap
        try:
            self.snap = self.source.read()
        except Exception:
            log.info("Wiedergabe konnte nicht gelesen werden")
            self.snap = Snapshot(OFF)
        self._read_at = now
        return self.snap

    def _announce(self, snap: Snapshot) -> None:
        if snap.state == PLAYING:
            label = f"spielt: {snap.title} — {snap.artist}"
        elif snap.state == PAUSED:
            label = f"Pause: {snap.title} — {snap.artist}"
        else:
            label = f"Wiedergabe: {snap.state}"
        if label != self._label:
            self._label = label
            log.info(label)

    def _store(self, key: str, item: CachedImage) -> None:
        if key in self._cache:
            self._order = [item_key for item_key in self._order if item_key != key]
        self._cache[key] = item
        self._order.append(key)
        while len(self._order) > CACHE_LIMIT:
            oldest = self._order.pop(0)
            self._cache.pop(oldest, None)
            self._pending.pop(oldest, None)
