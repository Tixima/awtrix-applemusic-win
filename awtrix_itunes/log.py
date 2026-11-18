"""Protokoll für Konsole und Datei."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

log = logging.getLogger("awtrix.itunes")

_seen: set[str] = set()


def once(message: str) -> None:
    """Gibt eine Meldung nur beim ersten Mal aus."""
    if message in _seen:
        return
    if len(_seen) > 50:
        _seen.clear()
    _seen.add(message)
    log.info(message)


def configure(path: Path | None) -> None:
    """Richtet Konsole und, wenn gewünscht, eine kleine Protokolldatei ein."""
    log.setLevel(logging.INFO)
    log.propagate = False
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S")
    stream = _stream_handler()
    if stream is not None:
        stream.setFormatter(formatter)
        log.addHandler(stream)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(path, maxBytes=512_000, backupCount=1, encoding="utf-8")
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)


def _stream_handler() -> logging.Handler | None:
    import sys

    stream = sys.stderr
    if stream is None:
        return None
    try:
        stream.reconfigure(errors="replace")
    except Exception:
        pass
    return logging.StreamHandler(stream)
