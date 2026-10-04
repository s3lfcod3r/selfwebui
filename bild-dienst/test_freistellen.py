"""Test des Freistellens mit einem künstlichen Logo (Ring mit Loch auf Weiß).

Aufruf auf dem Board:
  docker run --rm -v <ordner>:/code -w /code deritler-freistellen:local python3 test_freistellen.py
"""
import cv2
import numpy as np

import freistellen_allgemein as f

bild = np.full((400, 400, 3), 255, np.uint8)
cv2.circle(bild, (200, 200), 120, (140, 167, 51), -1, cv2.LINE_AA)      # Ring (Teal, BGR)
cv2.circle(bild, (200, 200), 60, (255, 255, 255), -1, cv2.LINE_AA)       # Loch in der Mitte, weiß und eingeschlossen
cv2.rectangle(bild, (190, 40), (210, 70), (40, 40, 40), -1)               # dunkler Block oben
cv2.circle(bild, (30, 30), 3, (140, 167, 51), -1)                          # Krümel, soll verschwinden

rgba, deckend, hg = f.freistellen(bild)
h, w = rgba.shape[:2]
a = rgba[..., 3]
assert list(hg) == [255, 255, 255], hg
assert (w, h) == (w, h) and w < 400 and h < 400, (w, h)                  # zugeschnitten
assert a[0, 0] == 0 and a[-1, -1] == 0, "Ecke muss durchsichtig sein"
assert a[h // 2, w // 2] == 0, "Loch in der Mitte muss durchsichtig sein"
assert a[h // 2, w // 2 + 90] == 255, "Ring muss deckend sein"
assert 0.05 < deckend < 0.5, deckend
kante = a[h // 2, :]
assert any(0 < v < 255 for v in kante.tolist()), "weiche Kante erwartet"
sauber = rgba[h // 2, w // 2 + 90, :3].tolist()
assert abs(sauber[0] - 140) < 6 and abs(sauber[1] - 167) < 6, sauber       # Farbe im Ring bleibt unverändert
ohne_zuschnitt, _, _ = f.freistellen(bild, zuschneiden=False)
assert ohne_zuschnitt.shape[:2] == (400, 400)
# Krümel oben links ist weg (im Zuschnitt nicht mehr enthalten, ohne Zuschnitt durchsichtig)
assert ohne_zuschnitt[30, 30, 3] == 0, "Krümel muss entfernt sein"
print("TEST OK")
