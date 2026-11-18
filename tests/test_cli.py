"""Kommandozeile und die Uhr-Datei."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from awtrix_itunes.cli import check_key, local_addresses, main, parse_args, resolve_bind, usable_ipv4

ROOT = Path(__file__).resolve().parents[1]


def test_hilfe_ueber_das_startskript():
    result = subprocess.run(
        [sys.executable, str(ROOT / "itunes-helper.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--install" in result.stdout
    assert "--demo" in result.stdout


def test_linux_startet_den_echten_helper_nicht():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert "Windows" in str(exc.value)


def test_install_nur_unter_windows():
    with pytest.raises(SystemExit) as exc:
        main(["--install"])
    assert "--install" in str(exc.value)


def test_config_und_schluessel(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"port": 9000, "key": "abc"}), encoding="utf-8")
    args = parse_args(["--config", str(config), "--port", "9001"])
    assert resolve_bind(args) == (9001, "abc")
    with pytest.raises(SystemExit):
        check_key("ge heim")
    with pytest.raises(SystemExit):
        check_key("a&b")


def test_nur_brauchbare_ipv4():
    assert usable_ipv4(["127.0.0.1", "192.168.1.20", "192.168.1.20", "0.0.0.0"]) == ["192.168.1.20"]
    assert all(not item.startswith("127.") for item in local_addresses())


def test_uhr_skript_passt_zum_protokoll():
    text = (ROOT / "itunes.ax").read_text(encoding="utf-8")
    assert '"PC-Adresse"' in text
    assert 'options=ausblenden,anzeigen' in text
    assert 'store.get("paused") == "anzeigen"' in text
    assert 'http.get(self.base + "/now"' in text
    assert 'text(0, 6, "Adresse"' in text
    assert "Set Mac" not in text
