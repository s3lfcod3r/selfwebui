# Projekt SelfAuthenticator
- **Was:** Selbst gehosteter Zero-Knowledge-2FA/TOTP-Tresor (Argon2id + XChaCha20-Poly1305), Docker-Container. GitHub: `s3lfcod3r/selfauthenticator` (öffentlich).
- **Arbeitsordner:** `Github SelfCoder/selfauthenticator` (Git-Klon, Container `/repos/selfauthenticator`). Die Android-App (Viewer, `com.selfauthenticator.viewer`) liegt in `Android/selfauth-app` ohne Git; Schlüssel unter `Android/` (selfauth).
- **Auslieferung:** `docker.yml` baut das Image beim Push; `notify-selfstore.yml` stößt SelfStore an. Sicherheitsprojekt: bei jeder Änderung am Verschlüsselungscode besonders sorgfältig prüfen und nichts am Format der gespeicherten Daten ändern, ohne Sven zu fragen.
- **Version:** Stellen in Backend, README-Badge und `versionName`/`versionCode` der App ermitteln und hier eintragen (bei der ersten Prüfung).
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
