// Meldung und Weiter-Knopf:
//  1. Wenn ein Chat von Bonsai fertig ist (egal in welchem Arbeitsbereich): Ton, Browser-Meldung und Haken im Tab-Titel.
//     Mit der Glocke unten links ein- und ausschalten (merkt sich der Browser).
//  2. Endet der aktuelle Chat rot (Bonsai ist beim Denken stehen geblieben oder mit Fehler beendet), erscheint über dem
//     Eingabefeld ein Knopf "Weiter senden". Die rote Karte im Arbeiter-Panel setzt dieselbe Marke und öffnet den Chat.
(() => {
  if (window.__selfwebusMeldung) return;
  window.__selfwebusMeldung = true;
  const KEY = 'sw-meldung', WEITER_KEY = 'sw-weiter';
  const lies = k => { try { return localStorage.getItem(k); } catch { return null; } };
  const schreibe = (k, v) => { try { localStorage.setItem(k, v); } catch {} };
  let an = lies(KEY) === '1';
  const titelOriginal = document.title;

  const style = document.createElement('style');
  style.textContent = '.sw-glocke{position:fixed;left:10px;bottom:52px;z-index:40;padding:5px 10px;border-radius:14px;border:1px solid rgba(148,163,184,.4);'
    + 'background:rgba(30,41,59,.92);color:#e2e8f0;font-size:12px;cursor:pointer}.sw-glocke.an{border-color:#4ade80}'
    + '.sw-fortsetzen{position:fixed;left:10px;bottom:84px;z-index:40;padding:5px 10px;border-radius:14px;border:1px solid rgba(148,163,184,.4);'
    + 'background:rgba(30,41,59,.92);color:#e2e8f0;font-size:12px;cursor:pointer}.sw-fortsetzen:hover{border-color:#38bdf8}'
    + '.sw-bild{position:fixed;right:350px;bottom:20px;z-index:45;width:280px;border-radius:14px;overflow:hidden;background:rgba(15,23,42,.97);'
    + 'border:1px solid rgba(148,163,184,.4);color:#e2e8f0;font-size:12px;box-shadow:0 8px 24px rgba(0,0,0,.5);display:none}'
    + '.sw-bild img{display:block;width:100%;height:auto;background:#000}.sw-bild .k{padding:8px 10px;display:flex;gap:8px;align-items:center;justify-content:space-between}'
    + '.sw-bild button,.sw-bild a{color:#bae6fd;background:none;border:0;cursor:pointer;font-size:12px;text-decoration:underline;padding:0}'
    + '.sw-bild .m{display:none;gap:6px;padding:6px 10px 0}.sw-bild .m button{border:1px solid rgba(148,163,184,.5);border-radius:6px;min-width:26px;padding:2px 6px;text-decoration:none}.sw-bild .m button.a{background:#0ea5e9;color:#082f49;border-color:#0ea5e9}'
    + '.sw-bildlauf{position:fixed;right:350px;bottom:20px;z-index:44;padding:6px 12px;border-radius:12px;background:rgba(30,41,59,.96);'
    + 'border:1px solid #38bdf8;color:#e2e8f0;font-size:12px;display:none}'
    + '.sw-weiter{position:fixed;z-index:31;display:none;align-items:center;gap:12px;padding:8px 14px;border-radius:12px;background:rgba(127,29,29,.96);'
    + 'border:1px solid #f87171;color:#fee2e2;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,.4)}'
    + '.sw-abschluss{position:fixed;z-index:31;display:none;align-items:center;gap:12px;padding:8px 14px;border-radius:12px;background:rgba(120,83,9,.96);'
    + 'color:#fef3c7;font-size:13px;box-shadow:0 4px 18px rgba(0,0,0,.4)}'
    + '.sw-abschluss button{border:0;border-radius:8px;padding:6px 14px;background:#fbbf24;color:#451a03;font-weight:700;cursor:pointer}'
    + '.sw-weiter button{border:0;border-radius:8px;padding:6px 14px;background:#f87171;color:#450a0a;font-weight:700;cursor:pointer}';
  document.head.append(style);

  // ---- Glocke ----
  const glocke = document.createElement('button');
  glocke.type = 'button';
  const glockeZeigen = () => { glocke.className = 'sw-glocke' + (an ? ' an' : ''); glocke.textContent = an ? '🔔 Meldung an' : '🔕 Meldung aus'; };
  glocke.onclick = async () => {
    an = !an; schreibe(KEY, an ? '1' : '0'); glockeZeigen();
    if (an) {
      try { if ('Notification' in window && Notification.permission === 'default') await Notification.requestPermission(); } catch {}
      ton(); // der Klick schaltet den Ton im Browser frei
    }
  };
  glockeZeigen();
  document.body.append(glocke);

  let audio = null;
  function ton() {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const jetzt = audio.currentTime;
      [660, 880].forEach((hz, i) => {
        const osc = audio.createOscillator(), gain = audio.createGain();
        osc.frequency.value = hz; osc.connect(gain); gain.connect(audio.destination);
        gain.gain.setValueAtTime(0.0001, jetzt + i * 0.18);
        gain.gain.exponentialRampToValueAtTime(0.25, jetzt + i * 0.18 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, jetzt + i * 0.18 + 0.16);
        osc.start(jetzt + i * 0.18); osc.stop(jetzt + i * 0.18 + 0.17);
      });
    } catch {}
  }
  function melden(titel, text) {
    if (!an) return;
    ton();
    document.title = '✓ ' + titelOriginal;
    try { if ('Notification' in window && Notification.permission === 'granted') new Notification(titel, {body: text}); } catch {}
  }
  window.addEventListener('focus', () => { document.title = titelOriginal; });

  // ---- Daten holen ----
  const holen = async url => { try { const r = await fetch(url, {cache: 'no-store'}); return r.ok ? await r.json() : null; } catch { return null; } };
  async function aktuellerChat() {
    const ws = new URLSearchParams(location.search).get('workspace');
    if (!ws) return null;
    const zustand = await holen('/api/state/workspace?path=' + encodeURIComponent(ws));
    const gruppen = (zustand && zustand.groups) || [];
    const gruppe = gruppen.find(g => g.id === zustand.activeGroupId) || gruppen[0];
    const tab = gruppe && (gruppe.tabs || []).find(t => t.id === gruppe.activeTabId);
    return tab && tab.type === 'chat' ? tab.path : null;
  }
  const editorFinden = () => document.querySelector('.chat-prosemirror[contenteditable=true], .tiptap[contenteditable=true]');

  // ---- Weiter-Knopf über dem Eingabefeld ----
  const leiste = document.createElement('div');
  leiste.className = 'sw-weiter';
  const leisteText = document.createElement('span');
  const leisteKnopf = document.createElement('button');
  leisteKnopf.type = 'button'; leisteKnopf.textContent = 'Weiter senden';
  leiste.append(leisteText, leisteKnopf);
  document.body.append(leiste);
  let gesendetFuer = '';
  function weiterSenden(chatId) {
    if (!window.__swSenden || gesendetFuer === chatId) return;
    gesendetFuer = chatId;
    leiste.style.display = 'none';
    window.__swSenden('weiter');
    setTimeout(() => { gesendetFuer = ''; }, 20000);   // danach darf es bei einem neuen Fehler wieder gesendet werden
  }
  leisteKnopf.onclick = () => { if (leiste.dataset.chat) weiterSenden(leiste.dataset.chat); };
  function leisteZeigen(chatId, fehler) {
    const editor = editorFinden();
    if (!chatId || !fehler || !editor || gesendetFuer === chatId) { leiste.style.display = 'none'; return; }
    const rect = editor.getBoundingClientRect();
    leiste.dataset.chat = chatId;
    leisteText.textContent = fehler;
    leiste.style.display = 'flex';
    leiste.style.left = Math.max(8, rect.left) + 'px';
    leiste.style.bottom = Math.max(8, window.innerHeight - rect.top + 24) + 'px';
    leiste.style.maxWidth = Math.max(260, rect.width) + 'px';
  }

  // ---- Abschluss-Knopf: Zug endete ohne Empfehlung zum Anklicken ----
  const ABSCHLUSS_BITTE = 'Fasse kurz zusammen, im Format: Gemacht (mit Beleg, z. B. Commit-ID oder Messwert), Nicht geprüft oder offen, und eine Empfehlung im Varianten-Format mit "Antworte mit der Nummer."';
  const abschluss = document.createElement('div');
  abschluss.className = 'sw-abschluss';
  const abschlussText = document.createElement('span');
  abschlussText.textContent = 'Bonsai hat keine Empfehlung gegeben.';
  const abschlussKnopf = document.createElement('button');
  abschlussKnopf.type = 'button'; abschlussKnopf.textContent = 'Zusammenfassung und nächster Schritt';
  abschluss.append(abschlussText, abschlussKnopf);
  document.body.append(abschluss);
  let abschlussGesendet = '';
  abschlussKnopf.onclick = () => {
    if (!window.__swSenden || !abschluss.dataset.chat) return;
    abschlussGesendet = abschluss.dataset.chat + '|' + abschluss.dataset.zeit;
    abschluss.style.display = 'none';
    window.__swSenden(ABSCHLUSS_BITTE);
  };
  function abschlussZeigen(chatId, eintrag) {
    const editor = editorFinden();
    const marke = eintrag ? chatId + '|' + eintrag.zeit : '';
    if (!chatId || !eintrag || !editor || abschlussGesendet === marke || leiste.style.display === 'flex') { abschluss.style.display = 'none'; return; }
    const rect = editor.getBoundingClientRect();
    abschluss.dataset.chat = chatId; abschluss.dataset.zeit = eintrag.zeit;
    abschluss.style.display = 'flex';
    abschluss.style.left = Math.max(8, rect.left) + 'px';
    abschluss.style.bottom = Math.max(8, window.innerHeight - rect.top + 24) + 'px';
    abschluss.style.maxWidth = Math.max(260, rect.width) + 'px';
  }

  // ---- Fortsetzen: neuer Chat im selben Arbeitsbereich mit dem Standard-Startsatz ----
  const warte = ms => new Promise(r => setTimeout(r, ms));
  const fortsetzenKnopf = document.createElement('button');
  fortsetzenKnopf.type = 'button';
  fortsetzenKnopf.className = 'sw-fortsetzen';
  fortsetzenKnopf.textContent = '↻ Neuer Chat mit Stand';
  fortsetzenKnopf.title = 'Startet einen frischen Chat in diesem Arbeitsbereich und lässt Bonsai PROJEKT.md und STATUS.md lesen';
  document.body.append(fortsetzenKnopf);
  let fortsetzenLaeuft = false;
  fortsetzenKnopf.onclick = async () => {
    if (fortsetzenLaeuft) return;
    const ws = new URLSearchParams(location.search).get('workspace');
    if (!ws || !window.__swSenden) return;
    const name = ws.split('/').filter(Boolean).pop();
    if (!window.confirm(`Neuen Chat in „${name}“ starten und mit dem Stand aus STATUS.md fortsetzen?`)) return;
    fortsetzenLaeuft = true;
    try {
      const vorher = await aktuellerChat();
      const neuerChatKnopf = () => {
        const a = [...document.querySelectorAll('.ws-item a')].find(x => (x.getAttribute('href') || '').includes(encodeURIComponent(ws)));
        const zeile = a && a.closest('div.group');
        return zeile && zeile.querySelector('[aria-label="Neuer Chat"]');
      };
      for (let versuch = 0; versuch < 3; versuch++) {
        const k = neuerChatKnopf();
        if (!k) break;
        k.click();
        await warte(1500);
        const jetzt = await aktuellerChat();
        if (jetzt && jetzt !== vorher) break;
      }
      for (let i = 0; i < 20 && !editorFinden(); i++) await warte(250);
      await warte(600);
      window.__swSenden(`Projekt ${name}, Fortsetzung. Lies PROJEKT.md und STATUS.md. Fasse in drei Zeilen zusammen, wo wir stehen, und mach mit dem nächsten offenen Punkt weiter. Pushen, Release und Löschen nur auf ausdrücklichen Auftrag.`);
    } finally {
      fortsetzenLaeuft = false;
    }
  };

  // ---- Bildaufträge (Bild-Dienst auf Board 1): Fortschrittsanzeige und fertiges Bild mit Vorschau ----
  const BILD_DIENST = 'http://192.168.1.103:8111';
  const bildLauf = document.createElement('div');
  bildLauf.className = 'sw-bildlauf';
  const bildKarte = document.createElement('div');
  bildKarte.className = 'sw-bild';
  const bildBild = document.createElement('img');
  bildBild.alt = 'Fertiges Bild';
  const bildMini = document.createElement('div');
  bildMini.className = 'm';
  const bildLeiste = document.createElement('div');
  bildLeiste.className = 'k';
  const bildText = document.createElement('span');
  const bildLink = document.createElement('a');
  bildLink.target = '_blank'; bildLink.rel = 'noopener'; bildLink.textContent = 'groß öffnen';
  const bildZu = document.createElement('button');
  bildZu.type = 'button'; bildZu.textContent = 'schließen';
  bildLeiste.append(bildText, bildLink, bildZu);
  bildKarte.append(bildBild, bildMini, bildLeiste);
  document.body.append(bildLauf, bildKarte);

  // Fertige Bilder bleiben sichtbar, bis Sven "schließen" klickt (auch nach Neuladen oder Tab-Wechsel).
  // Gemerkt wird, welche Aufträge er schon gesehen hat. Beim allerersten Start gelten Aufträge älter als 2 Stunden als gesehen.
  const GESEHEN_KEY = 'sw-bilder-gesehen';
  const gesehen = new Set();
  let gesehenNeu = true;
  try { const roh = JSON.parse(localStorage.getItem(GESEHEN_KEY) || 'null'); if (Array.isArray(roh)) { roh.forEach(i => gesehen.add(i)); gesehenNeu = false; } } catch {}
  function gesehenSpeichern() { try { localStorage.setItem(GESEHEN_KEY, JSON.stringify([...gesehen].slice(-300))); } catch {} }
  let ungesehen = [];
  let angezeigt = '';
  function bildAdresse(auftrag, datei) { return `${BILD_DIENST}/ergebnis/${auftrag.id}/${datei}`; }
  function bildWaehlen(auftrag, datei) {
    const adresse = bildAdresse(auftrag, datei);
    bildBild.src = adresse; bildLink.href = adresse;
    [...bildMini.children].forEach(b => b.classList.toggle('a', b.dataset.datei === datei));
  }
  function bildZeigen() {
    const auftrag = ungesehen[0];
    if (!auftrag) { bildKarte.style.display = 'none'; angezeigt = ''; return; }
    const dateien = auftrag.dateien || [];
    if (angezeigt !== auftrag.id) {              // nur neu aufbauen, wenn ein anderer Auftrag dran ist (sonst springt die Auswahl alle 4 s zurück)
      angezeigt = auftrag.id;
      bildMini.textContent = '';
      dateien.forEach((datei, i) => {
        const b = document.createElement('button');
        b.type = 'button'; b.dataset.datei = datei; b.textContent = String(i + 1);
        b.onclick = () => bildWaehlen(auftrag, datei);
        bildMini.append(b);
      });
      bildMini.style.display = dateien.length > 1 ? 'flex' : 'none';
      if (dateien[0]) bildWaehlen(auftrag, dateien[0]);
    }
    const mehr = ungesehen.length - 1;
    bildText.textContent = (auftrag.prompt || 'Bild fertig').slice(0, 50) + (mehr > 0 ? `  (+${mehr} weitere)` : '');
    bildKarte.style.display = 'block';
  }
  bildZu.onclick = () => {
    if (ungesehen[0]) { gesehen.add(ungesehen[0].id); gesehenSpeichern(); ungesehen = ungesehen.slice(1); }
    angezeigt = ''; bildZeigen();
  };
  let bildVorher = new Map();
  let bildErster = true;
  const BILD_TEXT = {wartet: 'wartet auf Bonsai', laedt: 'lädt das Bildmodell', rechnet: 'rechnet'};
  async function bildTakt() {
    try {
      const antwort = await fetch(BILD_DIENST + '/liste', {cache: 'no-store'});
      if (antwort.ok) {
        const liste = (await antwort.json()).auftraege || [];
        const jetzt = new Map(liste.map(a => [a.id, a]));
        const laufend = liste.find(a => BILD_TEXT[a.zustand]);
        bildLauf.style.display = laufend ? 'block' : 'none';
        if (laufend) bildLauf.textContent = '🖼 Bild ' + BILD_TEXT[laufend.zustand] + (laufend.zustand === 'wartet' ? ' (Bonsai beendet seinen Zug)' : ' (Bonsai ist entladen)');
        const jetztS = Date.now() / 1000;
        if (gesehenNeu) {
          liste.filter(a => a.zustand === 'fertig' && jetztS - (a.geaendert || 0) > 7200).forEach(a => gesehen.add(a.id));
          gesehenNeu = false; gesehenSpeichern();
        }
        for (const a of liste) {
          const alt = bildVorher.get(a.id);
          if (!bildErster && alt && alt.zustand !== 'fertig' && a.zustand === 'fertig') melden('Bild fertig', a.prompt || '');
          if (alt && alt.zustand !== 'fehler' && a.zustand === 'fehler') melden('Bildauftrag fehlgeschlagen', a.meldung || '');
        }
        // ältester zuerst unten, neuestes Bild liegt oben auf (die Liste kommt neueste zuerst)
        ungesehen = liste.filter(a => a.zustand === 'fertig' && (a.dateien || []).length && !gesehen.has(a.id) && jetztS - (a.geaendert || 0) < 7 * 86400);
        if (bildErster && ungesehen.length) melden('Bild fertig', ungesehen[0].prompt || '');
        bildZeigen();
        bildVorher = jetzt; bildErster = false;
      }
    } catch { bildLauf.style.display = 'none'; }
    setTimeout(bildTakt, 4000);
  }
  bildTakt();

  // ---- Hauptschleife ----
  let vorher = new Map();
  let erster = true;
  async function takt() {
    const aktiv = await holen('/api/selfwebui/aktiv');
    const fehler = (await holen('/api/selfwebui/fehler/status')) || {};
    const fehlerChats = fehler.chats || {};
    if (aktiv) {
      const jetzt = new Map((aktiv.laufend || []).map(c => [c.id, c.titel]));
      if (!erster) for (const [id, titel] of vorher) {
        if (jetzt.has(id)) continue;
        const rot = fehlerChats[id];
        melden(rot ? 'Bonsai ist stehen geblieben' : 'Bonsai ist fertig', titel + (rot ? ': ' + rot.fehler : ''));
      }
      vorher = jetzt; erster = false;
    }
    const aktuell = await aktuellerChat();
    leisteZeigen(aktuell, aktuell && fehlerChats[aktuell] ? fehlerChats[aktuell].fehler : '');
    abschlussZeigen(aktuell, aktuell && !fehlerChats[aktuell] ? (fehler.abschluss || {})[aktuell] : null);
    // Marke aus dem Arbeiter-Panel: Chat wurde über "Weiter" geöffnet, hier wird gesendet.
    const marke = lies(WEITER_KEY);
    if (marke) {
      let zeit = 0, id = marke;
      if (marke.includes('|')) [id, zeit] = [marke.split('|')[0], Number(marke.split('|')[1])];
      if (Date.now() - zeit > 40000) schreibe(WEITER_KEY, '');
      else if (aktuell === id && editorFinden() && fehlerChats[id]) { schreibe(WEITER_KEY, ''); weiterSenden(id); }
    }
    setTimeout(takt, 3000);
  }
  takt();
})();
