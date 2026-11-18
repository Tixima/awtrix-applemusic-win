#!/usr/bin/env python3
"""Zeigt Apple Music oder iTunes auf einer AWTRIX-Uhr.

  python itunes-helper.py              in diesem Fenster (Strg-C beendet)
  python itunes-helper.py --install    bei jeder Windows-Anmeldung
  python itunes-helper.py --uninstall  Autostart entfernen
  python itunes-helper.py --demo       festes Beispiel, ohne Apple Music
  Optionen: --port 8765  --key GEHEIM (derselbe Wert wie „Schlüssel“ auf der Uhr)

Der Helper startet Apple Music und iTunes nicht und steuert die Wiedergabe nicht.
"""

from awtrix_itunes.cli import main

if __name__ == "__main__":
    main()
