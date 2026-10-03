#!/usr/bin/env python3
"""Allgemeine Bilder mit Qwen-Image 2.1 Turbo (läuft IM Container deritler-qwen-image21, ComfyUI ist schon gestartet).

Aufruf (siehe bild_dienst.py):  qwen_entrypoint.sh /opt/bild_allgemein.py
Liest /job/auftrag.json und schreibt /job/ergebnis-<i>.png.
  modus   "neu"        Text zu Bild (breite x hoehe)
          "bearbeiten" Referenzbild /job/vorlage.<endung> nach dem Prompt umbauen (Größe folgt der Vorlage)
  prompt, seed, anzahl (1-4, seed+i), aufloesung (Encoder, Standard 1024)
"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, "/opt")
from qwen_batch import COMFY_IN, turbo_erzeugen  # noqa: E402

JOB = Path("/job")


def main():
    auftrag = json.loads((JOB / "auftrag.json").read_text(encoding="utf-8"))
    modus = auftrag.get("modus", "neu")
    anzahl = max(1, min(int(auftrag.get("anzahl", 1)), 4))
    seed = int(auftrag.get("seed", int(time.time()) % 100000000))
    aufloesung = int(auftrag.get("aufloesung", 1024))
    bilder, referenzen = [], []
    vorlage = next(iter(sorted(JOB.glob("vorlage.*"))), None)
    if modus == "bearbeiten" and vorlage is None:
        sys.exit("Modus bearbeiten, aber keine Vorlage im Auftrag")
    for i in range(anzahl):
        eintrag = {"prompt": auftrag["prompt"], "seed": seed + i, "ziel": JOB / f"ergebnis-{i}.png", "aufloesung": aufloesung}
        if modus == "bearbeiten":
            name = f"bild-ref-{i}-{int(time.time())}{vorlage.suffix}"
            shutil.copyfile(vorlage, COMFY_IN / name)
            referenzen.append(COMFY_IN / name)
            eintrag["ref_name"] = name
        else:
            eintrag["breite"] = int(auftrag.get("breite", 1024))
            eintrag["hoehe"] = int(auftrag.get("hoehe", 1024))
        bilder.append(eintrag)
    t0 = time.time()
    try:
        turbo_erzeugen(bilder)
    finally:
        for pfad in referenzen:
            pfad.unlink(missing_ok=True)
    print(f"qwen21-turbo {modus} bilder={anzahl} seed={seed} sekunden={time.time() - t0:.1f}", flush=True)


if __name__ == "__main__":
    main()
