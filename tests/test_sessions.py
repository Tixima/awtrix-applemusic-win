"""Sitzungen der Windows-Mediensteuerung, mit nachgebauten Objekten."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from awtrix_itunes.media import PLAYING
from awtrix_itunes.sessions import collect_snapshot


class Session:
    def __init__(self, aumid, status, props, timeline):
        self.source_app_user_model_id = aumid
        self._status = status
        self._props = props
        self._timeline = timeline

    def get_playback_info(self):
        return SimpleNamespace(playback_status=self._status)

    def get_timeline_properties(self):
        return self._timeline

    async def try_get_media_properties_async(self):
        return self._props


def _timeline(position=10):
    return SimpleNamespace(
        start_time=timedelta(0),
        end_time=timedelta(seconds=100),
        position=timedelta(seconds=position),
        last_updated_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_apple_music_gewinnt_gegen_spotify_und_liest_das_cover():
    props = SimpleNamespace(
        title="Song",
        artist="",
        album_title="Ava",
        album_artist="Famy - Ava",
        thumbnail="ref",
    )
    apple = Session("AppleInc.AppleMusicWin_nzyj5cx40ttqa!App", 4, props, _timeline())
    spotify = Session("Spotify.exe", 4, props, _timeline())
    seen = []

    async def thumb(ref):
        seen.append(ref)
        return b"jpeg"

    now = datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc)
    result = asyncio.run(collect_snapshot([spotify, apple], thumb, now))
    assert result.snapshot is not None
    assert result.snapshot.state == PLAYING
    assert result.snapshot.artist == "Famy"
    assert result.snapshot.album == "Ava"
    assert result.snapshot.position == 12.0
    assert result.snapshot.artwork == b"jpeg"
    assert seen == ["ref"]
    assert "AppleInc.AppleMusicWin_nzyj5cx40ttqa!App" in result.detail
    assert "spielt" in result.detail


def test_fremde_sitzung_wird_benannt():
    other = Session("Spotify.exe", 4, None, _timeline())

    async def thumb(ref):
        raise AssertionError(ref)

    result = asyncio.run(collect_snapshot([other], thumb, datetime(2026, 1, 1, tzinfo=timezone.utc)))
    assert result.snapshot is None
    assert "Spotify.exe" in result.detail


def test_pause_rechnet_die_zeit_nicht_weiter():
    props = SimpleNamespace(title="Song", artist="Band", album_title="Al", album_artist="", thumbnail=None)
    session = Session("AppleMusic.exe", 5, props, _timeline(10))

    async def thumb(ref):
        raise AssertionError(ref)

    now = datetime(2026, 1, 1, 0, 0, 8, tzinfo=timezone.utc)
    result = asyncio.run(collect_snapshot([session], thumb, now))
    assert result.snapshot is not None
    assert result.snapshot.position == 10.0
    assert result.snapshot.artwork is None
    assert "Pause" in result.detail


def test_keine_sitzung():
    async def thumb(ref):
        return b""

    result = asyncio.run(collect_snapshot([], thumb, datetime(2026, 1, 1, tzinfo=timezone.utc)))
    assert result.snapshot is None
    assert result.detail == "Keine Medien-Sitzung"
