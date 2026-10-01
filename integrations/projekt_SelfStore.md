# Projekt SelfStore
- **Was:** Selbst gehosteter App-Store als statische Seite (store.selfcoder.de) mit Katalog `catalog.json` und der Bootstrap-APK `selfstore.apk`; eigene Android-App SelfStore (`com.selfstore.app`). GitHub: `s3lfcod3r/selfstore` (öffentlich).
- **Arbeitsordner:** `/mnt/user/Privat/09_Cloude/Github SelfCoder/selfstore` (Container `/repos/selfstore`), Git-Klon, am 01.10.2026 **7 Commits hinter GitHub**: zuerst `docker exec GitHubTool gitpull selfstore`. Die Android-App liegt in `Android/selfstore-app` (kein Git, Schlüssel `Android/selfstore-release.jks`).
- **Katalog:** `.github/workflows/sync-catalog.yml` aktualisiert `catalog.json` und `selfstore.apk` selbst (alle 15 Minuten und nach Releases) und committet als "chore: Katalog Auto-Sync". Darum **immer erst `gitpull`**, und die Versionen in `catalog.json` **nie von Hand ändern**. `ensure-latest.yml` setzt die höchste Version als "Latest". Neue Apps trägt Sven von Hand ein.
- **Katalog-Apps:** SelfStore, SelfMailer, SelfAuthenticator, SelfDashboard (Viewer), SelfPoolTracker, SelfWG, SelfGuard, SelfRemote.
- **Version der App:** `versionCode`/`versionName` in `Android/selfstore-app/app/build.gradle.kts`.
- **Wichtig:** `SignerPins.kt` (Signaturprüfung) hatte bis 1.5.3 einen Fehler auf billigen Geräten (nur v2/v3, kein Rückfall auf v1). Alle APKs müssen v1, v2 und v3 tragen.
- **Nie:** den Arbeitsordner verschieben, ersetzen, klonen oder löschen. Kein Push und kein Release ohne ausdrücklichen Auftrag von Sven. Nach Zugangsdaten suchen (Passwörter, Tokens, Schlüssel), bevor etwas veröffentlicht wird. Keine Schlüsseldateien (`*.jks`, `keystore.properties`) committen.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
