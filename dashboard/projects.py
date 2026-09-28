"""Read-only STATUS.md adapter for SelfWebUI and existing project folders."""
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Bereiche als "Praefix=Pfad", mit Komma getrennt. Leeres Praefix = Name ohne Zusatz.
BEREICHE = [
    (teil.split("=", 1)[0].strip(), Path(teil.split("=", 1)[1].strip())) if "=" in teil else ("", Path(teil.strip()))
    for teil in os.environ.get("PROJEKTE", "=/projekte,Code=/code").split(",")
    if teil.strip()
]
UPDATES = Path(os.environ.get("UPDATES", "/updates/status.json"))
PORT = int(os.environ.get("PORT", "8097"))

AUFGABE = re.compile(r"^\s*[-*]\s+(?P<name>.+?)\s+[—–-]{1,2}\s+(?P<zustand>[^:]+?)\s*:\s*(?P<text>.*)$")
RANG = {"wartet": 0, "in arbeit": 1, "fertig": 2}


def rang(zustand: str) -> int:
    z = zustand.lower()
    for schluessel, wert in RANG.items():
        if schluessel in z:
            return wert
    return 1


def lies_status(datei: Path) -> dict:
    aufgaben, fragen, abschnitt = [], [], ""
    for zeile in datei.read_text(encoding="utf-8", errors="replace").splitlines():
        if zeile.startswith("## "):
            abschnitt = zeile[3:].strip().lower()
            continue
        if "wartet auf sven" in zeile.lower():
            t = re.sub(r"(?i).*wartet auf sven:?\s*", "", zeile).strip(" -*")
            if t and t not in fragen:
                fragen.append(t)
        if abschnitt.startswith("aufgaben"):
            m = AUFGABE.match(zeile)
            if m:
                aufgaben.append({k: m.group(k).strip() for k in ("name", "zustand", "text")})
        elif abschnitt.startswith("offene fragen"):
            t = zeile.strip().lstrip("-* ").strip()
            if t and t not in fragen:
                fragen.append(t)
    aufgaben.sort(key=lambda a: rang(a["zustand"]))
    return {"aufgaben": aufgaben, "fragen": fragen}


def status() -> dict:
    projekte = []
    ordner_liste = [(praefix, o) for praefix, wurzel in BEREICHE
                    for o in sorted(wurzel.iterdir() if wurzel.is_dir() else [])]
    for praefix, ordner in ordner_liste:
        datei = ordner / "STATUS.md"
        if not datei.is_file():
            continue
        try:
            eintrag = lies_status(datei)
            geaendert = datei.stat().st_mtime
        except OSError:
            continue
        eintrag["name"] = f"{praefix} · {ordner.name}" if praefix else ordner.name
        eintrag["geaendert"] = datetime.fromtimestamp(geaendert, timezone.utc).isoformat(timespec="seconds")
        projekte.append(eintrag)
    # Projekte mit offenen Fragen zuerst, dann nach letzter Aenderung.
    projekte.sort(key=lambda p: (not p["fragen"], p["geaendert"]), reverse=False)
    projekte.sort(key=lambda p: not p["fragen"])
    try:
        updates = json.loads(UPDATES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        updates = None
    return {"erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "projekte": projekte, "updates": updates}


