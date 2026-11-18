"""Liest ein laufendes klassisches iTunes über COM. Startet iTunes nicht."""

from __future__ import annotations

import os
import tempfile

from awtrix_itunes.log import log, once
from awtrix_itunes.media import PLAYING, STOPPED, Snapshot, itunes_player_state, text


def read_itunes_com(connect=None) -> Snapshot | None:
    """Verbindet sich nur, wenn iTunes schon läuft."""
    if connect is not None:
        app = connect()
        if app is None:
            return None
        return snapshot_from_app(app)

    try:
        import pythoncom
        import win32com.client
    except ImportError:
        once("pywin32 fehlt, klassisches iTunes über COM wird übersprungen.")
        return None

    pythoncom.CoInitialize()
    try:
        try:
            app = win32com.client.GetActiveObject("iTunes.Application")
        except Exception:
            return None
        return snapshot_from_app(app)
    except Exception:
        log.info("iTunes über COM nicht lesbar")
        return None
    finally:
        pythoncom.CoUninitialize()


def snapshot_from_app(app) -> Snapshot:
    state = itunes_player_state(int(app.PlayerState))
    if state != PLAYING:
        return Snapshot(STOPPED)
    track = app.CurrentTrack
    if track is None:
        return Snapshot(STOPPED)
    title = _field(track, "Name")
    artist = _field(track, "Artist")
    album = _field(track, "Album")
    duration = _number(getattr(track, "Duration", 0))
    position = _number(getattr(app, "PlayerPosition", 0))
    if duration > 0:
        position = min(max(position, 0.0), duration)
    artwork = _artwork(track)
    return Snapshot(PLAYING, title, artist, album, round(position, 1), round(duration, 1), artwork)


def _artwork(track) -> bytes | None:
    try:
        artworks = track.Artwork
        count = artworks.Count
        if callable(count):
            count = count()
        if int(count) < 1:
            return None
        folder = tempfile.mkdtemp(prefix="awtrix-itunes-")
        path = os.path.join(folder, "art.bin")
        try:
            artworks.Item(1).SaveArtworkToFile(path)
            with open(path, "rb") as handle:
                data = handle.read()
        finally:
            try:
                os.remove(path)
                os.rmdir(folder)
            except OSError:
                pass
        return data or None
    except Exception:
        return None


def _field(track, name: str) -> str:
    try:
        return text(getattr(track, name))
    except Exception:
        return ""


def _number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
