"""Test der Archiv-Funktionen des Bild-Dienstes (Trockenlauf, ohne Docker und ohne Karte).

Aufruf auf dem Board:  docker run --rm -v <ordner>:/code -w /code python:3.12-slim python test_archiv.py
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

daten = tempfile.mkdtemp()


class BonsaiStub(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        antwort = json.dumps({"choices": [{"message": {"content": "<think>x</think>\"A red lighthouse at dusk, no readable text.\""}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(antwort)))
        self.end_headers()
        self.wfile.write(antwort)


stub = ThreadingHTTPServer(("127.0.0.1", 0), BonsaiStub)
threading.Thread(target=stub.serve_forever, daemon=True).start()
os.environ.update(BILD_DATEN=daten, BILD_TROCKEN="1", PRODUKTIONS_LOCK=daten + "/x.lock", BONSAI_URL="http://127.0.0.1:%d" % stub.server_port)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bild_dienst as b  # noqa: E402

server = ThreadingHTTPServer(("127.0.0.1", 0), b.Anfrage)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d" % server.server_port


def rufen(methode, pfad, daten_=None):
    anfrage = urllib.request.Request(URL + pfad, method=methode, data=json.dumps(daten_).encode() if daten_ is not None else None,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(anfrage, timeout=10) as antwort:
            koerper = antwort.read()
            return antwort.status, (json.loads(koerper) if antwort.headers.get("Content-Type") == "application/json" else koerper)
    except urllib.error.HTTPError as fehler:
        return fehler.code, json.loads(fehler.read())


jetzt = time.time()
tag = 86400


def auftrag(job_id, zustand, alter_tage, prompt="Ein Test", modus="neu", favorit=False, thumb=False, vorlage=False):
    ordner = Path(daten) / "jobs" / job_id
    ordner.mkdir(parents=True)
    (ordner / "ergebnis-0.png").write_bytes(b"png")
    if thumb:
        (ordner / "thumb-0.jpg").write_bytes(b"jpg")
    if vorlage:
        (ordner / "vorlage.jpg").write_bytes(b"foto")
    (ordner / "auftrag.json").write_text(json.dumps({"modus": modus, "prompt": prompt, "seed": 5, "breite": 1024, "hoehe": 1024, "aufloesung": 1024, "anzahl": 1}))
    (ordner / "status.json").write_text(json.dumps({"zustand": zustand, "meldung": "m", "dateien": ["ergebnis-0.png"], "geaendert": int(jetzt - alter_tage * tag), "favorit": favorit}))


auftrag("20260101-000000-aaaa", "fertig", 40, prompt="Leuchtturm im Sturm", thumb=True)
auftrag("20260102-000000-bbbb", "fertig", 40, prompt="Hase auf Wiese", modus="bearbeiten", vorlage=True)
auftrag("20260103-000000-cccc", "fertig", 40, prompt="Mein Favorit", favorit=True)
auftrag("20260104-000000-dddd", "fertig", 2, prompt="Neu")
auftrag("20260105-000000-eeee", "wartet", 50, prompt="Wartet")
auftrag("20260106-000000-ffff", "rechnet", 50, prompt="Rechnet")

# Archiv und Filter
code, a = rufen("GET", "/archiv")
assert code == 200 and len(a["auftraege"]) == 6, a
assert a["auftraege"][0]["id"] == "20260106-000000-ffff"            # neueste zuerst
eintrag = [e for e in a["auftraege"] if e["id"] == "20260101-000000-aaaa"][0]
assert eintrag["thumbs"] == ["thumb-0.jpg"] and eintrag["prompt"] == "Leuchtturm im Sturm" and eintrag["seed"] == 5 and eintrag["breite"] == 1024
assert [e["id"] for e in rufen("GET", "/archiv?q=hase")[1]["auftraege"]] == ["20260102-000000-bbbb"]
assert [e["id"] for e in rufen("GET", "/archiv?favorit=1")[1]["auftraege"]] == ["20260103-000000-cccc"]
assert [e["id"] for e in rufen("GET", "/archiv?modus=bearbeiten")[1]["auftraege"]] == ["20260102-000000-bbbb"]
assert rufen("GET", "/archiv?limit=2")[1]["auftraege"][1]["id"] == "20260105-000000-eeee"

# Vorschaubild und Ausgangsfoto
assert rufen("GET", "/ergebnis/20260101-000000-aaaa/thumb-0.jpg") == (200, b"jpg")
assert rufen("GET", "/vorlage-bild/20260102-000000-bbbb") == (200, b"foto")
assert rufen("GET", "/vorlage-bild/20260101-000000-aaaa")[0] == 404

# Einstellungen: Standard 30 Tage, setzen, ungültig
code, e = rufen("GET", "/einstellungen")
assert code == 200 and e["aufbewahren_tage"] == 30 and e["auftraege"] == 6 and e["bytes"] > 0 and e["frei"] > 0, e
assert rufen("POST", "/einstellungen", {"aufbewahren_tage": 7})[1]["aufbewahren_tage"] == 7
assert rufen("POST", "/einstellungen", {"aufbewahren_tage": -3})[0] == 400
assert rufen("POST", "/einstellungen", {"aufbewahren_tage": 99999})[0] == 400

# Aufräumen: nie = nichts, 30 Tage = alte weg, Favorit und Laufende bleiben
rufen("POST", "/einstellungen", {"aufbewahren_tage": 0})
assert rufen("POST", "/aufraeumen")[1]["geloescht"] == 0
rufen("POST", "/einstellungen", {"aufbewahren_tage": 30})
assert rufen("POST", "/aufraeumen")[1]["geloescht"] == 2                    # Leuchtturm und Hase
rest = sorted(p.name for p in (Path(daten) / "jobs").iterdir())
assert rest == ["20260103-000000-cccc", "20260104-000000-dddd", "20260105-000000-eeee", "20260106-000000-ffff"], rest

# Favorit setzen und entfernen
assert rufen("POST", "/auftrag/20260104-000000-dddd/favorit", {"an": True})[1]["favorit"] is True
assert rufen("POST", "/auftrag/20260104-000000-dddd/favorit", {"an": False})[1]["favorit"] is False
assert rufen("POST", "/auftrag/20250101-000000-0000/favorit", {"an": True})[0] == 404

# Abbrechen: nur wartende; löschen: nicht laufende
assert rufen("POST", "/auftrag/20260106-000000-ffff/abbrechen")[0] == 409
assert rufen("POST", "/auftrag/20260105-000000-eeee/abbrechen")[0] == 200
assert b.status_lesen("20260105-000000-eeee")["zustand"] == "fehler"
assert rufen("DELETE", "/auftrag/20260106-000000-ffff")[0] == 409
assert rufen("DELETE", "/auftrag/20260105-000000-eeee")[0] == 200
assert not (Path(daten) / "jobs" / "20260105-000000-eeee").exists()
assert rufen("DELETE", "/auftrag/20260105-000000-eeee")[0] == 404

# Archivbild als neue Vorlage
code, v = rufen("POST", "/vorlage-aus-ergebnis", {"id": "20260104-000000-dddd", "datei": "ergebnis-0.png"})
assert code == 200 and (Path(daten) / "vorlagen" / v["vorlage"]).read_bytes() == b"png", v
assert rufen("POST", "/vorlage-aus-ergebnis", {"id": "20260104-000000-dddd", "datei": "../x.png"})[0] == 400
code, auf = rufen("POST", "/auftrag", {"modus": "bearbeiten", "prompt": "Nochmal anders", "vorlage": v["vorlage"]})
assert code == 200, auf

# Prompt von Bonsai (Stub) und Ausfall
code, p = rufen("POST", "/prompt", {"text": "Ein roter Leuchtturm bei Dämmerung", "modus": "neu"})
assert code == 200 and p["prompt"] == "A red lighthouse at dusk, no readable text.", p
assert rufen("POST", "/prompt", {"text": "x"})[0] == 400
# Freistellen (Docker ist im Test ersetzt)
aufrufe = []


def falsches_docker(*args, timeout=60):
    aufrufe.append(args)
    ziel = [x for x in args if str(x).startswith("/job/frei-")]
    if ziel and "ZERO" not in os.environ:
        host = [x for x in args if str(x).endswith(":/job")][0].split(":")[0]
        (Path(daten) / "jobs" / host.rsplit("/", 1)[1] / ziel[0].split("/")[-1]).write_bytes(b"freipng")
    return __import__("subprocess").CompletedProcess(args, 0, "", "")


b.docker = falsches_docker
code, fr = rufen("POST", "/freistellen", {"id": "20260104-000000-dddd"})
assert code == 200 and fr["frei"] == ["frei-0.png"], fr
assert any("deritler-freistellen:local" in a_ for a_ in aufrufe)
assert rufen("GET", "/ergebnis/20260104-000000-dddd/frei-0.png") == (200, b"freipng")
assert [e for e in rufen("GET", "/archiv")[1]["auftraege"] if e["id"] == "20260104-000000-dddd"][0]["frei"] == ["frei-0.png"]
assert rufen("POST", "/freistellen", {"id": "20260104-000000-dddd", "datei": "../x"})[0] == 400
assert rufen("POST", "/freistellen", {"id": "20250101-000000-0000"})[0] == 404
auftrag("20260107-000000-9999", "wartet", 0)
assert rufen("POST", "/freistellen", {"id": "20260107-000000-9999"})[0] == 409
code, auf = rufen("POST", "/auftrag", {"modus": "neu", "prompt": "Ein Logo auf Weiß", "transparent": True})
assert code == 200 and b.auftrag_lesen(auf["id"])["transparent"] is True
stub.shutdown(); stub.server_close()
assert rufen("POST", "/prompt", {"text": "Ein roter Leuchtturm bei Dämmerung"})[0] == 503
print("TEST OK")
