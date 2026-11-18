"""Macht aus einem Cover ein 16×16-PNG, sonst eine Note."""

from __future__ import annotations

import io
import json
import urllib.parse
import urllib.request

from PIL import Image

from awtrix_itunes.log import log

USER_AGENT = "awtrix-apple-music-windows/1.0"
MAX_BYTES = 8_000_000

# Dieselbe Note wie im Mac-Helper, Zeile für Zeile von oben nach unten.
NOTE_ROWS = (
    "................",
    "................",
    ".......#######..",
    ".......#######..",
    ".......#.....#..",
    ".......#.....#..",
    ".......#.....#..",
    ".......#.....#..",
    ".......#.....#..",
    "....####..####..",
    "...#####.#####..",
    "...#####.#####..",
    "....###...###...",
    "................",
    "................",
    "................",
)

_note: bytes | None = None


def to_png16(raw: bytes) -> bytes:
    """Verkleinert ein Bild auf 16×16 und legt Transparenz auf dunkles Grau."""
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Cover fehlt oder ist zu groß")
    image = Image.open(io.BytesIO(raw)).convert("RGBA")
    image = image.resize((16, 16), Image.Resampling.LANCZOS)
    plate = Image.new("RGB", (16, 16), (0x20, 0x20, 0x20))
    plate.paste(image, mask=image.getchannel("A"))
    out = io.BytesIO()
    plate.save(out, format="PNG", optimize=True)
    return out.getvalue()


def note_png() -> bytes:
    """Weiße Note auf Grau, wenn nirgends ein Cover liegt."""
    global _note
    if _note is None:
        image = Image.new("RGB", (16, 16), (0x30, 0x30, 0x30))
        for y, row in enumerate(NOTE_ROWS):
            for x, pixel in enumerate(row):
                if pixel == "#":
                    image.putpixel((x, y), (255, 255, 255))
        out = io.BytesIO()
        image.save(out, format="PNG", optimize=True)
        _note = out.getvalue()
    return _note


class Artwork:
    """Cover aus dem Player, sonst die iTunes-Suche, sonst die Note."""

    def __init__(self, fetch=None):
        self.fetch = fetch_itunes_artwork if fetch is None else fetch

    def render(self, snap) -> tuple[bytes, bool]:
        """Liefert PNG-Bytes und ob das Bild dauerhaft gelten darf."""
        if snap.artwork:
            try:
                return to_png16(snap.artwork), True
            except Exception:
                log.info("Cover ließ sich nicht umrechnen")
        if snap.artist or snap.album:
            try:
                raw = self.fetch(snap.artist, snap.album)
                if raw:
                    return to_png16(raw), True
            except Exception:
                log.info("Cover-Suche fehlgeschlagen")
        return note_png(), False


def fetch_itunes_artwork(artist: str, album: str, opener=urllib.request.urlopen) -> bytes | None:
    """Gestreamte Titel geben ihr Cover oft nicht her. Dann fragt der Mac-Helper dieselbe Suche."""
    term = f"{artist} {album}".strip()
    if not term:
        return None
    query = urllib.parse.urlencode({"term": term, "entity": "album", "limit": 1})
    search = urllib.request.Request(
        f"https://itunes.apple.com/search?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    with opener(search, timeout=10) as response:
        payload = json.load(response)
    results = payload.get("results") or []
    if not results:
        return None
    url = results[0].get("artworkUrl100")
    if not url:
        return None
    image_request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener(image_request, timeout=10) as response:
        data = response.read()
    return data or None
