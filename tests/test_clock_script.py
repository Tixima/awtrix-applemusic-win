"""Vorgaben wie im Original. Umbruch, Überblenden und die übrigen Schalter bleiben."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "itunes.ax"


def test_original_und_die_zusaetzlichen_optionen():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '{"repeat": 1, "speed": sp}' in source
    assert '{"speed": sp}' in source
    assert "default=90" in source
    assert "default=original" in source
    assert 'bool   "Titel auf zwei Zeilen" default=false' in source
    assert 'bool   "Überblenden"       default=true' in source
    assert 'bool   "Pegel"             default=false' in source
    assert "options=original,ruhig,beide,gross,breit" in source
    assert "options=original,stehen,einmal,hinher,dauernd" in source
    assert "self.wrap" in source
    assert "def fade_level()" in source
    assert "def fit_lines(" in source
    assert "def syllables(" in source
    assert "def segments(" in source
    assert 'ch == " "' in source
    assert "title[i] == 32" not in source
    assert "def paint_eq(" in source
    assert "def draw_standby(" in source
    assert "def paint_note(" in source
    assert "self.link" in source
    assert '"Adresse"' in source
    assert '"kein PC"' in source
    assert "rect_fill(0, 10, 8, 6" not in source
    assert "@version 2.4" in source
