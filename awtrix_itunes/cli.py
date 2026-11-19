"""Kommandozeile des Windows-Helpers."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

from awtrix_itunes import __version__
from awtrix_itunes.artwork import Artwork
from awtrix_itunes.demo import DemoSource
from awtrix_itunes.install_task import install, uninstall
from awtrix_itunes.log import configure, log
from awtrix_itunes.player import Player
from awtrix_itunes.server import make_server

FORBIDDEN_KEY = set(" &\t\r\n?#")


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass
    args = parse_args(argv)
    if args.install:
        run_install(args)
        return
    if args.uninstall:
        run_uninstall()
        return
    port, key = resolve_bind(args)
    check_key(key)
    configure(log_path(args.config))
    source = build_source(args.demo)
    player = Player(source, Artwork())
    try:
        server = make_server(player, key, port)
    except OSError as exc:
        raise SystemExit(f"Port {port} ist belegt oder gesperrt: {exc}") from exc
    log.info("Musik-Helper %s auf Port %s%s", __version__, port, " (Schlüssel nötig)" if key else "")
    addresses = local_addresses()
    if addresses:
        log.info("Für die Uhr: %s", ", ".join(addresses))
    if key:
        log.info("Denselben Schlüssel in der Uhr bei „Schlüssel“ eintragen.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Beendet")
    finally:
        server.server_close()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Zeigt Apple Music, iTunes oder Spotify einer AWTRIX-Uhr im lokalen Netz."
    )
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--key", default=None, help="optional, derselbe Wert wie „Schlüssel“ auf der Uhr")
    parser.add_argument("--config", default="", help=argparse.SUPPRESS)
    parser.add_argument("--install", action="store_true", help="bei jeder Windows-Anmeldung starten")
    parser.add_argument("--uninstall", action="store_true", help="Autostart entfernen")
    parser.add_argument("--demo", action="store_true", help="festes Beispiel, ohne Player")
    return parser.parse_args(argv)


def resolve_bind(args: argparse.Namespace) -> tuple[int, str]:
    port = 8765
    key = ""
    if args.config:
        try:
            data = json.loads(Path(args.config).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"config.json lässt sich nicht lesen: {exc}") from exc
        port = int(data.get("port", port))
        key = str(data.get("key", ""))
    if args.port is not None:
        port = args.port
    if args.key is not None:
        key = args.key
    if not 1 <= port <= 65535:
        raise SystemExit("Der Port muss zwischen 1 und 65535 liegen.")
    return port, key


def check_key(key: str) -> None:
    if any(char in FORBIDDEN_KEY for char in key):
        raise SystemExit("Der Schlüssel darf kein Leerzeichen und keines von & ? # enthalten.")


def build_source(demo: bool):
    if demo:
        log.info("Demo: festes Beispiel, es wird kein Player gelesen.")
        return DemoSource()
    if sys.platform != "win32":
        raise SystemExit(
            "Dieser Helper liest Apple Music, iTunes und Spotify über die Windows-Mediensteuerung. "
            "Zum Ausprobieren ohne Windows: python itunes-helper.py --demo"
        )
    from awtrix_itunes.windows_media import WindowsMediaSource

    return WindowsMediaSource()


def run_install(args: argparse.Namespace) -> None:
    if sys.platform != "win32":
        raise SystemExit("--install gibt es nur unter Windows.")
    from awtrix_itunes.windows_smtc import ensure_winrt

    ensure_winrt()
    port, key = resolve_bind(args)
    check_key(key)
    base = windows_base_dir()
    dest = install(
        source_root=Path(__file__).resolve().parent.parent,
        port=port,
        key=key,
        executable=sys.executable,
        base_dir=base,
    )
    print(f"Eingerichtet. Läuft jetzt und bei jeder Anmeldung, Port {port}.")
    print(f"Ordner: {dest}")
    print(f"Protokoll: {dest / 'helper.log'}")
    print("Die Windows-Firewall fragt beim ersten Start. Zugriff im privaten Netz zulassen.")
    addresses = local_addresses()
    if addresses:
        print("Adresse für die Uhr: " + ", ".join(addresses))


def run_uninstall() -> None:
    if sys.platform != "win32":
        raise SystemExit("--uninstall gibt es nur unter Windows.")
    uninstall(base_dir=windows_base_dir())
    print("Entfernt.")


def windows_base_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise SystemExit("LOCALAPPDATA ist nicht gesetzt.")
    return Path(base)


def log_path(config: str) -> Path | None:
    if config:
        return Path(config).resolve().parent / "helper.log"
    try:
        interactive = sys.stderr is not None and sys.stderr.isatty()
    except Exception:
        interactive = False
    if interactive:
        return None
    return Path(__file__).resolve().parent.parent / "helper.log"


def local_addresses() -> list[str]:
    found: list[str] = []
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    for info in infos:
        found.append(info[4][0])
    return usable_ipv4(found)


def usable_ipv4(addresses: list[str]) -> list[str]:
    result: list[str] = []
    for address in addresses:
        if address.startswith("127.") or address == "0.0.0.0":
            continue
        if address not in result:
            result.append(address)
    return result
