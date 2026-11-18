"""Aufgabenplanung, ohne Windows aufzurufen."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from awtrix_itunes.install_task import (
    TASK_NAME,
    build_task_xml,
    install,
    program_arguments,
    uninstall,
    windowless_python,
)

ROOT = Path(__file__).resolve().parents[1]


def test_xml_ist_gueltig_und_enthaelt_keinen_schluessel():
    xml = build_task_xml(
        executable=r"C:\Python\pythonw.exe",
        script=r"C:\A&B\itunes-helper.py",
        config=r"C:\A&B\config.json",
        workdir=r"C:\A&B",
    )
    ET.fromstring(xml.split("?>", 1)[1])
    assert "<LogonTrigger>" in xml
    assert "InteractiveToken" in xml
    assert "<RestartOnFailure>" in xml
    assert "PT0S" in xml
    assert "PT1M" in xml
    assert "pythonw.exe" in xml
    assert "C:\\A&amp;B\\itunes-helper.py" in xml
    assert "geheim" not in xml
    assert program_arguments(r"C:\Windows\pyw.exe", r"C:\App\itunes-helper.py", r"C:\App\config.json").startswith("-3 ")


def test_windowless_python_bevorzugt_pythonw(tmp_path):
    py = tmp_path / "python.exe"
    pyw = tmp_path / "pythonw.exe"
    py.write_text("", encoding="utf-8")
    pyw.write_text("", encoding="utf-8")
    assert windowless_python(str(py)) == str(pyw)
    only = tmp_path / "only" / "python.exe"
    only.parent.mkdir()
    only.write_text("", encoding="utf-8")
    assert windowless_python(str(only)) == str(only)


def test_install_kopiert_und_legt_den_schluessel_nur_in_die_config(tmp_path):
    exe = tmp_path / "python.exe"
    pyw = tmp_path / "pythonw.exe"
    exe.write_bytes(b"")
    pyw.write_bytes(b"")
    calls = []

    def runner(cmd, check=False):
        calls.append(list(cmd))
        return None

    dest = install(
        source_root=ROOT,
        port=9123,
        key="a&b",
        executable=str(exe),
        base_dir=tmp_path / "local",
        runner=runner,
    )
    assert (dest / "itunes-helper.py").is_file()
    assert (dest / "awtrix_itunes" / "cli.py").is_file()
    config = json.loads((dest / "config.json").read_text(encoding="utf-8"))
    assert config == {"port": 9123, "key": "a&b"}
    xml = (dest / "task.xml").read_text(encoding="utf-16")
    assert "a&b" not in xml
    assert "9123" not in xml
    assert str(dest / "config.json") in xml
    assert calls[0][:3] == ["schtasks", "/End", "/TN"]
    assert calls[0][3] == TASK_NAME
    assert calls[2][1] == "/Create"
    assert calls[3] == ["schtasks", "/Run", "/TN", TASK_NAME]

    uninstall(base_dir=tmp_path / "local", runner=runner)
    assert not dest.exists()
