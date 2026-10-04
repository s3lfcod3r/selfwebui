#!/usr/bin/env python3
"""Hintergrund einfarbiger Bilder entfernen (Logos, Icons, Produkte, Figuren auf einfarbigem Grund) -> PNG mit Transparenz.

Läuft im Mini-Image deritler-freistellen:local (nur numpy + OpenCV, keine GPU).
Aufruf: freistellen_allgemein.py <eingabe> <ausgabe.png> [zuschneiden=1]

Verfahren: Hintergrundfarbe aus dem Bildrand (Median). Hintergrund ist, was dem Randton ähnelt UND vom Rand aus erreichbar ist;
eingeschlossene Flächen (Loch im "O", Henkel) werden entfernt, wenn sie sehr genau den Randton haben. An der Kante läuft
die Deckkraft weich mit dem Farbabstand, und die Hintergrundfarbe wird aus den Randpixeln herausgerechnet (keine weißen Säume).
"""
import sys

import cv2
import numpy as np

RAND_PX = 6
T_RAND = 20          # bis zu diesem Farbabstand gilt ein randverbundenes Pixel als Hintergrund
T_INSEL = 12         # eingeschlossene Flächen: strenger
INSEL_MIN = 120      # kleinste eingeschlossene Fläche in Pixeln, die entfernt wird
T_VOLL = 70          # ab diesem Abstand ist die Kante voll deckend
KRUEMEL_MAX = 40     # freistehende Vordergrund-Krümel bis zu dieser Fläche fliegen raus
RAND_ZUGABE = 12     # Rand um das Motiv beim Zuschneiden


def freistellen(bgr, zuschneiden=True):
    h, w = bgr.shape[:2]
    rand = np.concatenate([bgr[:RAND_PX].reshape(-1, 3), bgr[-RAND_PX:].reshape(-1, 3),
                           bgr[:, :RAND_PX].reshape(-1, 3), bgr[:, -RAND_PX:].reshape(-1, 3)])
    hg = np.median(rand, axis=0)
    f = bgr.astype(np.float32)
    d = np.abs(f - hg).max(axis=2)

    # Hintergrund vom Rand aus
    _, lab = cv2.connectedComponents((d <= T_RAND).astype(np.uint8), connectivity=4)
    rand_labels = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    rand_labels = rand_labels[rand_labels != 0]
    aussen = np.isin(lab, rand_labels)

    # eingeschlossene, sehr hintergrundähnliche Flächen (Löcher)
    n, lab2, stat, _ = cv2.connectedComponentsWithStats(((d <= T_INSEL) & ~aussen).astype(np.uint8), connectivity=4)
    insel = np.zeros_like(aussen)
    for i in range(1, n):
        if stat[i, cv2.CC_STAT_AREA] >= INSEL_MIN:
            insel |= lab2 == i
    hintergrund = aussen | insel

    # weiche Kante: nur im schmalen Ring um den Hintergrund
    ring = cv2.dilate(hintergrund.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(bool) & ~hintergrund
    alpha = np.where(hintergrund, 0.0, 1.0).astype(np.float32)
    alpha[ring] = np.clip((d[ring] - T_RAND * 0.5) / (T_VOLL - T_RAND * 0.5), 0.0, 1.0)

    # Krümel entfernen
    n, lab3, stat, _ = cv2.connectedComponentsWithStats((alpha > 0.5).astype(np.uint8), connectivity=8)
    for i in range(1, n):
        if stat[i, cv2.CC_STAT_AREA] <= KRUEMEL_MAX:
            alpha[lab3 == i] = 0.0
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.6)
    alpha[hintergrund & (alpha < 0.02)] = 0.0

    # Hintergrundfarbe aus den teiltransparenten Pixeln herausrechnen
    farbe = f.copy()
    teil = (alpha > 0.0) & (alpha < 1.0)
    a3 = np.clip(alpha, 0.08, 1.0)[..., None]
    farbe[teil] = np.clip((f[teil] - (1.0 - a3[teil]) * hg) / a3[teil], 0, 255)

    rgba = np.dstack([farbe.astype(np.uint8), np.clip(alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)])
    if zuschneiden:
        ys, xs = np.nonzero(rgba[..., 3] > 8)
        if len(ys):
            y0, y1 = max(0, ys.min() - RAND_ZUGABE), min(h, ys.max() + 1 + RAND_ZUGABE)
            x0, x1 = max(0, xs.min() - RAND_ZUGABE), min(w, xs.max() + 1 + RAND_ZUGABE)
            rgba = rgba[y0:y1, x0:x1]
    deckend = float((rgba[..., 3] > 127).mean())
    return rgba, deckend, hg


def main():
    if len(sys.argv) < 3:
        sys.exit("Aufruf: freistellen_allgemein.py <eingabe> <ausgabe.png> [zuschneiden=1]")
    bild = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
    if bild is None:
        sys.exit("Bild nicht lesbar: " + sys.argv[1])
    rgba, deckend, hg = freistellen(bild, zuschneiden=(sys.argv[3] != "0") if len(sys.argv) > 3 else True)
    cv2.imwrite(sys.argv[2], rgba)
    print(f"freigestellt {rgba.shape[1]}x{rgba.shape[0]} deckend={deckend:.2f} hintergrund_bgr={[int(x) for x in hg]}", flush=True)


if __name__ == "__main__":
    main()
