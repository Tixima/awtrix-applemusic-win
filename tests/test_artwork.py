"""Cover auf 16×16, Suche und die Ersatz-Note."""

import io
import json

from PIL import Image

from awtrix_itunes.artwork import Artwork, fetch_itunes_artwork, note_png, to_png16
from awtrix_itunes.media import PLAYING, Snapshot


class Body:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _png(color, size=(32, 18)):
    image = Image.new("RGB", size, color)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_verkleinert_auf_16():
    png = to_png16(_png((200, 10, 10)))
    image = Image.open(io.BytesIO(png))
    assert image.size == (16, 16)
    assert image.format == "PNG"
    red = image.getpixel((8, 8))
    assert red[0] > 150 and red[1] < 40


def test_note_hat_die_bekannten_pixel():
    image = Image.open(io.BytesIO(note_png()))
    assert image.size == (16, 16)
    assert image.getpixel((7, 2)) == (255, 255, 255)
    assert image.getpixel((0, 0)) == (0x30, 0x30, 0x30)


def test_zu_grosses_cover_wird_abgelehnt():
    try:
        to_png16(b"x" * (8_000_001))
    except ValueError:
        return
    raise AssertionError("großes Cover hätte scheitern müssen")


def test_suche_liefert_das_bild_und_faellt_auf_die_note_zurueck():
    cover = _png((10, 180, 20), (40, 40))
    seen = []

    def opener(request, timeout=10):
        seen.append(request.full_url)
        if "search" in request.full_url:
            payload = {"results": [{"artworkUrl100": "https://example.test/cover.jpg"}]}
            return Body(json.dumps(payload).encode())
        return Body(cover)

    raw = fetch_itunes_artwork("Band", "Album", opener)
    assert raw == cover
    assert "Band" in seen[0]
    assert seen[1] == "https://example.test/cover.jpg"

    rendered, cacheable = Artwork(fetch=lambda artist, album: cover).render(
        Snapshot(PLAYING, "T", "Band", "Album")
    )
    assert cacheable
    assert Image.open(io.BytesIO(rendered)).size == (16, 16)

    note, cacheable = Artwork(fetch=lambda artist, album: None).render(Snapshot(PLAYING, "T", "Band", "Album"))
    assert cacheable is False
    assert note == note_png()


def test_kaputtes_cover_wird_zur_note():
    png, cacheable = Artwork(fetch=lambda artist, album: None).render(
        Snapshot(PLAYING, "T", "", "", artwork=b"kein bild")
    )
    assert cacheable is False
    assert png == note_png()
