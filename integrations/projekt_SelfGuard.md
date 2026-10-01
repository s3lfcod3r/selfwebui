# Projekt SelfGuard
- **Was:** Android-App mit DNS-Filter (`com.selfguard.app`), bewusst eigenständig und nicht in SelfWG eingebaut. GitHub: `s3lfcod3r/selfguard` (öffentlich). Katalog-App im SelfStore.
- **Arbeitsordner:** Der Quellordner liegt **nicht** unter `Github SelfCoder`, sondern in `Github SelfCoder/Android/selfguard-app` (Git-Klon, enthält `app/`, `worker/`, `keystore.properties`, `docs/`). Release-Schlüssel `Android/selfguard-release.jks`. **`keystore.properties` enthält Klartext-Passwörter und darf nie committet oder ausgegeben werden.**
- **Bauen:** `docker exec AndroidBuild bauen selfguard release` (Fingerabdruck und Signatur wie bei den anderen Apps prüfen).
- **Wichtig:** `gitpush` und `gitpush-dateien` nehmen nur Ordner direkt unter `/repos`. Für diesen Ordner (`/repos/Android/selfguard-app`) funktioniert das Veröffentlichen mit den heutigen Werkzeugen nicht: melde es Sven, statt Umwege zu bauen.
- **Version:** `versionCode`/`versionName` in `app/build.gradle.kts`; nach einem Release im SelfStore-Katalog prüfen (am 01.10.2026: versionCode 7).
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
