"""Richtet den Helper als Aufgabe bei der Windows-Anmeldung ein."""

from __future__ import annotations

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

FOLDER_NAME = "AWTRIX Apple Music Helper"
TASK_NAME = "AWTRIX Apple Music Helper"
TASK_XMLNS = "http://schemas.microsoft.com/windows/2004/02/mit/task"


def windowless_python(executable: str) -> str:
    """Nimmt pythonw oder pyw, damit bei der Anmeldung kein Konsolfenster aufgeht."""
    path = Path(executable)
    name = _exe_name(executable)
    if name in {"python.exe", "python3.exe"} or (name.startswith("python3.") and name.endswith(".exe")):
        candidate = path.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    if name == "py.exe":
        candidate = path.with_name("pyw.exe")
        if candidate.exists():
            return str(candidate)
    return str(path)


def program_arguments(executable: str, script: str, config: str) -> str:
    arguments = f"{_quote(script)} --config {_quote(config)}"
    if _exe_name(executable) == "pyw.exe":
        return f"-3 {arguments}"
    return arguments


def _exe_name(executable: str) -> str:
    """Letzter Namensbestandteil, auch wenn der Pfad auf einem anderen System gebaut wurde."""
    return executable.replace("\\", "/").rsplit("/", 1)[-1].lower()


def build_task_xml(*, executable: str, script: str, config: str, workdir: str) -> str:
    """Aufgabenplanung: bei Anmeldung starten, im Benutzerkonto, bei Fehler neu."""
    task = ET.Element("Task", {"version": "1.2", "xmlns": TASK_XMLNS})
    info = ET.SubElement(task, "RegistrationInfo")
    ET.SubElement(info, "Description").text = (
        "Zeigt den Titel aus Apple Music oder iTunes auf einer AWTRIX-Uhr."
    )
    triggers = ET.SubElement(task, "Triggers")
    trigger = ET.SubElement(triggers, "LogonTrigger")
    ET.SubElement(trigger, "Enabled").text = "true"

    principals = ET.SubElement(task, "Principals")
    principal = ET.SubElement(principals, "Principal", {"id": "Author"})
    ET.SubElement(principal, "LogonType").text = "InteractiveToken"
    ET.SubElement(principal, "RunLevel").text = "LeastPrivilege"

    settings = ET.SubElement(task, "Settings")
    ET.SubElement(settings, "MultipleInstancesPolicy").text = "IgnoreNew"
    ET.SubElement(settings, "DisallowStartIfOnBatteries").text = "false"
    ET.SubElement(settings, "StopIfGoingOnBatteries").text = "false"
    ET.SubElement(settings, "AllowHardTerminate").text = "true"
    ET.SubElement(settings, "StartWhenAvailable").text = "true"
    ET.SubElement(settings, "RunOnlyIfNetworkAvailable").text = "false"
    ET.SubElement(settings, "AllowStartOnDemand").text = "true"
    ET.SubElement(settings, "Enabled").text = "true"
    ET.SubElement(settings, "Hidden").text = "false"
    ET.SubElement(settings, "RunOnlyIfIdle").text = "false"
    ET.SubElement(settings, "ExecutionTimeLimit").text = "PT0S"
    ET.SubElement(settings, "Priority").text = "7"
    restart = ET.SubElement(settings, "RestartOnFailure")
    ET.SubElement(restart, "Interval").text = "PT1M"
    ET.SubElement(restart, "Count").text = "999"

    actions = ET.SubElement(task, "Actions", {"Context": "Author"})
    action = ET.SubElement(actions, "Exec")
    ET.SubElement(action, "Command").text = executable
    ET.SubElement(action, "Arguments").text = program_arguments(executable, script, config)
    ET.SubElement(action, "WorkingDirectory").text = workdir

    body = ET.tostring(task, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-16"?>\n' + body


def install(
    *,
    source_root: Path,
    port: int,
    key: str,
    executable: str,
    base_dir: Path,
    runner=subprocess.run,
) -> Path:
    """Kopiert den Helper und trägt die Anmeldungsaufgabe ein."""
    package = source_root / "awtrix_itunes"
    script = source_root / "itunes-helper.py"
    if not package.is_dir() or not script.is_file():
        raise SystemExit("itunes-helper.py und awtrix_itunes müssen im selben Ordner liegen.")

    dest = base_dir / FOLDER_NAME
    dest.mkdir(parents=True, exist_ok=True)
    package_dest = dest / "awtrix_itunes"
    if package_dest.exists():
        shutil.rmtree(package_dest)
    shutil.copytree(package, package_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(script, dest / "itunes-helper.py")

    config_path = dest / "config.json"
    config_path.write_text(
        json.dumps({"port": port, "key": key}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    chosen = windowless_python(executable)
    xml = build_task_xml(
        executable=chosen,
        script=str(dest / "itunes-helper.py"),
        config=str(config_path),
        workdir=str(dest),
    )
    xml_path = dest / "task.xml"
    xml_path.write_text(xml, encoding="utf-16")

    runner(["schtasks", "/End", "/TN", TASK_NAME], check=False)
    runner(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], check=False)
    runner(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"], check=True)
    runner(["schtasks", "/Run", "/TN", TASK_NAME], check=True)
    return dest


def uninstall(*, base_dir: Path, runner=subprocess.run) -> None:
    runner(["schtasks", "/End", "/TN", TASK_NAME], check=False)
    runner(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], check=False)
    dest = base_dir / FOLDER_NAME
    if dest.exists():
        shutil.rmtree(dest)


def _quote(value: str) -> str:
    if '"' in value:
        raise SystemExit("Ein Pfad enthält ein Anführungszeichen und kann nicht eingetragen werden.")
    return f'"{value}"'
