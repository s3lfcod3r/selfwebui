# Projekt SelfMailer
- **Was:** Selbst gehosteter Mail-Client (kein Mailserver): FastAPI + SQLite in einem Docker-Container, React-Oberfläche, native Android-App, dazu Kalender, Kontakte, Notizen. GitHub: `s3lfcod3r/selfmailer` (öffentlich). Läuft auf dem Tower unter http://192.168.1.10:8090.
- **Der Code liegt an ZWEI Orten:** Server und Oberfläche in `Github SelfCoder/selfmailer` (Git-Klon, Container `/repos/selfmailer`); die **Android-App in `Android/selfmailer-app` hat kein Git** (Schlüssel `Android/selfmailer-release.jks`, `keystore.properties` daneben, nie committen).
- **Die Version steht an fünf Stellen, die zusammen geändert werden:** `APP_VERSION` in `backend/app/main.py`, README-Badge, `frontend/package.json`, Git-Tag, und `versionName` plus `versionCode` in `Android/selfmailer-app/app/build.gradle.kts`. `versionCode` muss mitsteigen. (`frontend/package-lock.json` bleibt bewusst auf 0.1.0.) Der Stand, der wirklich läuft, steht in `GET /api/health` (`APP_BUILD`).
- **Auslieferung:** Push auf `main` startet die CI (pytest, ruff, tsc), nur bei Grün baut `docker-image.yml` das Image; Unraid zieht `ghcr.io/s3lfcod3r/selfmailer:latest`. `notify-selfstore.yml` stößt SelfStore an (Katalog-App: Viewer `com.selfmailer.viewer`).
- **Nie ändern:** `SELFMAILER_SECRET` (daraus werden JWT-Schlüssel und der Schlüssel für die gespeicherten Postfach-Passwörter abgeleitet; ein Wechsel macht alle Zugangsdaten unlesbar).
- **Vor Aussagen zur Release-Version** erst `git fetch --tags` (lokale Tags sind oft veraltet).
- **APK bauen:** `docker exec AndroidBuild bauen selfmailer release` (die Toolchain liegt im Container, es gibt kein `gradlew` im Projekt).
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
