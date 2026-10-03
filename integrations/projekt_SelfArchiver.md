# Projekt SelfArchiver
- **Was:** Selbst gehosteter E-Mail-Archivierer: regelbasiert per IMAP in einen einzigen SQLite-Container archivieren, optional mit Löschen nach dem Archivieren. Docker (Node). GitHub: `s3lfcod3r/selfarchiver` (öffentlich, letzter Push 02.07.2026).
- **Prüfbefehl:** `docker run --rm --memory 2g -v /media/Safe-Storage/appdata/werkstatt/repos/selfarchiver:/src:ro node:22-bookworm-slim bash -c 'set -o pipefail; mkdir /w && cd /src && tar cf - --exclude=node_modules --exclude=out --exclude=.next --exclude=dist . | tar xf - -C /w && cd /w && npm install --no-audit --no-fund --loglevel=error --ignore-scripts >/dev/null 2>&1 || { echo "npm install fehlgeschlagen"; exit 1; }; npm run typecheck 2>&1 | tail -15; typecheck=${PIPESTATUS[0]}; echo "typecheck=$typecheck"; exit $(($typecheck))'`
- **Arbeitsordner:** `Github SelfCoder/selfarchiver` (Container `/repos/selfarchiver`), **ohne Git**: die lokale Kopie kann vom GitHub-Stand abweichen. **Maßgeblich ist GitHub `main`.** Zum Prüfen flach in einen Temp-Ordner klonen (`git clone --depth 1 https://github.com/s3lfcod3r/selfarchiver /tmp/selfarchiver-check`); den Ordner nie verändern.
- **Veröffentlichen:** `docker exec GitHubTool gitpush-dateien selfarchiver "<Nachricht>" <datei> ...` (überträgt nur die genannten Dateien). `docker.yml` baut das Image.
- **Version:** `package.json` (1.0.0 am 01.10.2026), README, CHANGELOG, falls vorhanden.
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
