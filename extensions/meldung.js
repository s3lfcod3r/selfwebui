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
    + '.sw-weiter{position:fixed;z-index:31;display:none;align-items:center;gap:12px;padding:8px 14px;border-radius:12px;background:rgba(127,29,29,.96);'
    + 'border:1px solid #f87171;color:#fee2e2;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,.4)}'
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
    leiste.style.bottom = Math.max(8, window.innerHeight - rect.top + 56) + 'px';
    leiste.style.maxWidth = Math.max(260, rect.width) + 'px';
  }

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
