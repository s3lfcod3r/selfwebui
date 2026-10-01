# Projektregeln RTX2000 (Bonsai allein)

- Projekte liegen unter `/mnt/user/Privat/09_Cloude/Github SelfCoder/<projekt>` auf dem Tower. GitHub-Repos dorthin klonen, wenn lokal nichts vorhanden ist (`git clone https://github.com/s3lfcod3r/<name>`).
- Auf dem Tower sind keine GitHub-Zugangsdaten hinterlegt: pushen geht nicht. Lokal committen, Push macht Sven.
- Android/Kotlin lässt sich auf dem Tower nicht bauen. Solche Änderungen nur lesen, ändern, per `git diff` belegen und den fehlenden Build ausdrücklich melden.
- Bei Projektarbeit die `STATUS.md` im Projektordner aktuell halten: Abschnitt "## Aufgaben" (`- Aufgabe — in Arbeit: Stand` bzw. `- Aufgabe — fertig: überprüftes Ergebnis`) und "## Offene Fragen". Bestehende Inhalte erhalten, nichts als fertig markieren, was nicht belegt ist.
- Neue Apps nicht in bestehende Self-Projekte einbauen, eigenständig anlegen.
- **Git auf den Shares immer als Nutzer nobody ausführen:** `runuser -u nobody -- git -C '<pfad>' <befehl>` (Commit, Checkout, Branch usw.). Läuft git als root, gehören neue Dateien in `.git` root, und der Container GitHubTool (Nutzer 99) kann dann nicht mehr pushen oder pullen. Ist es passiert: `chown -R 99:100 '<klon>'`, dann weitermachen.

## Apps bauen (AndroidBuild-Container auf dem Tower)
- Bauen: `docker exec AndroidBuild bauen <projekt> <release|debug> [quellordner]` über `heim_befehl_tower` mit `timeout` 600. Beispiele: `bauen selfwg debug /repos/selfwg` (Klon mit ungepushten Änderungen kompilieren), `bauen selfwg release` (echte App aus `Android/selfwg-app`, signiert).
- Klone liegen im Container unter `/repos/<name>`, die App-Quellen unter `/android/<name>-app`. Ergebnis (APK, SHA-256, Signatur) steht in der Ausgabe und in `/mnt/user/Privat/09_Cloude/Github SelfCoder/Android/_apk-out/<projekt>/`.
- Schlägt der Bau fehl, zeigt die Ausgabe die Fehlerzeilen (`e: Datei:Zeile: Meldung`). Lies die Stelle, korrigiere sie mit `datei_ersetzen`, baue erneut. Höchstens 5 Versuche, dann berichte den Stand.
- Ein Release ist nur gültig, wenn "Verifies" und der Zertifikats-Fingerabdruck (SHA-256) zum bisher veröffentlichten Release passt (bei SelfWG `a22e4d33…`). Nie einen anderen Schlüssel als den aus `keystore.properties` verwenden.
- Veröffentlichen (push, GitHub-Release, APK-Upload) macht Claude vom PC aus, nicht du.

## Release veröffentlichen (GitHubTool-Container)
Nur auf ausdrücklichen Auftrag von Sven ("Release", "veröffentliche"), nie von selbst. Vorher `docker exec GitHubTool githubstatus`: zeigt es keinen Konto-Namen, fehlt das Token, dann melden und stoppen (nur Sven legt es ab).
Ablauf für Version X.Y.Z im Klon `Github SelfCoder/<name>` (Container-Pfad `/repos/<name>`), jeder Schritt mit Beleg:
1. `versionName` und `versionCode` (+1) in `app/build.gradle.kts` und das Versions-Badge in `README.md` anheben, lokal committen (`chore: bump auf X.Y.Z`).
2. Gegenprüfung (siehe unten, `diffpruefen`), dann `docker exec GitHubTool gitpush <name>` (pusht nur fast-forward, nie force).
3. `docker exec AndroidBuild bauen <name> release /repos/<name>` (timeout 600). Es muss "Verifies", "Zertifikat stimmt mit der letzten Veröffentlichung überein" und "FERTIG" erscheinen. Sonst nicht veröffentlichen.
4. Erst `docker exec GitHubTool veroeffentlichen <name> vX.Y.Z /out/<name>/<name>-vX.Y.Z.apk "<Notizen>" --trocken`, dann ohne `--trocken`. Notizen ehrlich: was sich geändert hat und was nicht auf einem Gerät getestet wurde.
5. Ergebnis melden: Release-Link, SHA-256, ob der SelfStore-Abgleich sauber lief.
Schlägt ein Schritt fehl: Ausgabe lesen, Ursache nennen, nichts erzwingen (kein force, kein Überschreiben von Releases).

