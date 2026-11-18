"""Wählt aus den Medien-Sitzungen die von Apple Music oder iTunes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awtrix_itunes.media import (
    STATE_WORD,
    Snapshot,
    choose_session,
    clean_meta,
    state_from_status,
    timeline_seconds,
)


@dataclass(frozen=True)
class SmtcResult:
    snapshot: Snapshot | None
    detail: str


async def collect_snapshot(sessions, read_thumb, now: datetime) -> SmtcResult:
    """Liest die passenden Sitzungen. `read_thumb` holt die Cover-Bytes."""
    readable: list[tuple[object, str, str]] = []
    for session in sessions:
        try:
            aumid = str(session.source_app_user_model_id or "")
            status = session.get_playback_info().playback_status
        except Exception:
            continue
        readable.append((session, aumid, state_from_status(status)))
    if not readable:
        return SmtcResult(None, "Keine Medien-Sitzung")

    rows = [(aumid, state) for _, aumid, state in readable]
    index = choose_session(rows)
    if index is None:
        names = ", ".join(aumid for _, aumid, _ in readable) or "keine"
        return SmtcResult(None, f"Keine Apple-Music-Sitzung. Sichtbar: {names}")

    session, aumid, state = readable[index]
    title, artist, album, artwork = await _metadata(session, read_thumb)
    position, duration = _timeline(session, state, now)
    detail = f"Mediensteuerung: {aumid} ({STATE_WORD.get(state, state)})"
    return SmtcResult(Snapshot(state, title, artist, album, position, duration, artwork), detail)


async def _metadata(session, read_thumb) -> tuple[str, str, str, bytes | None]:
    try:
        props = await session.try_get_media_properties_async()
    except Exception:
        return "", "", "", None
    if props is None:
        return "", "", "", None
    title, artist, album = clean_meta(
        getattr(props, "title", ""),
        getattr(props, "artist", ""),
        getattr(props, "album_title", ""),
        getattr(props, "album_artist", ""),
    )
    artwork = None
    thumbnail = getattr(props, "thumbnail", None)
    if thumbnail is not None:
        try:
            artwork = await read_thumb(thumbnail)
        except Exception:
            artwork = None
    return title, artist, album, artwork or None


def _timeline(session, state: str, now: datetime) -> tuple[float, float]:
    try:
        timeline = session.get_timeline_properties()
    except Exception:
        return 0.0, 0.0
    return timeline_seconds(
        getattr(timeline, "start_time", None),
        getattr(timeline, "end_time", None),
        getattr(timeline, "position", None),
        getattr(timeline, "last_updated_time", None),
        state,
        now,
    )
