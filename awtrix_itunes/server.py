"""HTTP-Antworten, die die Uhr erwartet: /now und /art/<id>.png."""

from __future__ import annotations

import hmac
import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ART_ID = re.compile(r"^[0-9a-f]{12}$")


class QuietServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def make_server(player, key: str, port: int, host: str = "0.0.0.0") -> QuietServer:
    handler = make_handler(player, key)
    return QuietServer((host, port), handler)


def make_handler(player, key: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if not _allowed(key, _provided_key(url.query)):
                self._send(403, b'{"error":"wrong key"}', "application/json", "no-store")
                return
            if url.path == "/now":
                body = json.dumps(player.current(), ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8", "no-store")
                return
            art_id = _art_id(url.path)
            if art_id is not None:
                image = player.artwork_for(art_id)
                if image is not None:
                    png, cacheable = image
                    cache = "max-age=86400" if cacheable else "no-store"
                    self._send(200, png, "image/png", cache)
                    return
            self._send(404, b'{"error":"not found"}', "application/json", "no-store")

        def _send(self, code: int, body: bytes, content_type: str, cache: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            return

    return Handler


def _art_id(path: str) -> str | None:
    if not path.startswith("/art/") or not path.endswith(".png"):
        return None
    art_id = path[5:-4]
    if ART_ID.fullmatch(art_id) is None:
        return None
    return art_id


def _provided_key(query: str) -> str:
    values = urllib.parse.parse_qs(query, keep_blank_values=True).get("k", [])
    return values[0] if values else ""


def _allowed(expected: str, provided: str) -> bool:
    if expected == "":
        return True
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))
