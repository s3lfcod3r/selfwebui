import json, os, sys, time, tempfile
from pathlib import Path

daten = tempfile.mkdtemp()
os.environ.update(BILD_DATEN=daten, BILD_TROCKEN="1", PRODUKTIONS_LOCK=daten + "/x.lock")
sys.path.insert(0, "/code")
import bild_dienst as b

jetzt = time.time()
tag = 86400


def auftrag(name, zustand, alter_tage):
    ordner = Path(daten) / "jobs" / name
    ordner.mkdir(parents=True)
    (ordner / "ergebnis-0.png").write_bytes(b"x")
    (ordner / "status.json").write_text(json.dumps({"zustand": zustand, "geaendert": int(jetzt - alter_tage * tag)}))


auftrag("alt-fertig", "fertig", 31)
auftrag("alt-fehler", "fehler", 45)
auftrag("neu-fertig", "fertig", 5)
auftrag("grenze-fertig", "fertig", 29)
auftrag("alt-rechnet", "rechnet", 40)   # läuft angeblich noch: bleibt immer
alt = Path(daten) / "vorlagen" / "alt.png"
alt.write_bytes(b"x"); os.utime(alt, (jetzt - 31 * tag, jetzt - 31 * tag))
neu = Path(daten) / "vorlagen" / "neu.png"
neu.write_bytes(b"x")

anzahl = b.aufraeumen(jetzt)
uebrig = sorted(p.name for p in (Path(daten) / "jobs").iterdir())
vorlagen = sorted(p.name for p in (Path(daten) / "vorlagen").iterdir())
print("geloescht:", anzahl)
print("Aufträge übrig:", uebrig)
print("Vorlagen übrig:", vorlagen)
assert anzahl == 3, anzahl
assert uebrig == ["alt-rechnet", "grenze-fertig", "neu-fertig"], uebrig
assert vorlagen == ["neu.png"], vorlagen
print("TEST OK")
