#!/usr/bin/env python3
"""Zeigt Apple Music, iTunes oder Spotify auf einer AWTRIX-Uhr.

  python itunes-helper.py              in diesem Fenster (Strg-C beendet)
  python itunes-helper.py --install    bei jeder Windows-Anmeldung
  python itunes-helper.py --uninstall  Autostart entfernen
  python itunes-helper.py --demo       festes Beispiel, ohne Player
  Optionen: --port 8765  --key GEHEIM (derselbe Wert wie „Schlüssel“ auf der Uhr)

Der Helper startet die Player nicht und steuert die Wiedergabe nicht.
"""

from awtrix_itunes.cli import main

if __name__ == "__main__":
    main()
