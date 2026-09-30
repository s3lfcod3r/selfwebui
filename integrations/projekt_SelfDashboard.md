# Projekt SelfDashboard

- **Was:** Selbst gehostetes Homelab-Dashboard (Next.js 15, TypeScript, Docker), Plugin-System mit `plugins-pack/` und `src/builtin-plugins/`, mehrere Benutzer, 2FA. GitHub: `s3lfcod3r/selfdashboard`. Läuft auf dem Tower unter http://192.168.1.21:3000.
- **Maßgebliche Arbeitskopie:** `/mnt/user/Privat/09_Cloude/Github SelfCoder/selfdashboard`. Sie hat **keine** Git-Historie und ist neuer als GitHub (Stand GitHub: 24.09.2026). Nie darin `git init` oder `git push` ausführen.
- **Vor jeder Änderung:** frisch von GitHub klonen (Temp-Ordner), die Datei der Arbeitskopie per `git hash-object` gegen den Blob im Klon prüfen. Ein einfacher Dateivergleich täuscht: der Klon hat CRLF, die Arbeitskopie LF.
- **Arbeiten:** direkt im Ordner `selfdashboard` (Container `/repos/selfdashboard`). Ihn **nie** verschieben, ersetzen oder klonen. `selfdashboard-klon` daneben ist ein alter Klon und wird nicht benutzt.
- **Veröffentlichen:** `docker exec GitHubTool gitpush-dateien selfdashboard "<Nachricht>" <datei> ...` (nur die geänderten Dateien; der Ordner ist kein Git-Klon). `plugins-pack/plugins-index.json` und `README.md` sind gesperrt.

## Nie tun
- **`plugins-pack/plugins-index.json` und die Wurzel-`README.md` aus der Arbeitskopie nie pushen.** Der lokale Baum ist veraltet, der Push würde Plugins aus dem Store löschen. Die Action `plugins-index.yml` baut den Index bei jedem Push auf `plugins-pack/**` selbst.
- **Pack-Plugins (shelly-*, dreame) nicht in die Seal-Liste** in `src/lib/widgetSecrets.ts` eintragen (führt zu "Passwort nötig/falsch").
- Widget-Build prüft keine Typen (`npm run build:plugin-pack` strippt nur). Bei fehlgeschlagenem Build fällt er still auf das alte `widget.js` zurück und meldet trotzdem "Pack: 1 ok": die Zeile mitlesen.

## Stand 30.09.2026
- Auf GitHub (`a09af13`): Befund 1 (PluginStoreModal, `useMemo` an `activePlugins`) und Befund 2 (`postcss-legacy-compat.js`: in der Arbeitskopie gibt es die Datei nicht) sind erledigt, `STATUS.md` liegt dort.
- Die Arbeitskopie weicht von GitHub ab: es fehlen dort `.github/workflows/notify-selfstore.yml`, `docs/plugins/dreame|muell`, `postcss-legacy-compat.js`; dafür gibt es `android/` und `public/privacy.html`. Deshalb nur einzelne Dateien übertragen.

## Bekannte offene Punkte (belegt, Prüfung vom 30.09.2026)
- `PluginStoreModal.tsx:261`: `activeDashboard()?.plugins ?? []` erzeugt pro Render ein neues Array, das in den Deps von `handleAddPlugin` und `catalogRows` steht (nur Performance).
- `postcss-legacy-compat.js:1`: überflüssige `eslint-disable`-Zeile.
- `npm audit`: 21 Meldungen, aber ohne Laufzeit-Pfad (keine Server-Actions, axios nur im Build-Skript).

## Gelernt (nicht wiederholen)
- Der SQL-Verdacht in `db.ts` (`ensureColumn`) war ein Fehlalarm: die Werte sind fest im Code.
