# Projekt SelfPoolTracker
- **Was:** Poolwerte (pH, Chlor u. a.) verfolgen, "local-first" als Ein-Datei-Web-App; live unter pool.selfcoder.de. GitHub: `s3lfcod3r/selfpooltracker` (öffentlich). Dazu eine Android-App (`com.selfpooltracker.app`).
- **Arbeitsordner:** `Github SelfCoder/selfpooltracker` (Git-Klon, Container `/repos/selfpooltracker`). Die Android-App liegt in `Android/selfpooltracker-app` **ohne Git**, Schlüssel `Android/selfpooltracker-release.jks`.
- **Auslieferung:** Web: Push auf `main`. APK: Version und `versionCode` in der App erhöhen, `docker exec AndroidBuild bauen selfpooltracker release`, Release auf GitHub; `notify-selfstore.yml` stößt SelfStore an.
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
