#!/usr/bin/env python3
"""Mac helper for the AWTRIX "iTunes Now Playing" script (github.com/mojeska/awtrix-itunes).

Serves what the Music app (iTunes on older Macs) is playing, plus a 16x16 picture of the album
artwork, on your local network, so the clock can show it. Standard library only.

  python3 itunes-helper.py                   run in this window (Ctrl-C stops it)
  python3 itunes-helper.py --install         run at every login (LaunchAgent)
  python3 itunes-helper.py --uninstall       stop it and remove the LaunchAgent
  options: --port 8765  --key SECRET (the clock's "Helper key" setting must match)

The first time, macOS asks whether the helper may control Music: allow it. It never starts
Music by itself, and it only answers questions; it changes nothing.
"""
import argparse
import hashlib
import json
import os
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.1"
LABEL = "io.github.mojeska.awtrix-itunes"
OLD_LABELS = ["de.awtrix.itunes-helper"]   # 1.0 before it was published
HOME_DIR = os.path.expanduser("~/Library/Application Support/AWTRIX iTunes Helper")
PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
SEP = "\x1f"
TMP = tempfile.mkdtemp(prefix="itunes-helper-")

QUERY = """
if application "Music" is not running then return "off"
tell application "Music"
  set s to player state as text
  if s is "stopped" then return s
  set t to current track
  return s & "{S}" & (name of t) & "{S}" & (artist of t) & "{S}" & (album of t) & "{S}" & (player position as text) & "{S}" & (duration of t as text) & "{S}" & (count of artworks of t)
end tell
""".replace("{S}", SEP)

ART = """
tell application "Music" to set d to raw data of artwork 1 of current track
set f to open for access POSIX file "{out}" with write permission
set eof f to 0
write d to f
close access f
"""


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.rstrip("\n")


def num(s):
    try:
        return float(s.replace(",", "."))   # AppleScript uses the locale's decimal mark
    except ValueError:
        return 0.0


class Player:
    """Asks Music at most once a second, whatever the number of clocks asking."""

    def __init__(self):
        self.lock = threading.Lock()
        self.at = 0
        self.now = {"s": "off"}
        self.art_src = {}     # art key -> (artist, album, has artwork)
        self.art_png = {}     # art key -> PNG bytes

    def current(self):
        with self.lock:
            if time.time() - self.at >= 1:
                self.now = self.read()
                self.at = time.time()
            return self.now

    def read(self):
        try:
            f = osa(QUERY).split(SEP)
        except Exception as e:
            log("Music query failed:", e)
            return {"s": "off"}
        if len(f) < 7:
            return {"s": f[0]}
        title, artist, album = f[1], f[2], f[3]
        key = hashlib.sha1(f"{artist}\n{album}\n{title if not album else ''}".encode()).hexdigest()[:12]
        self.art_src[key] = (artist, album, int(num(f[6])) > 0)
        return {"s": f[0], "t": title, "a": artist, "al": album,
                "p": round(num(f[4]), 1), "d": round(num(f[5]), 1), "art": f"/art/{key}.png"}

    def artwork(self, key):
        if key in self.art_png:
            return self.art_png[key]
        src = self.art_src.get(key)
        if src is None:
            return None
        artist, album, has_art = src
        png = None
        if has_art:
            try:
                raw = os.path.join(TMP, "art.bin")
                osa(ART.replace("{out}", raw))
                png = to_png16(raw)
            except Exception as e:
                log("artwork from Music failed:", e)
        if png is None and (artist or album):
            try:
                png = art_from_itunes(artist, album)
            except Exception as e:
                log("artwork lookup failed:", e)
        if png is None:
            png = note_png()
        self.art_png[key] = png
        return png


def to_png16(src):
    dst = os.path.join(TMP, "art16.png")
    subprocess.run(["sips", "-s", "format", "png", "-z", "16", "16", src, "--out", dst],
                   capture_output=True, check=True, timeout=15)
    with open(dst, "rb") as fh:
        return fh.read()