## Mit Sven reden: Auswahl statt Fragen (Pflicht)
Sven will keine langen Texte schreiben. Darum:
- Wenn eine Entscheidung offen ist, stelle **keine offene Frage**, sondern biete **2 bis 4 nummerierte Varianten** an (1, 2, 3 …), jede in einem Satz, mit den Folgen. Markiere deine Empfehlung mit "(Empfehlung)" und sie steht an Platz 1. Sven antwortet dann nur mit "1", "2" oder "ja".
- Am Ende jeder Antwort, die auf eine Entscheidung wartet: genau **eine** Frage, kurz, mit den Nummern. Nicht mehrere Fragen auf einmal.
- Kurzantworten verstehst du so: "ja", "ok", "mach" = die Empfehlung ausführen. "1"/"2"/"3" = diese Variante. "weiter" = den nächsten Schritt deines Plans. "stopp" = sofort anhalten und den Stand melden. "pushen" oder "push frei" = ausdrücklicher Auftrag zum Pushen (nur für das gerade besprochene Projekt).
- **Nach einem Fehler:** Sagt Sven "weiter" und der letzte Lauf endete mit einem Fehler (die Arbeiter-Spalte zeigt ihn rot), dann: 1. Stand mit den Werkzeugen prüfen (git status und git log, Dateien), bevor du etwas wiederholst. 2. Die Ursache kurz analysieren und beheben, ohne zurückzufragen. 3. Dort weitermachen, wo du aufgehört hast. Tritt derselbe Fehler wieder auf, beschreibe ihn genau und höre auf.
- Für Push und Release gilt trotzdem: nur nach einem solchen ausdrücklichen Wort von Sven. Bei Unklarheit nachfragen mit Varianten, nicht raten.
- Berichte kurz: erst das Ergebnis in 2 bis 4 Zeilen, dann Belege. Danach die eine Frage mit Varianten, falls etwas offen ist.

## Arbeitsordner niemals ersetzen (Pflicht)
- Projektordner unter `Github SelfCoder/<name>` sind Svens Arbeitsstand. **Nie** verschieben, umbenennen, ersetzen, löschen und **keinen Klon an ihre Stelle setzen** (kein `mv`, kein `rm -rf`, kein `git clone` in diesen Ordner). Arbeite direkt in dem Ordner, den Sven nennt.
- Ist der Ordner **kein** Git-Klon (kein `.git`) oder weicht er vom GitHub-Stand ab (steht in `PROJEKT.md`), veröffentlichst du nur so: `docker exec GitHubTool gitpush-dateien <name> "<Commit-Nachricht>" <datei1> <datei2> ...` (Pfade relativ zum Projektordner). Es überträgt nur die genannten Dateien als einen Commit, löscht nie etwas und ändert den Arbeitsordner nicht. Den Bericht "Entfernte Zeilen" danach im Bericht begründen.
- Pushen nur auf ausdrücklichen Auftrag von Sven.

## Gegenprüfung vor jedem Push (Pflicht)
Kleine Modelle löschen gelegentlich ungewollt Code oder erfinden Befunde. Darum vor jedem `gitpush`:
1. `docker exec GitHubTool diffpruefen <name>` ausführen (`gitpush` zeigt denselben Bericht selbst noch einmal).
2. **Jede entfernte Zeile** aus dem Bericht einzeln begründen: Warum gehört das Entfernen zum Auftrag? Kannst du es nicht begründen, stelle die Zeile wieder her und committe erneut.
3. Prüfe, ob die Änderung genau den Befund oder Auftrag umsetzt, nicht mehr und nicht weniger.
4. Der Bau muss grün sein, sonst kein Push.
5. Befunde aus Prüfungen nur umsetzen, wenn du sie am Code belegen kannst (Datei:Zeile, was genau dort steht). Erfundene Regeln oder API-Namen sind ein Fehler: im Zweifel den Befund verwerfen und das melden.
Im Bericht am Ende: Liste der entfernten Zeilen mit Begründung.
