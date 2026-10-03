#!/usr/bin/env python3
"""Bild-Dienst für Bonsai (Board 1, Port 8111): nimmt Bildaufträge an und wechselt dafür die GPU-Belegung.

Ablauf je Auftrag: warten, bis Bonsai ruhig ist (hat seinen Zug beendet) und die Karte frei genug ist -> Bonsai entladen
(docker stop) -> Qwen-Image 2.1 im Wegwerf-Container rechnen -> Bonsai wieder laden (docker start, wartet auf /health).
Bonsai wird nur wieder gestartet, wenn er vorher lief. Nichts läuft gleichzeitig: Auftrag für Auftrag.

HTTP (nur LAN, kein Login, wie die anderen Dienste auf dem Board):
  POST /auftrag             JSON {modus: neu|bearbeiten, prompt, seed?, breite?, hoehe?, anzahl?, vorlage?} -> {id}
  PUT  /vorlage/<name>      Referenzbild hochladen (bis 25 MB), name = [A-Za-z0-9._-]+
  GET  /status/<id>         Zustand: wartet | laedt | rechnet | fertig | fehler
  GET  /liste               die letzten 20 Aufträge
  GET  /ergebnis/<id>/<datei>.png
"""
import fcntl
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATEN = Path(os.environ.get("BILD_DATEN", "/daten"))
HOST_DATEN = os.environ.get("BILD_HOST_DATEN", "/media/Safe-Storage/appdata/bild-dienst")
QWEN_MODELLE = os.environ.get("QWEN_MODELLE", "/media/Safe-Storage/appdata/deritler-pipeline/models/qwen-image21")
BONSAI_URL = os.environ.get("BONSAI_URL", "http://192.168.1.103:8085").rstrip("/")
BONSAI_CONTAINER = os.environ.get("BONSAI_CONTAINER", "bonsai-combo")
QWEN_IMAGE = os.environ.get("QWEN_IMAGE", "deritler-qwen-image21:local")
LOCK_DATEI = os.environ.get("PRODUKTIONS_LOCK", "/deritler-runtime/production.lock")
MAX_VRAM_MIB = int(os.environ.get("MAX_VRAM_MIB", "5000"))     # darüber ist die Karte für Qwen zu belegt (Stimme, HandBrake)
BONSAI_RUHE_S = int(os.environ.get("BONSAI_RUHE_S", "20"))
JOB_FRIST_S = int(os.environ.get("JOB_FRIST_S", "2400"))
AUFBEWAHREN_TAGE = int(os.environ.get("AUFBEWAHREN_TAGE", "30"))
MAX_SEITE = int(os.environ.get("MAX_SEITE", "2048"))               # längste erlaubte Bildseite (neu)
MAX_AUFLOESUNG = int(os.environ.get("MAX_AUFLOESUNG", "2048"))   # Kantenmaß beim Bearbeiten: Ergebnis hat etwa Aufloesung x Aufloesung Pixel
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
ID = re.compile(r"\d{8}-\d{6}-[0-9a-f]{4}")
LAUFENDE_ZUSTAENDE = ("wartet", "laedt", "rechnet")
BILD_TROCKEN = os.environ.get("BILD_TROCKEN") == "1"   # nur für Tests: Warteschlange und HTTP ohne Docker und ohne Karte

(DATEN / "jobs").mkdir(parents=True, exist_ok=True)
(DATEN / "vorlagen").mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()


