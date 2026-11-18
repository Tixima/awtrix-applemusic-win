"""Festes Beispiel, damit die Uhr ohne Apple Music geprüft werden kann."""

from __future__ import annotations

import io
import time

from PIL import Image

from awtrix_itunes.media import PLAYING, Snapshot

_ART: bytes | None = None


def demo_png() -> bytes:
    global _ART
    if _ART is None:
        image = Image.new("RGB", (64, 64), (32, 96, 180))
        for x in range(16, 48):
            for y in range(16, 48):
                image.putpixel((x, y), (240, 176, 48))
        out = io.BytesIO()
        image.save(out, format="PNG")
        _ART = out.getvalue()
    return _ART


class DemoSource:
    def __init__(self, now=time.monotonic):
        self._now = now
        self._start = now()

    def read(self) -> Snapshot:
        elapsed = max(0.0, self._now() - self._start) % 200
        return Snapshot(PLAYING, "Probelauf", "AWTRIX", "Windows", round(elapsed, 1), 200.0, demo_png())
