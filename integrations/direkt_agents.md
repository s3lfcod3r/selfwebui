# Projektregeln RTX2000 (Bonsai allein)

- Projekte liegen unter `/mnt/user/Privat/09_Cloude/Github SelfCoder/<projekt>` auf dem Tower. GitHub-Repos dorthin klonen, wenn lokal nichts vorhanden ist (`git clone https://github.com/s3lfcod3r/<name>`).
- Auf dem Tower sind keine GitHub-Zugangsdaten hinterlegt: pushen geht nicht. Lokal committen, Push macht Sven.
- Android/Kotlin lässt sich auf dem Tower nicht bauen. Solche Änderungen nur lesen, ändern, per `git diff` belegen und den fehlenden Build ausdrücklich melden.
- Bei Projektarbeit die `STATUS.md` im Projektordner aktuell halten: Abschnitt "## Aufgaben" (`- Aufgabe — in Arbeit: Stand` bzw. `- Aufgabe — fertig: überprüftes Ergebnis`) und "## Offene Fragen". Bestehende Inhalte erhalten, nichts als fertig markieren, was nicht belegt ist.
- Neue Apps nicht in bestehende Self-Projekte einbauen, eigenständig anlegen.

## Apps bauen (AndroidBuild-Container auf dem Tower)
- Bauen: `docker exec AndroidBuild bauen <projekt> <release|debug> [quellordner]` über `heim_befehl_tower` mit `timeout` 600. Beispiele: `bauen selfwg debug /repos/selfwg` (Klon mit ungepushten Änderungen kompilieren), `bauen selfwg release` (echte App aus `Android/selfwg-app`, signiert).
- Klone liegen im Container unter `/repos/<name>`, die App-Quellen unter `/android/<name>-app`. Ergebnis (APK, SHA-256, Signatur) steht in der Ausgabe und in `/mnt/user/Privat/09_Cloude/Github SelfCoder/Android/_apk-out/<projekt>/`.
- Schlägt der Bau fehl, zeigt die Ausgabe die Fehlerzeilen (`e: Datei:Zeile: Meldung`). Lies die Stelle, korrigiere sie mit `datei_ersetzen`, baue erneut. Höchstens 5 Versuche, dann berichte den Stand.
- Ein Release ist nur gültig, wenn "Verifies" und der Zertifikats-Fingerabdruck (SHA-256) zum bisher veröffentlichten Release passt (bei SelfWG `a22e4d33…`). Nie einen anderen Schlüssel als den aus `keystore.properties` verwenden.
- Veröffentlichen (push, GitHub-Release, APK-Upload) macht Claude vom PC aus, nicht du.