# ---------------------------------------------------------------- Hilfen
def docker(*args, timeout=60):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def status_lesen(job_id):
    try:
        return json.loads((DATEN / "jobs" / job_id / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status_setzen(job_id, zustand, meldung="", **extra):
    with _lock:
        alt = status_lesen(job_id) or {}
        alt.update(zustand=zustand, meldung=meldung, geaendert=int(time.time()), **extra)
        pfad = DATEN / "jobs" / job_id / "status.json"
        pfad.write_text(json.dumps(alt, ensure_ascii=False), encoding="utf-8")
        return alt


def bonsai_laeuft():
    if BILD_TROCKEN:
        return False
    r = docker("inspect", "-f", "{{.State.Running}}", BONSAI_CONTAINER)
    return r.returncode == 0 and r.stdout.strip() == "true"


def bonsai_beschaeftigt():
    """True, solange Bonsai rechnet. Nicht erreichbar zählt als ruhig."""
    try:
        with urllib.request.urlopen(BONSAI_URL + "/slots", timeout=4) as antwort:
            return any(slot.get("is_processing") for slot in json.load(antwort))
    except (OSError, ValueError):
        return False


def vram_belegt_mib():
    r = docker("exec", "gpufan", "nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits")
    try:
        return int(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return 99999


def ram_frei_mib():
    for zeile in Path("/proc/meminfo").read_text().splitlines():
        if zeile.startswith("MemAvailable:"):
            return int(zeile.split()[1]) // 1024
    return 0


def bonsai_starten():
    docker("start", BONSAI_CONTAINER)
    ende = time.time() + 240
    while time.time() < ende:
        try:
            with urllib.request.urlopen(BONSAI_URL + "/health", timeout=3) as antwort:
                if antwort.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(5)
    return False


# ---------------------------------------------------------------- Abarbeiten
def auftrag_abarbeiten(job_id):
    ordner = DATEN / "jobs" / job_id
    auftrag = json.loads((ordner / "auftrag.json").read_text(encoding="utf-8"))
    bonsai_war_an = False
    sperre = None
    try:
        # 1. Warten: Bonsai ruhig, genug Arbeitsspeicher, Produktionssperre von DerITler frei
        ruhig_seit = None
        beginn = time.time()
        while True:
            if time.time() - beginn > 3600:
                raise RuntimeError("Nach 60 Minuten keine freie Gelegenheit (Bonsai oder DerITler blockiert dauerhaft)")
            if bonsai_beschaeftigt():
                ruhig_seit = None
            elif ruhig_seit is None:
                ruhig_seit = time.time()
            ruhig = ruhig_seit is not None and time.time() - ruhig_seit >= BONSAI_RUHE_S
            if ruhig:
                if sperre is None:
                    kandidat = open(LOCK_DATEI, "a")
                    try:
                        fcntl.flock(kandidat, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        sperre = kandidat
                    except OSError:
                        kandidat.close()
                if sperre is not None:
                    break
            status_setzen(job_id, "wartet", "wartet, bis Bonsai seinen Zug beendet hat und die Karte frei ist")
            time.sleep(5)

        # 2. Bonsai entladen
        status_setzen(job_id, "laedt", "Bonsai wird entladen, Qwen-Image wird geladen")
        bonsai_war_an = (not BILD_TROCKEN) and bonsai_laeuft()
        if bonsai_war_an:
            docker("stop", "-t", "15", BONSAI_CONTAINER, timeout=60)
        for _ in range(24):   # bis zu 2 Minuten: VRAM muss frei werden
            if BILD_TROCKEN or (vram_belegt_mib() <= MAX_VRAM_MIB and ram_frei_mib() >= 9216):
                break
            time.sleep(5)
        else:
            raise RuntimeError("Die Karte ist belegt (%d MiB VRAM, %d MiB RAM frei): Stimme, HandBrake oder DerITler laufen" % (vram_belegt_mib(), ram_frei_mib()))

        # 3. Rechnen
        status_setzen(job_id, "rechnet", "Qwen-Image 2.1 rechnet", gestartet=int(time.time()))
        host_job = f"{HOST_DATEN}/jobs/{job_id}"
        befehl = ["run", "--rm", "--name", f"bild-qwen-{job_id}", "--runtime=nvidia", "--gpus", "all", "--network", "none",
                  "--memory", "11g", "--memory-swap", "11g", "-e", "HF_HUB_OFFLINE=1",
                  "-v", f"{host_job}:/job",
                  "-v", f"{HOST_DATEN}/bild_allgemein.py:/opt/bild_allgemein.py:ro",
                  "-v", f"{QWEN_MODELLE}/diffusion_models:/opt/ComfyUI/models/diffusion_models:ro",
                  "-v", f"{QWEN_MODELLE}/text_encoders:/opt/ComfyUI/models/text_encoders:ro",
                  "-v", f"{QWEN_MODELLE}/vae:/opt/ComfyUI/models/vae:ro",
                  QWEN_IMAGE, "/opt/bild_allgemein.py"]
        if BILD_TROCKEN:
            time.sleep(2)
            (ordner / "ergebnis-0.png").write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0f01f0005000201a5f645400000000049454e44ae426082"))
            ergebnis = subprocess.CompletedProcess([], 0, "", "")
        else:
            ergebnis = docker(*befehl, timeout=JOB_FRIST_S)
        if ergebnis.returncode != 0:
            raise RuntimeError(((ergebnis.stderr or ergebnis.stdout) or "unbekannter Fehler")[-500:])
        dateien = sorted(p.name for p in ordner.glob("ergebnis-*.png"))
        if not dateien:
            raise RuntimeError("Qwen-Image hat kein Bild geliefert")
        status_setzen(job_id, "fertig", "Bild fertig", dateien=dateien, fertig=int(time.time()))
    except subprocess.TimeoutExpired:
        docker("rm", "-f", f"bild-qwen-{job_id}")
        status_setzen(job_id, "fehler", f"Zeitüberschreitung nach {JOB_FRIST_S} s")
    except Exception as fehler:   # noqa: BLE001 - der Fehler wird dem Auftrag mitgegeben
        status_setzen(job_id, "fehler", str(fehler)[:500])
    finally:
        if BILD_TROCKEN:
            bonsai_war_an = False
        if bonsai_war_an and not bonsai_laeuft():
            if not bonsai_starten():
                status_setzen(job_id, (status_lesen(job_id) or {}).get("zustand", "fehler"),
                              ((status_lesen(job_id) or {}).get("meldung", "") + " | WARNUNG: Bonsai antwortet nach dem Neustart nicht, bitte prüfen")[:600])
        if sperre is not None:
            try:
                fcntl.flock(sperre, fcntl.LOCK_UN)
                sperre.close()
            except OSError:
                pass
        (DATEN / "bonsai-war-an").unlink(missing_ok=True)


def aufraeumen(jetzt=None):
    """Löscht Aufträge und hochgeladene Vorlagen, die älter als AUFBEWAHREN_TAGE sind. Laufende Aufträge bleiben immer."""
    jetzt = jetzt or time.time()
    grenze = jetzt - AUFBEWAHREN_TAGE * 86400
    geloescht = 0
    for ordner in list((DATEN / "jobs").iterdir()):
        s = status_lesen(ordner.name) or {}
        if s.get("zustand") in LAUFENDE_ZUSTAENDE:
            continue
        stand = s.get("geaendert") or ordner.stat().st_mtime
        if stand < grenze:
            shutil.rmtree(ordner, ignore_errors=True)
            geloescht += 1
    for datei in list((DATEN / "vorlagen").iterdir()):
        if datei.is_file() and datei.stat().st_mtime < grenze:
            datei.unlink(missing_ok=True)
            geloescht += 1
    return geloescht


def laeufer():
    # Nach einem Neustart des Dienstes: halbfertige Aufträge als Fehler markieren und Bonsai wieder anschalten
    for ordner in sorted((DATEN / "jobs").iterdir()):
        s = status_lesen(ordner.name)
        if s and s.get("zustand") in ("laedt", "rechnet"):
            status_setzen(ordner.name, "fehler", "Dienst wurde währenddessen neu gestartet")
            if (DATEN / "bonsai-war-an").exists() and not bonsai_laeuft():
                bonsai_starten()
    naechste_pflege = 0.0
    while True:
        if time.time() >= naechste_pflege:
            try:
                aufraeumen()
            except OSError:
                pass
            naechste_pflege = time.time() + 3600
        wartend = [o.name for o in sorted((DATEN / "jobs").iterdir()) if (status_lesen(o.name) or {}).get("zustand") == "wartet"]
        if wartend:
            auftrag_abarbeiten(wartend[0])
        else:
            time.sleep(3)


# ---------------------------------------------------------------- HTTP
class Anfrage(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def senden(self, code, daten, typ="application/json"):
        koerper = daten if isinstance(daten, bytes) else json.dumps(daten, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(koerper)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(koerper)

    def do_OPTIONS(self):
        self.send_response(204)
        for kopf, wert in (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS"),
                           ("Access-Control-Allow-Headers", "Content-Type")):
            self.send_header(kopf, wert)
        self.end_headers()

    def do_GET(self):
        pfad = self.path.split("?")[0]
        if pfad == "/liste":
            eintraege = []
            for ordner in sorted((DATEN / "jobs").iterdir(), reverse=True)[:20]:
                s = status_lesen(ordner.name)
                if s:
                    eintraege.append({"id": ordner.name, **{k: s.get(k) for k in ("zustand", "meldung", "dateien", "prompt", "modus", "geaendert")}})
            return self.senden(200, {"auftraege": eintraege})
        treffer = re.fullmatch(r"/status/(" + ID.pattern + ")", pfad)
        if treffer:
            s = status_lesen(treffer.group(1))
            return self.senden(200 if s else 404, s or {"fehler": "unbekannte Auftrags-ID"})
        treffer = re.fullmatch(r"/ergebnis/(" + ID.pattern + r")/(ergebnis-\d\.png)", pfad)
        if treffer:
            datei = DATEN / "jobs" / treffer.group(1) / treffer.group(2)
            if datei.is_file():
                return self.senden(200, datei.read_bytes(), "image/png")
        self.senden(404, {"fehler": "nicht gefunden"})

    def do_PUT(self):
        treffer = re.fullmatch(r"/vorlage/(" + NAME.pattern + ")", self.path.split("?")[0])
        laenge = int(self.headers.get("Content-Length") or 0)
        if not treffer or laenge <= 0 or laenge > 25 * 1024 * 1024:
            return self.senden(400, {"fehler": "Name [A-Za-z0-9._-] und Größe bis 25 MB erforderlich"})
        (DATEN / "vorlagen" / treffer.group(1)).write_bytes(self.rfile.read(laenge))
        self.senden(200, {"vorlage": treffer.group(1), "bytes": laenge})

    def do_POST(self):
        if self.path.split("?")[0] != "/auftrag":
            return self.senden(404, {"fehler": "nicht gefunden"})
        try:
            a = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            modus = a.get("modus", "neu")
            prompt = str(a.get("prompt", "")).strip()
            if modus not in ("neu", "bearbeiten") or not 3 <= len(prompt) <= 2000:
                raise ValueError("modus neu|bearbeiten und prompt (3 bis 2000 Zeichen) erforderlich")
            anzahl = max(1, min(int(a.get("anzahl", 1)), 4))
            breite, hoehe = int(a.get("breite", 1024)), int(a.get("hoehe", 1024))
            if not (512 <= breite <= MAX_SEITE and 512 <= hoehe <= MAX_SEITE and breite % 16 == 0 and hoehe % 16 == 0):
                raise ValueError("breite und hoehe: 512 bis %d in 16er-Schritten" % MAX_SEITE)
            aufloesung = int(a.get("aufloesung", 1024))
            if not 512 <= aufloesung <= MAX_AUFLOESUNG:
                raise ValueError("aufloesung: 512 bis %d" % MAX_AUFLOESUNG)
            vorlage = a.get("vorlage")
            if modus == "bearbeiten":
                if not isinstance(vorlage, str) or not NAME.fullmatch(vorlage) or not (DATEN / "vorlagen" / vorlage).is_file():
                    raise ValueError("Für bearbeiten zuerst die Vorlage hochladen (PUT /vorlage/<name>) und den Namen angeben")
            job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
            ordner = DATEN / "jobs" / job_id
            ordner.mkdir(parents=True)
            auftrag = {"modus": modus, "prompt": prompt, "anzahl": anzahl, "breite": breite, "hoehe": hoehe, "aufloesung": aufloesung,
                       "seed": int(a["seed"]) if a.get("seed") is not None else int(time.time()) % 100000000}
            if modus == "bearbeiten":
                endung = Path(vorlage).suffix.lower() or ".png"
                (ordner / ("vorlage" + endung)).write_bytes((DATEN / "vorlagen" / vorlage).read_bytes())
            (ordner / "auftrag.json").write_text(json.dumps(auftrag, ensure_ascii=False), encoding="utf-8")
            status_setzen(job_id, "wartet", "angenommen", prompt=prompt[:200], modus=modus, angelegt=int(time.time()))
            if bonsai_laeuft():
                (DATEN / "bonsai-war-an").write_text("1")
            self.senden(200, {"id": job_id, "zustand": "wartet",
                              "hinweis": "Bonsai wird für das Bild entladen, sobald er seinen Zug beendet hat. Beende jetzt deinen Zug."})
        except (ValueError, KeyError, TypeError) as fehler:
            self.senden(400, {"fehler": str(fehler)})


if __name__ == "__main__":
    threading.Thread(target=laeufer, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8111"))), Anfrage).serve_forever()
