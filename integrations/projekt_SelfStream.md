# Projekt SelfStream

- **Was:** Selbst gehosteter Streaming- und Live-TV-Dienst (Python-Backend `backend/`, Web-Frontend `frontend/`), läuft als Docker-Container `selfstream` auf der Werkstatt (Board 2) (192.168.1.14). GitHub: `s3lfcod3r/selfstream` (öffentlich). Image: `ghcr.io/s3lfcod3r/selfstream:latest`.
- **Maßgeblich ist GitHub `main`, nicht der Ordner auf F:.** Der Ordner `Github SelfCoder/selfstream` ist ein alter Stand vom 22.08.2026 ohne Git (Backend dort viel kleiner, es fehlen z. B. `epg_merge.py` und `epg_quality.py`). Nie daraus prüfen oder pushen.
- **Prüfen ohne den Ordner anzufassen:** einen flachen Klon in einen Temp-Ordner machen, z. B. `git clone --depth 1 https://github.com/s3lfcod3r/selfstream /tmp/selfstream-check`, und nur dort lesen. Nach der Prüfung bleibt der Temp-Ordner liegen oder wird gelöscht, der Ordner `selfstream` wird nie verändert. Ändern und Pushen: nur auf ausdrücklichen Auftrag von Sven.
- **Container:** läuft den Stand v1.82 (Commit 4e0b094); auf GitHub liegt seit 27.09.2026 v1.83 (gebaut, noch nicht ausgerollt). Den laufenden Container nicht anfassen, nicht neu starten.
- **Veröffentlichen später:** der Arbeitsordner ist kein Git-Klon. Dann `docker exec GitHubTool gitpush-dateien selfstream "<Nachricht>" <datei> ...` oder in einem frischen Temp-Klon arbeiten und von dort pushen. Public Repo: vor jedem Commit nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel, interne IPs in Beispielen).

## Prüfauftrag (30.09./01.10.2026)
- Container-Version komplett prüfen: Backend, Frontend, Dockerfile, `docker-compose.yml`, `selfstream.xml` (Unraid-Vorlage), `setup.sh`, `update.sh`, GitHub-Actions, README/CHANGELOG. Ziel: Fehler und Verbesserungen, nach Schwere sortiert, jeder Befund mit Datei:Zeile und Beleg.
- Frühere Funde einer anderen Durchsicht liefen gegen den alten Ordner und waren teils überholt (z. B. HSTS). Nichts aus dem Gedächtnis übernehmen, alles am aktuellen Code belegen.

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst. Im Zweifel verwerfen und das sagen.
