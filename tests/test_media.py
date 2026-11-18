"""Ablauf, Sitzungswahl und Zeiten, ohne Windows."""

from datetime import datetime, timedelta, timezone

from awtrix_itunes.media import (
    OFF,
    PAUSED,
    PLAYING,
    STOPPED,
    Snapshot,
    art_key,
    artist_from_album_artist,
    choose_session,
    clean_meta,
    is_apple_session,
    itunes_player_state,
    prefer,
    state_from_status,
    timeline_seconds,
)


def test_art_key_folgt_dem_album():
    mit_album = art_key("A", "B", "C")
    gleicher_titel_egal = art_key("A", "B", "D")
    ohne_album = art_key("A", "", "C")
    anderer_titel = art_key("A", "", "D")
    assert mit_album == gleicher_titel_egal
    assert ohne_album != anderer_titel
    assert len(mit_album) == 12


def test_interpret_aus_albumartist():
    assert clean_meta("Song", "Band", "Album") == ("Song", "Band", "Album")
    assert clean_meta("Song", "", "Ava", "Famy - Ava") == ("Song", "Famy", "Ava")
    assert clean_meta("Song", "", "", "Nur Band") == ("Song", "Nur Band", "")
    assert clean_meta("Song", "", "Anderes", "Famy - Ava")[1] == "Famy - Ava"
    assert artist_from_album_artist("A - B - C", "C") == "A - B"
    assert clean_meta(
        "Upside Down", "", "", "Black Gryph0n & Baasik - Upside Down - Single"
    ) == ("Upside Down", "Black Gryph0n & Baasik", "")
    assert clean_meta("  T ", None, " Al ") == ("T", "", "Al")


def test_apple_sitzungen():
    assert is_apple_session("AppleInc.AppleMusicWin_nzyj5cx40ttqa!App")
    assert is_apple_session("AppleMusic.exe")
    assert is_apple_session(r"C:\Program Files\AppleMusic.exe")
    assert is_apple_session("iTunes.exe")
    assert is_apple_session("!iTunes")
    assert not is_apple_session("Spotify.exe")
    assert not is_apple_session("AppleInc.AppleTVWin_nzyj5cx40ttqa!App")
    assert not is_apple_session("Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic")
    assert not is_apple_session("")


def test_status_und_itunes_com():
    assert state_from_status(4) == PLAYING
    assert state_from_status(5) == PAUSED
    assert state_from_status(0) == STOPPED
    assert state_from_status("nein") == STOPPED
    assert itunes_player_state(1) == PLAYING
    assert itunes_player_state(2) == PLAYING
    assert itunes_player_state(0) == STOPPED


def test_waehlt_spielende_apple_sitzung():
    rows = [("Spotify.exe", PLAYING), ("AppleMusic.exe", PAUSED), ("iTunes.exe", PLAYING)]
    assert choose_session(rows) == 2
    assert choose_session([("Spotify.exe", PLAYING)]) is None
    assert choose_session([("AppleMusic.exe", STOPPED)]) == 0


def test_zeit_nur_beim_spielen():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    updated = start
    now = start + timedelta(seconds=2.5)
    playing, duration = timeline_seconds(timedelta(0), timedelta(seconds=100), timedelta(seconds=10), updated, PLAYING, now)
    paused, _ = timeline_seconds(timedelta(0), timedelta(seconds=100), timedelta(seconds=10), updated, PAUSED, now)
    assert playing == 12.5
    assert duration == 100.0
    assert paused == 10.0


def test_zeit_ignoriert_alte_oder_zukuenftige_staende():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    stale = timeline_seconds(
        timedelta(0), timedelta(seconds=50), timedelta(seconds=10),
        start, PLAYING, start + timedelta(seconds=121),
    )
    future = timeline_seconds(
        timedelta(0), timedelta(seconds=50), timedelta(seconds=10),
        start + timedelta(seconds=5), PLAYING, start,
    )
    assert stale == (10.0, 50.0)
    assert future == (10.0, 50.0)


def test_position_bleibt_im_titel():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    position, duration = timeline_seconds(
        timedelta(seconds=5), timedelta(seconds=15), timedelta(seconds=14),
        start, PLAYING, start + timedelta(seconds=10),
    )
    assert duration == 10.0
    assert position == 10.0


def test_prefer_nimmt_die_laufende_quelle():
    stopped = Snapshot(STOPPED)
    playing = Snapshot(PLAYING, "Song")
    assert prefer(stopped, playing).title == "Song"
    assert prefer(playing, Snapshot(PLAYING, "anders")).title == "Song"
    assert prefer(stopped, None).state == STOPPED
    assert prefer(None, None).state == OFF
    assert prefer(Snapshot(PAUSED, "Pause"), playing).title == "Pause"
