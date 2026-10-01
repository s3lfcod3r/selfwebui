# Projekt SelfRemote
- **Was:** Eigene Fernwartung: Go-Server als Container (Oberfläche, Vermittlung, SQLite), Windows-Agent als einzelne .exe, Android-Agent (`de.selfcoder.selfremote`). Der Agent ruft **ausgehend** per WebSocket an, es braucht keine Portfreigabe. Nur Administratoren dürfen fernsteuern (serverseitig in `requireAdmin`). GitHub: `s3lfcod3r/SelfRemote` (öffentlich). Läuft auf dem ZimaBoard über https://remote.ss-its.de.
- **Arbeitsordner:** `Github SelfCoder/selfremote` (Git-Klon, Container `/repos/selfremote`); der Android-Teil liegt darin unter `android/` (Modul `android/app/build.gradle.kts`).
- **Version der Android-App:** `versionCode` und `versionName` in `android/app/build.gradle.kts` (Quelltext am 01.10.2026: 7 / 0.7.0). **Der Katalog zeigt versionCode 4:** prüfen, ob für 0.5 bis 0.7 ein Release mit APK fehlt (nicht von dir veröffentlichen, Sven fragen). Der Server ist ein Docker-Image (Dockerfile im Repo), ausgerollt von Sven.
- **Bauen:** Go-Server und Windows-Agent lassen sich im Linux-Container cross-kompilieren (kein CGO). Den Windows-Agent kannst du nicht starten oder testen, das macht Sven (auf seinem Entwicklungs-PC blockiert Smart App Control unsignierte .exe).
- **Kein `notify-selfstore.yml`** im Repo: ein Release erscheint im Katalog erst beim 15-Minuten-Sync.
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
