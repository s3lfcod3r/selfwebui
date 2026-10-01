# Projekt SelfStreamDesktop

- **Was:** Portabler **Windows-Client** für den eigenen selfstream-Proxy (Electron + React + TypeScript, Wiedergabe über ein mitgeliefertes mpv). Kanalliste, Programmraster (EPG), Catchup (Archiv), Zappen ohne Neustart. Plan und Messwerte: `docs/PLAN.md`, Sicherheit: `docs/SICHERHEIT.md`.
- **Ordner:** `/media/Safe-Storage/appdata/werkstatt/repos/selfstreamdesktop` (im Container `/repos/selfstreamdesktop`). Es ist ein Git-Ordner **ohne einen einzigen Commit und ohne Remote**: das Projekt ist noch nirgends veröffentlicht, auch nicht auf GitHub. Der Ordner enthält `node_modules`, `out`, `dist`, `vendor` (diese stehen in der `.gitignore`).
- **Nie:** den Ordner verschieben, ersetzen, klonen oder löschen. Kein `git init`, kein erster Commit, kein neues GitHub-Repo und kein Push ohne ausdrücklichen Auftrag von Sven (Sichtbarkeit privat oder öffentlich entscheidet Sven).
- **Wichtig, Datenschutz:** `C:\Windows`-Pfade und `C:\SelfStream\data` (Einstellungen, Playlist-Token, EPG-Zwischenspeicher) gehören Sven und sind für dich nicht erreichbar. Nie nach Zugangsdaten suchen, nie ein Token in Ausgaben, Dateien oder Tests schreiben. Vor einem späteren ersten Commit nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel, interne Adressen).
- **Was du hier kannst und was nicht:** Du arbeitest auf der Werkstatt (Board 2) unter Linux. Lesen, Code prüfen, `npm run lint`, `npm run typecheck` und `npm test` (vitest) kannst du in einem Wegwerf-Container mit Node 22 oder neuer ausführen (`docker run --rm`, Ordner nur lesend einbinden und in einen Temp-Ordner kopieren, damit `node_modules` des Ordners unberührt bleibt). Das Windows-Paket (`npm run package`, `electron-builder --win`) und das Starten der App kannst du **nicht**: das baut und testet Sven auf seinem PC. Der Entwicklungsmodus (`npm run dev`) startet auf Svens PC wegen eines GPU-Fehlers nicht; geprüft wird über die gepackte EXE.
- **Bau-Ablauf auf Svens PC (zur Info):** `npm install`, `npm run fetch:mpv`, `npm run package`. Das Skript `fetch:mpv` prüft die Summe von mpv und bricht sonst ab.
- **Verwandt:** Das Backend `selfstream` ist ein eigener Arbeitsbereich (GitHub `s3lfcod3r/selfstream`). Die EPG-Reparatur für Doppelspuren sitzt im Backend, nicht im Client.

## Bekannte Punkte
- Version 0.1.0 (21.08.2026), 51 TypeScript-Dateien, Abhängigkeit zur Laufzeit nur `saxes`.
- Noch kein Commit, kein Remote, keine CI. Veröffentlichen heißt: Repo anlegen, ersten Commit machen, Releases mit der Portable-EXE.

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
