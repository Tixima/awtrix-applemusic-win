"""Der Player fragt höchstens einmal pro Sekunde und merkt sich Cover."""

from awtrix_itunes.media import PLAYING, STOPPED, Snapshot, art_key
from awtrix_itunes.player import Player


class Source:
    def __init__(self, snap):
        self.snap = snap
        self.calls = 0

    def read(self):
        self.calls += 1
        return self.snap


class Arts:
    def __init__(self, png=b"png", cacheable=True):
        self.png = png
        self.cacheable = cacheable
        self.calls = 0

    def render(self, snap):
        self.calls += 1
        return self.png, self.cacheable


def _player(source, arts, clock):
    return Player(source, arts, interval=1, now=lambda: clock["t"])


def test_cache_und_cover():
    clock = {"t": 10.0}
    source = Source(Snapshot(PLAYING, "Titel", "Band", "Album", 1.0, 20.0, b"raw"))
    arts = Arts()
    player = _player(source, arts, clock)
    body = player.current()
    assert body["s"] == PLAYING
    assert body["t"] == "Titel"
    assert body["art"].endswith(".png")
    assert source.calls == 1
    player.current()
    assert source.calls == 1
    clock["t"] = 11.1
    player.current()
    assert source.calls == 2

    key = art_key("Band", "Album", "Titel")
    png, cacheable = player.artwork_for(key)
    assert png == b"png" and cacheable
    assert arts.calls == 1
    player.artwork_for(key)
    assert arts.calls == 1
    assert player.artwork_for("0123456789ab") is None


def test_note_wird_erneut_versucht():
    clock = {"t": 0.0}
    source = Source(Snapshot(PLAYING, "Titel", "Band", "Album", 0, 10))
    arts = Arts(png=b"note", cacheable=False)
    player = _player(source, arts, clock)
    player.current()
    key = art_key("Band", "Album", "Titel")
    assert player.artwork_for(key) == (b"note", False)
    clock["t"] = 29
    assert player.artwork_for(key) == (b"note", False)
    assert arts.calls == 1
    clock["t"] = 31
    assert player.artwork_for(key)[0] == b"note"
    assert arts.calls == 2


def test_gestoppt_hat_kein_cover_und_fehler_wird_aus():
    clock = {"t": 0.0}
    source = Source(Snapshot(STOPPED, "Titel"))
    player = _player(source, Arts(), clock)
    assert player.current() == {"s": "stopped"}

    class Boom:
        def read(self):
            raise RuntimeError("weg")

    assert Player(Boom(), Arts(), now=lambda: 1).current() == {"s": "off"}
