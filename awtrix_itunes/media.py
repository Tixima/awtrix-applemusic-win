"""Reines Abbild eines Titels, ohne Windows-Aufrufe."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

PLAYING = "playing"
PAUSED = "paused"
STOPPED = "stopped"
OFF = "off"

ACTIVE = (PLAYING, PAUSED)

STATE_WORD = {
    PLAYING: "spielt",
    PAUSED: "Pause",
    STOPPED: "gestoppt",
    OFF: "aus",
}


@dataclass(frozen=True)
class Snapshot:
    """Was der Player gerade tut. `artwork` sind die Originalbytes des Covers."""

    state: str
    title: str = ""
    artist: str = ""
    album: str = ""
    position: float = 0.0
    duration: float = 0.0
    artwork: bytes | None = None


def art_key(artist: str, album: str, title: str) -> str:
    """Dieselbe Kurz-ID wie der Mac-Helper: pro Album, ohne Album pro Titel."""
    marker = title if not album else ""
    raw = f"{artist}\n{album}\n{marker}".encode()
    return hashlib.sha1(raw).hexdigest()[:12]


def text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_meta(title: object, artist: object, album: object, album_artist: object = "") -> tuple[str, str, str]:
    """Übernimmt den Interpreten aus dem Album-Interpreten, wenn das Feld leer ist.

    Apple Music für Windows lässt `artist` manchmal leer und schreibt
    „Interpret - Album“ in `album_artist`.
    """
    title_text = text(title)
    artist_text = text(artist)
    album_text = text(album)
    album_artist_text = text(album_artist)
    if not artist_text and album_artist_text:
        artist_text = artist_from_album_artist(album_artist_text, album_text, title_text)
    return title_text, artist_text, album_text


def artist_from_album_artist(album_artist: str, album: str, title: str = "") -> str:
    """Trennt „Interpret - Album“ und schneidet ein angehängtes „Single“ ab."""
    text = album_artist.strip()
    for suffix in (" - Single", " - EP", " - Album"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].rstrip()
    if " - " in text:
        head, _, tail = text.rpartition(" - ")
        head = head.strip()
        tail = tail.strip()
        if head and tail and tail in {album, title}:
            return head
    return text


def is_apple_session(aumid: str) -> bool:
    """Erkennt Apple Music (Windows 10 und 11) und das klassische iTunes."""
    if not aumid:
        return False
    normalized = aumid.strip().lower().replace("\\", "/")
    base = normalized.split("/")[-1]
    if base in {"applemusic.exe", "itunes.exe", "itunes"}:
        return True
    if "applemusic" in normalized:
        return True
    return "!itunes" in normalized


def state_from_status(status: object) -> str:
    """SMTC: 4 spielt, 5 Pause, alles andere ist gestoppt."""
    try:
        value = int(status)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return STOPPED
    if value == 4:
        return PLAYING
    if value == 5:
        return PAUSED
    return STOPPED


def itunes_player_state(player_state: int) -> str:
    """iTunes-COM: 1 spielt, 2 Vorspulen, 3 Zurückspulen. Pause kennt das COM-Objekt nicht."""
    if player_state in (1, 2, 3):
        return PLAYING
    return STOPPED


def choose_session(rows: list[tuple[str, str]]) -> int | None:
    """Wählt die Apple-Sitzung, die gerade spielt, sonst die in Pause."""
    apple = [(index, state) for index, (aumid, state) in enumerate(rows) if is_apple_session(aumid)]
    if not apple:
        return None
    for wanted in ACTIVE:
        for index, state in apple:
            if state == wanted:
                return index
    return apple[0][0]


def timeline_seconds(
    start: object,
    end: object,
    position: object,
    last_updated: datetime | None,
    state: str,
    now: datetime,
) -> tuple[float, float]:
    """Position und Länge in Sekunden. Beim Abspielen die Zeit seit dem Stand dazurechnen."""
    start_s = _seconds(start)
    end_s = _seconds(end)
    position_s = _seconds(position)
    duration = end_s - start_s
    if duration > 0:
        relative = position_s - start_s
    else:
        duration = 0.0
        relative = position_s
    if state == PLAYING and isinstance(last_updated, datetime):
        delta = (_aware(now) - _aware(last_updated)).total_seconds()
        if 0 <= delta <= 120:
            relative += delta
    if duration > 0:
        relative = min(max(relative, 0.0), duration)
    else:
        relative = max(relative, 0.0)
    return round(relative, 1), round(duration, 1)


def prefer(primary: Snapshot | None, secondary: Snapshot | None) -> Snapshot:
    """Nimmt die laufende oder pausierte Quelle, sonst den ersten vorhandenen Stand."""
    for snap in (primary, secondary):
        if snap is not None and snap.state in ACTIVE:
            return snap
    for snap in (primary, secondary):
        if snap is not None and snap.state != OFF:
            return snap
    for snap in (primary, secondary):
        if snap is not None:
            return snap
    return Snapshot(OFF)


def _seconds(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, timedelta):
        return value.total_seconds()
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)