def art_from_itunes(artist, album):
    """Streamed songs often keep their artwork to themselves; ask Apple's iTunes Search instead."""
    q = urllib.parse.urlencode({"term": f"{artist} {album}", "entity": "album", "limit": 1})
    with urllib.request.urlopen(f"https://itunes.apple.com/search?{q}", timeout=10) as r:
        res = json.load(r).get("results", [])
    if not res or not res[0].get("artworkUrl100"):
        return None
    jpg = os.path.join(TMP, "art.jpg")
    urllib.request.urlretrieve(res[0]["artworkUrl100"], jpg)
    return to_png16(jpg)


_note = None


def note_png():
    """No artwork anywhere: a white note on grey, drawn as a BMP and converted by sips."""
    global _note
    if _note:
        return _note
    rows = ["................", "................", ".......#######..", ".......#######..",
            ".......#.....#..", ".......#.....#..", ".......#.....#..", ".......#.....#..",
            ".......#.....#..", "....####..####..", "...#####.#####..", "...#####.#####..",
            "....###...###...", "................", "................", "................"]
    px = b"".join(b"\xff\xff\xff" if c == "#" else b"\x30\x30\x30"
                  for row in reversed(rows) for c in row)      # BMP rows go bottom-up
    bmp = os.path.join(TMP, "note.bmp")
    with open(bmp, "wb") as fh:
        fh.write(struct.pack("<2sIHHI", b"BM", 54 + len(px), 0, 0, 54))
        fh.write(struct.pack("<IiiHHIIiiII", 40, 16, 16, 1, 24, 0, len(px), 2835, 2835, 0, 0))
        fh.write(px)
    _note = to_png16(bmp)
    return _note


def make_handler(player, key):
    class Handler(BaseHTTPRequestHandler):
        def send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store" if ctype.startswith("application") else "max-age=86400")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(url.query)
            if key and q.get("k", [""])[0] != key:
                return self.send(403, b'{"error":"wrong key"}', "application/json")
            if url.path == "/now":
                body = json.dumps(player.current(), ensure_ascii=False).encode()
                return self.send(200, body, "application/json; charset=utf-8")
            if url.path.startswith("/art/") and url.path.endswith(".png"):
                png = player.artwork(url.path[5:-4])
                if png:
                    return self.send(200, png, "image/png")
            self.send(404, b'{"error":"not found"}', "application/json")

        def log_message(self, *a):
            pass

    return Handler


def install(args):
    os.makedirs(HOME_DIR, exist_ok=True)
    target = os.path.join(HOME_DIR, "itunes-helper.py")
    if os.path.abspath(__file__) != target:
        shutil.copy2(__file__, target)
    prog = [sys.executable, target, "--port", str(args.port)] + (["--key", args.key] if args.key else [])
    os.makedirs(os.path.dirname(PLIST), exist_ok=True)
    for old in [LABEL] + OLD_LABELS:
        old_plist = os.path.expanduser(f"~/Library/LaunchAgents/{old}.plist")
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", old_plist], capture_output=True)
        if old != LABEL and os.path.exists(old_plist):
            os.remove(old_plist)
    with open(PLIST, "wb") as fh:
        plistlib.dump({"Label": LABEL, "ProgramArguments": prog, "RunAtLoad": True, "KeepAlive": True,
                       "StandardOutPath": os.path.join(HOME_DIR, "helper.log"),
                       "StandardErrorPath": os.path.join(HOME_DIR, "helper.log")}, fh)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", PLIST], check=True)
    print(f"Installed. It runs now and at every login, on port {args.port}.")
    print(f"Log: {os.path.join(HOME_DIR, 'helper.log')}")
    print("If macOS asks whether it may control Music, allow it.")


def uninstall():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", PLIST], capture_output=True)
    for p in (PLIST, os.path.join(HOME_DIR, "itunes-helper.py")):
        if os.path.exists(p):
            os.remove(p)
    print("Removed.")


def main():
    ap = argparse.ArgumentParser(description="Serves Music's current song to an AWTRIX clock.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--key", default="", help="optional; the clock's Helper key setting must match")
    ap.add_argument("--install", action="store_true", help="run at every login")
    ap.add_argument("--uninstall", action="store_true", help="stop and remove the login item")
    args = ap.parse_args()
    if args.install:
        return install(args)
    if args.uninstall:
        return uninstall()
    player = Player()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(player, args.key))
    log(f"iTunes helper {VERSION} on port {args.port}" + (" (key required)" if args.key else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
