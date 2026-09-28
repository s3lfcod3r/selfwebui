"""Persistent RTX metrics collector; preserves imported historical counters."""
import json
import os
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# "Name=URL" je Eintrag, mit Komma getrennt
SERVER = os.environ.get("SERVER", "")
DATEN = Path(os.environ.get("DATEN", "/daten"))
PORT = int(os.environ.get("PORT", "8098"))
ABSTAND = int(os.environ.get("ABSTAND_SEKUNDEN", "60"))
TAGE = int(os.environ.get("TAGE", "400"))
from zoneinfo import ZoneInfo
ZEITZONE = ZoneInfo("Europe/Berlin")

VERLAUF = DATEN / "verlauf.json"
OC_ZEILE = re.compile(r'^openclaw_model_tokens_total\{([^}]*)\}\s+([0-9.eE+-]+)\s*$')
PAAR = re.compile(r'(\w+)="([^"]*)"')
LLAMA = re.compile(r'^llamacpp:([a-z_]+)\s+([0-9.eE+-]+)\s*$')

sperre = threading.Lock()
stand = {"letzte_pruefung": None, "fehler": None, "roh": {}, "tage": {}, "spitze": {}}


def heute() -> str:
    return datetime.now(ZEITZONE).strftime("%Y-%m-%d")


def lade() -> None:
    try:
        stand.update(json.loads(VERLAUF.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    stand.setdefault("spitze", {})


def sichere() -> None:
    try:
        DATEN.mkdir(parents=True, exist_ok=True)
        tmp = VERLAUF.with_suffix(".tmp")
        tmp.write_text(json.dumps(stand, ensure_ascii=False), encoding="utf-8")
        tmp.replace(VERLAUF)
    except OSError as e:
        stand["fehler"] = f"Speichern: {e}"


def hole(url: str, token: str | None = None) -> str:
    kopf = {"Authorization": f"Bearer {token}"} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=kopf), timeout=15) as r:
        return r.read().decode("utf-8", "replace")


def von_servern() -> tuple[dict, dict]:
    """Zaehler und Spitzenwerte der llama.cpp-Server."""
    werte, spitzen = {}, {}
    for teil in SERVER.split(","):
        teil = teil.strip()
        if not teil:
            continue
        name, _, adresse = teil.partition("=")
        name, adresse = name.strip(), (adresse or name).strip().rstrip("/")
        try:
            roh = {m.group(1): float(m.group(2))
                   for m in (LLAMA.match(z.strip()) for z in hole(f"{adresse}/metrics").splitlines()) if m}
        except Exception as exc:
            raise RuntimeError("RTX-Modellserver nicht erreichbar") from exc
        werte[f"server|{name}|ein"] = roh.get("prompt_tokens_total", 0)
        werte[f"server|{name}|aus"] = roh.get("tokens_predicted_total", 0)
        if roh.get("n_tokens_max"):
            spitzen[name] = roh["n_tokens_max"]
    return werte, spitzen


def verbuche(neu: dict, spitzen: dict) -> None:
    alt = stand.get("roh", {})
    tag = stand.setdefault("tage", {}).setdefault(heute(), {})
    for schluessel, wert in neu.items():
        vorher = alt.get(schluessel, 0)
        zuwachs = wert - vorher if wert >= vorher else wert   # Zaehler neu gestartet
        if zuwachs > 0:
            tag[schluessel] = tag.get(schluessel, 0) + zuwachs
    stand["roh"] = {**alt, **neu}
    heutige_spitze = stand.setdefault("spitze", {}).setdefault(heute(), {})
    for name, wert in spitzen.items():
        if wert > heutige_spitze.get(name, 0):
            heutige_spitze[name] = wert
    for t in sorted(stand["tage"])[:-TAGE]:
        del stand["tage"][t]
    for t in sorted(stand["spitze"])[:-TAGE]:
        del stand["spitze"][t]


def schleife() -> None:
    while True:
        alles, fehler = {}, None
        try:
            werte, spitzen = von_servern()
            alles.update(werte)
        except Exception as e:
            spitzen = {}
            fehler = f"{fehler + '; ' if fehler else ''}Server: {type(e).__name__}"
        with sperre:
            if alles:
                verbuche(alles, spitzen)
            stand["letzte_pruefung"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            stand["fehler"] = fehler
            sichere()
        time.sleep(ABSTAND)


def summen(roh: dict, spitzen: dict | None = None) -> dict:
    gesamt = {"ein": 0, "aus": 0, "cache_gelesen": 0, "cache_geschrieben": 0}
    agenten, server = {}, {}
    for schluessel, wert in roh.items():
        teile = schluessel.split("|")
        if teile[0] == "agent":
            _, agent, provider, art = teile
            if art in gesamt:
                gesamt[art] += wert
            if art in ("ein", "aus"):
                agenten.setdefault("OpenClaw (Verlauf) · "+agent, {"ein": 0, "aus": 0})[art] += wert
        elif teile[0] == "server":
            _, name, art = teile
            server.setdefault(name, {"ein": 0, "aus": 0})[art] += wert
    # Die Gesamtzahl kommt von den Modell-Servern: sie zaehlen laufend mit.
    # OpenClaws eigene Zaehler springen nur zu bestimmten Zeitpunkten und
    # wirken dazwischen eingefroren - die zeigen wir nur als Aufteilung.
    if server:
        gesamt["ein"] = sum(w["ein"] for w in server.values())
        gesamt["aus"] = sum(w["aus"] for w in server.values())
    return {"gesamt": gesamt, "agenten": agenten, "server": server,
            "spitze": spitzen or {}}


def bereich(tage: list[str]) -> dict:
    roh, spitzen = {}, {}
    for t in tage:
        for k, v in stand.get("tage", {}).get(t, {}).items():
            roh[k] = roh.get(k, 0) + v
        for n, v in stand.get("spitze", {}).get(t, {}).items():
            spitzen[n] = max(spitzen.get(n, 0), v)
    return summen(roh, spitzen)


def server_adressen() -> dict:
    """Name -> Adresse je llama-Server, damit die Kachel die Namen aus LLM-Tempo uebernehmen kann."""
    aus = {}
    for teil in SERVER.split(","):
        name, _, adresse = teil.strip().partition("=")
        if name.strip():
            aus[name.strip()] = (adresse or name).strip().rstrip("/")
    return aus


def antwort() -> dict:
    with sperre:
        alle = sorted(stand.get("tage", {}))
        h = heute()
        gestern = (datetime.now(ZEITZONE) - timedelta(days=1)).strftime("%Y-%m-%d")
        monate = sorted({t[:7] for t in alle})
        return {
            "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "letzte_pruefung": stand.get("letzte_pruefung"),
            "fehler": stand.get("fehler"),
            "heute": bereich([h]),
            "gestern": bereich([gestern]),
            "woche": bereich([(datetime.now(ZEITZONE)-timedelta(days=n)).strftime("%Y-%m-%d") for n in range(7)]),
            "monate": {m: bereich([t for t in alle if t.startswith(m)]) for m in monate[-13:]},
            "tage": {t: bereich([t])["gesamt"] for t in alle[-62:]},
            "adressen": server_adressen(),
        }


