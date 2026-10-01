# Projekt SelfStorm

- **Was:** Wetter- und Unwetter-Warnseite mit Deutschlandkarte, live unter https://wetter.selfcoder.de (statische Seite über GitHub Pages, `CNAME`). GitHub: `s3lfcod3r/selfstorm`.
- **Arbeitsordner:** `/media/Safe-Storage/appdata/werkstatt/repos/selfstorm` (im Container `/repos/selfstorm`). Es ist ein echter Git-Klon, stand am 30.09.2026 aber **96 Commits hinter GitHub** (BBK-Code fehlte). Zuerst `docker exec GitHubTool gitpull selfstorm`. Die Datei `mockup-redesign.html` ist untracked und von Sven: nicht löschen, nicht pushen.
- **Nie:** den Ordner verschieben, ersetzen oder klonen. Nur dort arbeiten.
- **Aufbau:** `index.html`, `karte.html` (Karte), `map/` (Raster, Gemeinden, GeoJSON), `warner/` (`check.mjs`, `config.json`, `state.json`), BBK: `bbk.js`, `bbk-geo.js`, `bbk-view.js`, `bbk.css`, Tests in `tests/*.cjs` (`node tests/bbk.cjs` usw.). Actions: `.github/workflows/karte.yml` (Raster), `waechter.yml` (Warner).
- **Auto-Commits:** Die Actions committen selbst (`chore(karte): Raster aktualisiert [skip ci]`, `warner/state.json`). Diese Dateien nie von Hand ändern, vor einem Push immer `gitpull`.
- **Veröffentlichen:** Push auf `main` (`gitpush selfstorm`) veröffentlicht die Seite. Nur auf ausdrücklichen Auftrag von Sven.

## Bekannte offene Punkte (belegt, 30.09.2026)
- **BBK nicht abrufbar:** `bbk.js:63` und `bbk-geo.js:81` rufen `https://warnung.bund.de/api31/...` direkt im Browser ab. Die Schnittstelle sendet keinen `Access-Control-Allow-Origin`-Header (mit `curl` und im Browser von wetter.selfcoder.de geprüft: "Failed to fetch"). Darum zeigt die Seite "BBK nicht abrufbar". Geplanter Fix: GitHub-Action spiegelt `mapData.json` und die Geometrien aktiver Warnungen alle 10 bis 15 Minuten ins Repo, die Seite lädt sie von der eigenen Domain.

## Gelernt (nicht wiederholen)
- Die Kopie dieses Projekts war lokal veraltet, weil niemand `git pull` gemacht hatte: immer erst `gitpull`, dann arbeiten.
