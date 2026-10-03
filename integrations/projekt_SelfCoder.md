# Projekt SelfCoder (Webseite selfcoder.de)

- **Was:** Die Portfolio-Webseite https://selfcoder.de: dunkle, animierte One-Page-Seite, die die Self-Projekte vorstellt (zweisprachig Deutsch/Englisch). Next.js mit statischem Export (`output: "export"`, Ordner `out`), Tailwind. GitHub: `s3lfcod3r/selfcoder` (öffentlich, Standardzweig `main`).
- **Wichtig zu Next.js:** `AGENTS.md` im Repo sagt, dass diese Next.js-Version Änderungen gegenüber deinem Wissen hat. Lies vor Code-Änderungen die passende Anleitung unter `node_modules/next/dist/docs/` und rate keine APIs.
- **Hosting:** GitHub Pages. Die Aktion `Deploy to GitHub Pages` (`.github/workflows/deploy.yml`) baut bei jedem Push auf `main` (`npm ci`, `npm run build`) und veröffentlicht den Ordner `out`. Es gibt keinen Build auf dem Server. Die Domain `selfcoder.de` zeigt per DNS bei Strato (Nameserver `rzone.de`) auf GitHub Pages (am 01.10.2026: `185.199.108.153`), `www` leitet mit 301 auf `selfcoder.de` weiter. **Cloudflare ist für diese Domain nicht davor** (Antwort-Header: "Server: GitHub.com"). Sven nannte Cloudflare: falls es dazu etwas gibt (Tunnel, Mail, andere Domain), frage nach, statt zu raten.
- **Arbeitsordner:** `/repos/website` auf dem Board (Git-Klon von `s3lfcod3r/selfcoder`; auf dem alten Tower hieß er `Github SelfCoder/website`). Nie verschieben, ersetzen, klonen oder löschen. Vor jeder Arbeit `docker exec GitHubTool gitpull website`.
- **Prüfen ohne den Ordner zu verändern:** Kopiere den Ordner OHNE `node_modules` und `out` in einen Temp-Ordner (z. B. `/tmp/selfcoder-check`) und führe dort in einem Wegwerf-Container mit Node 20 oder neuer `npm ci`, `npm run lint` und `npm run build` aus (`docker run --rm --memory 2g`). Der Build muss grün sein, bevor etwas gepusht wird.
- **Veröffentlichen:** Push auf `main` veröffentlicht die Seite sofort. Nur auf ausdrücklichen Auftrag von Sven pushen, vorher Build grün und die Seite im Temp-Ordner geprüft. Danach den Lauf der Aktion `Deploy to GitHub Pages` ansehen und die Seite abrufen (`curl -sI https://selfcoder.de`).
- **Bei jeder Prüfung ansehen:**
  1. Links auf **eingestellte Projekte**: SelfMessenger, SelfMind und TwitchClips gibt es nicht mehr (Repos gelöscht). Jede Erwähnung oder jeder Link auf sie ist ein Befund.
  2. **Tote oder falsche Links** (Repos, Live-Adressen der Self-Projekte, Impressum, Datenschutz). Die Seiten der Projekte stehen in `Github SelfCoder/_INDEX.md` beziehungsweise in den Arbeitsbereichen.
  3. **Rechtliches (Deutschland):** Impressum nach § 5 DDG, Datenschutzerklärung, keine Google Fonts von fremden Servern (Schriften müssen lokal ausgeliefert werden), keine Einbindung fremder Skripte oder Tracker ohne Einwilligung.
  4. **Sicherheit:** GitHub Pages erlaubt keine eigenen HTTP-Header. Prüfe, ob eine `Content-Security-Policy` per `<meta>` sinnvoll ist, externe Skripte mit Integritätsprüfung (SRI) und `rel="noopener"` bei externen Links. HTTPS erzwingen ist in den Pages-Einstellungen von Sven.
  5. **Qualität:** Barrierefreiheit (Kontrast, Alt-Texte, Tastaturbedienung, `prefers-reduced-motion`), SEO (Titel, Beschreibung, Open-Graph, `sitemap`, `robots`), Ladegröße der Bilder (`public/`, `Logo/`), Abhängigkeiten (`npm audit`, nur belegte Befunde).
  6. **Aussehen** folgt dem `brand-kit` (`SELF-RULES.md`): kein eigenes Logo, kein anderes Farbschema.
- **Nicht möglich für dich:** DNS-Einträge bei Strato ansehen oder ändern (z. B. Reste abgeschalteter Seiten, die auf GitHub Pages zeigen und gekapert werden könnten: das ist Sven oder Claude am PC). Weise in solchen Fällen darauf hin.
- **Version:** Die Seite hat keine Versionsnummer. Der Stand ist der Commit auf `main`. `gitpush` verlangt sonst eine Versionsänderung: bei dieser Seite mit Svens ausdrücklicher Erlaubnis `docker exec -e GITPUSH_OHNE_VERSION=1 GitHubTool gitpush website` benutzen.
- **Nie:** Zugangsdaten, private Adressen oder E-Mail-Adressen, die nicht schon öffentlich auf der Seite stehen, in den Code schreiben. Nach Zugangsdaten suchen, bevor etwas veröffentlicht wird.

## Bekannte offene Punkte
- (noch keine eingetragen: bei der ersten Prüfung belegt ergänzen)

## Gelernt (nicht wiederholen)
- Erfundene Befunde sind der häufigste Fehler: nur melden, was du mit Datei:Zeile belegen kannst.
