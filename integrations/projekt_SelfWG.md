# Projekt SelfWG

- **Was:** Android-WireGuard-Client (Kotlin/Compose) mit Auto-Reconnect-Wächter, der die tägliche IP-Änderung des Providers übersteht. Split-Tunnel pro App, mehrere Tunnel, Fingerabdruck-Sperre. GitHub: `s3lfcod3r/selfwg`.
- **Klon zum Arbeiten:** `/media/Safe-Storage/appdata/werkstatt/repos/selfwg` (im Container `/repos/selfwg`). Der echte App-Ordner mit Schlüssel ist `Github SelfCoder/Android/selfwg-app`; den aktualisiert Sven selbst per `git pull`.
- **Stand:** v1.2.5 (versionCode 8), veröffentlicht. Zertifikat-Fingerabdruck (SHA-256) `a22e4d33…a22b`, Referenz in `Android/_apk-out/selfwg/cert-sha256.txt`.
- **Version:** `versionCode`/`versionName` in `app/build.gradle.kts` (Zeile ca. 29/30), Badge in `README.md` (Zeile 9).
- **Bauen:** `docker exec AndroidBuild bauen selfwg <debug|release> /repos/selfwg`. Release nur mit `keystore.properties` (liegt in `Android/selfwg-app`), sonst bricht der Bau ab.
- **Wichtige Dateien:** `vpn/SelfWgService.kt` (Wächter, Alarm), `vpn/TunnelManager.kt` (Tunnel), `data/TunnelStore.kt` (verschlüsselte Ablage), `MainActivity.kt` + `ui/LockScreen.kt` (Sperre), `ui/AppScreen.kt` (Anzeige).

## Bekannte offene Punkte (belegt)
- `isMinifyEnabled = false` im Release (`app/build.gradle.kts`): APK ist unverschleiert.
- Der Wächter erkennt einen Tunnel, der als verbunden gilt, aber keinen Handshake mehr hat, nicht (er prüft nur IP-Wechsel und den Zustand).
- `WgFields.build` schreibt `PrivateKey`/`PublicKey` auch leer (`data/WgFields.kt` Zeilen 61 und 67): harmlos, nur die Fehlermeldung ist allgemein.
- **Nicht auf einem Gerät getestet:** Sperre ohne Gerätesperre, Fehleranzeige mit Fehlerart, Wächter-Schleife im Alarm-Pfad.

## Gelernt (nicht wiederholen)
- `FOREGROUND_SERVICE_SPECIAL_USE` ist eine normale Berechtigung und steht im Manifest. Es gibt keine Laufzeit-Anfrage dafür und keinen Absturz auf Android 14 deswegen. Ein früherer Befund war erfunden.
- Im Zweig `ACTION_CHECK` muss `scope.launch { watchTick() }` bleiben (sofortiger Check beim Alarm). Eine Änderung hatte die Zeile ungewollt gelöscht.
