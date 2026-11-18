"""Zusammenbau von Mediensteuerung und iTunes-COM, ohne echte Windows-Aufrufe."""

from pathlib import Path

from awtrix_itunes.media import PAUSED, PLAYING, STOPPED, Snapshot
from awtrix_itunes.sessions import SmtcResult
from awtrix_itunes.windows_com import read_itunes_com, snapshot_from_app
from awtrix_itunes.windows_media import WindowsMediaSource
from awtrix_itunes.windows_smtc import ensure_winrt


def test_spielende_mediensteuerung_fragt_itunes_nicht():
    called = {"n": 0}

    def com():
        called["n"] += 1
        return Snapshot(PLAYING, "com")

    source = WindowsMediaSource(
        smtc=lambda: SmtcResult(Snapshot(PLAYING, "Song", "A", "", 1, 2), "Mediensteuerung: App (spielt)"),
        com=com,
    )
    assert source.read().title == "Song"
    assert called["n"] == 0


def test_pause_in_apple_music_bleibt_pause():
    source = WindowsMediaSource(
        smtc=lambda: SmtcResult(Snapshot(PAUSED, "Song"), "Pause"),
        com=lambda: Snapshot(PLAYING, "iTunes"),
    )
    assert source.read().title == "Song"
    assert source.read().state == PAUSED


def test_gestoppte_mediensteuerung_weicht_laufendem_itunes():
    source = WindowsMediaSource(
        smtc=lambda: SmtcResult(Snapshot(STOPPED), "steht"),
        com=lambda: Snapshot(PLAYING, "Aus iTunes", "Band", "Album", 3, 9, b"a"),
    )
    snap = source.read()
    assert snap.title == "Aus iTunes"
    assert snap.artwork == b"a"


def test_ohne_quelle_ist_aus():
    source = WindowsMediaSource(smtc=lambda: SmtcResult(None, "Keine Medien-Sitzung"), com=lambda: None)
    assert source.read().state == "off"


def test_fehler_in_der_mediensteuerung_nutzt_itunes():
    def boom():
        raise RuntimeError("weg")

    source = WindowsMediaSource(smtc=boom, com=lambda: Snapshot(PAUSED, "Pause"))
    assert source.read().state == PAUSED


def test_com_liest_titel_und_cover(tmp_path, monkeypatch):
    def fake_mkdtemp(prefix=""):
        folder = tmp_path / "cover"
        folder.mkdir()
        return str(folder)

    monkeypatch.setattr("awtrix_itunes.windows_com.tempfile.mkdtemp", fake_mkdtemp)

    class Item:
        def SaveArtworkToFile(self, path):
            Path(path).write_bytes(b"raw-cover")

    class Arts:
        Count = 1

        def Item(self, number):
            assert number == 1
            return Item()

    class Track:
        Name = "Song"
        Artist = "Band"
        Album = "Platte"
        Duration = 180
        Artwork = Arts()

    class App:
        PlayerState = 1
        PlayerPosition = 12.24
        CurrentTrack = Track()

    snap = snapshot_from_app(App())
    assert snap.state == PLAYING
    assert snap.title == "Song"
    assert snap.position == 12.2
    assert snap.duration == 180
    assert snap.artwork == b"raw-cover"


def test_com_bei_stop_liest_den_titel_nicht():
    class App:
        PlayerState = 0

        @property
        def CurrentTrack(self):
            raise AssertionError("bei Stop wird der Titel nicht gebraucht")

    assert snapshot_from_app(App()).state == STOPPED


def test_com_ohne_pywin32_ist_still():
    assert read_itunes_com() is None


def test_winrt_fehlt_auf_diesem_rechner():
    try:
        ensure_winrt()
    except SystemExit as exc:
        assert "requirements.txt" in str(exc)
    else:
        raise AssertionError("ohne die Windows-Pakete hätte der Start abbrechen müssen")
