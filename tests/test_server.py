"""HTTP, so wie die Uhr es aufruft."""

import io
import json
import threading
import urllib.error
import urllib.request

from PIL import Image

from awtrix_itunes.artwork import Artwork
from awtrix_itunes.demo import DemoSource
from awtrix_itunes.media import art_key
from awtrix_itunes.player import Player
from awtrix_itunes.server import make_server


class Stub:
    def current(self):
        return {"s": "playing", "t": "Geheim", "a": "A", "al": "Al", "p": 1, "d": 2, "art": "/art/0123456789ab.png"}

    def artwork_for(self, key):
        if key == "0123456789ab":
            return b"\x89PNG\r\n", True
        return None


def _serve(player, key=""):
    server = make_server(player, key, 0, "127.0.0.1")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _get(server, path):
    port = server.server_address[1]
    return urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5)


def test_schluessel_und_pfade():
    server = _serve(Stub(), "geheim")
    try:
        try:
            _get(server, "/now")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
            assert b"Geheim" not in exc.read()
        else:
            raise AssertionError("ohne Schlüssel hätte 403 kommen müssen")

        with _get(server, "/now?k=geheim") as response:
            body = json.load(response)
        assert body["t"] == "Geheim"
        assert response.headers["Cache-Control"] == "no-store"

        with _get(server, "/art/0123456789ab.png?k=geheim") as response:
            assert response.read().startswith(b"\x89PNG")
            assert response.headers["Cache-Control"] == "max-age=86400"

        try:
            _get(server, "/art/../../etc.png?k=geheim")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("fremder Pfad hätte 404 sein müssen")
    finally:
        server.shutdown()
        server.server_close()


def test_demo_spricht_das_uhr_protokoll():
    player = Player(DemoSource(), Artwork())
    server = _serve(player)
    try:
        with _get(server, "/now") as response:
            body = json.load(response)
        assert body["s"] == "playing"
        assert body["t"] == "Probelauf"
        assert body["a"] == "AWTRIX"
        assert body["al"] == "Windows"
        assert 0 <= body["p"] <= body["d"] == 200
        assert body["art"] == "/art/" + art_key("AWTRIX", "Windows", "Probelauf") + ".png"
        with _get(server, body["art"]) as response:
            image = Image.open(io.BytesIO(response.read()))
        assert image.size == (16, 16)
        assert image.format == "PNG"
    finally:
        server.shutdown()
        server.server_close()
