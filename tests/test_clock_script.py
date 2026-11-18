"""Das Uhr-Skript bleibt ruhig: kurzer Text steht, und höchstens eine Zeile wandert."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "itunes.ax"


def test_lauftext_steht_wenn_er_passt_und_ignoriert_die_uhr_vorgabe():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"whenFits": "static"' in source
    assert '"mode": "static"' in source
    assert '"mode": "bounce"' in source
    assert 'self.move == "einmal"' in source
    assert 'self.move == "dauernd"' in source
    assert 'self.move == "hinher"' in source
    assert "options=stehen,einmal,hinher,dauernd" in source
    assert "default=einmal" in source
    assert "options=ruhig,beide,gross,breit" in source
    assert "default=ruhig" in source
    assert "@version 2.0" in source
    assert "scroll_text" in source
