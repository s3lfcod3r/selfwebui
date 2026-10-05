// Chat-Status: zeigt direkt über dem Eingabefeld, was Bonsai gerade tut (liest den Chat / schreibt), mit Token-Zähler.
// Die Zahlen kommen aus /api/selfwebui/worker/status (Feld "aktivitaet"), dieselbe Quelle wie das Arbeiter-Panel.
(() => {
  if (window.__selfwebusChatstatus) return;
  window.__selfwebusChatstatus = true;
  const style = document.createElement('style');
  style.textContent = '.sw-chatstatus{position:fixed;z-index:30;display:none;align-items:center;gap:10px;padding:7px 14px;border-radius:12px;'
    + 'background:rgba(30,41,59,.96);border:1px solid rgba(148,163,184,.35);color:#e2e8f0;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,.35)}'
    + '.sw-chatstatus .p{flex:none;width:9px;height:9px;border-radius:50%;background:#38bdf8;animation:swpuls 1.1s ease-in-out infinite}'
    + '.sw-chatstatus.schreibt .p{background:#4ade80}'
    + '.sw-chatstatus .b{flex:none;width:90px;height:5px;border-radius:3px;background:rgba(148,163,184,.3);overflow:hidden}'
    + '.sw-chatstatus .b i{display:block;height:100%;background:#38bdf8}'
    + '@keyframes swpuls{50%{opacity:.35;transform:scale(.7)}}';
  document.head.append(style);
  const box = document.createElement('div');
  box.className = 'sw-chatstatus';
  const dot = document.createElement('span'); dot.className = 'p';
  const text = document.createElement('span');
  const bar = document.createElement('span'); bar.className = 'b';
  const fill = document.createElement('i'); bar.append(fill);
  box.append(dot, text, bar);
  document.body.append(box);

  const zahl = n => n.toLocaleString('de-DE');
  function zeigen(a) {
    const editor = document.querySelector('.chat-prosemirror[contenteditable=true], .tiptap[contenteditable=true]');
    if (!a || !editor) { box.style.display = 'none'; return; }
    const lesen = a.phase === 'liest';
    box.className = 'sw-chatstatus ' + (lesen ? 'liest' : 'schreibt');
    text.textContent = lesen
      ? `Bonsai liest den Chat: bisher ${zahl(a.gelesen)} Token. Noch keine Ausgabe, das dauert bei langen Chats.`
      : `Bonsai schreibt: ${zahl(a.geschrieben)} Token`;
    bar.style.display = 'none';   // die Gesamtlänge liefert der Server nicht, nur den Fortschritt
    const rect = editor.getBoundingClientRect();
    box.style.display = 'flex';
    box.style.left = Math.max(8, rect.left) + 'px';
    box.style.bottom = Math.max(8, window.innerHeight - rect.top + 24) + 'px';
    box.style.maxWidth = Math.max(240, rect.width) + 'px';
  }
  async function poll() {
    try {
      if (!document.hidden) {
        const response = await fetch('/api/selfwebui/worker/status', {cache: 'no-store'});
        zeigen(response.ok ? (await response.json()).aktivitaet : null);
      }
    } catch { zeigen(null); }
    setTimeout(poll, 1500);
  }
  poll();

  // ---- Kontext-Zähler: wie viel vom Chat-Gedächtnis belegt ist (Hinweis, wann ein neuer Chat sinnvoll ist) ----
  const kStyle = document.createElement('style');
  kStyle.textContent = '.sw-kontext{position:fixed;z-index:29;display:none;gap:8px;font:11px ui-monospace,SFMono-Regular,Menlo,monospace}'
    + '.sw-kontext span{padding:3px 9px;border-radius:8px;background:rgba(30,41,59,.92);border:1px solid rgba(148,163,184,.3);color:#cbd5e1}'
    + '.sw-kontext .gelb{border-color:#fbbf24;color:#fde68a}.sw-kontext .rot{border-color:#f87171;color:#fecaca}';
  document.head.append(kStyle);
  const kBox = document.createElement('div'); kBox.className = 'sw-kontext';
  const kPille = document.createElement('span'), aPille = document.createElement('span');
  kBox.append(kPille, aPille); document.body.append(kBox);
  async function chatId() {
    const ws = new URLSearchParams(location.search).get('workspace');
    if (!ws) return null;
    try {
      const r = await fetch('/api/state/workspace?path=' + encodeURIComponent(ws), {cache: 'no-store'});
      const z = r.ok ? await r.json() : null;
      const gruppen = (z && z.groups) || [];
      const g = gruppen.find(x => x.id === z.activeGroupId) || gruppen[0];
      const tab = g && (g.tabs || []).find(t => t.id === g.activeTabId);
      return tab && tab.type === 'chat' ? tab.path : null;
    } catch { return null; }
  }
  async function kontextTakt() {
    try {
      if (!document.hidden) {
        const id = await chatId();
        const editor = document.querySelector('.chat-prosemirror[contenteditable=true], .tiptap[contenteditable=true]');
        const r = id && editor ? await fetch('/api/selfwebui/kontext?chat=' + encodeURIComponent(id), {cache: 'no-store'}) : null;
        const k = r && r.ok ? (await r.json()).kontext : null;
        if (k) {
          const stufe = k.prozent >= 85 ? 'rot' : k.prozent >= 60 ? 'gelb' : '';
          kPille.className = stufe;
          kPille.textContent = `Kontext: ${zahl(k.kontext)} / ${zahl(k.grenze)} (${k.prozent} %)` + (stufe === 'rot' ? ' · bald neuer Chat' : '');
          kPille.title = `Länge des Chats beim letzten Aufruf. Bei ${zahl(k.grenze)} Token verdichtet Bonsai selbst, der Server kann bis ${zahl(k.max)}. Je länger, desto langsamer.`;
          aPille.textContent = `Ausgabe: ${zahl(k.ausgabe)}`;
          aPille.title = 'Token, die Bonsai im letzten Zug geschrieben und gedacht hat';
          const rect = editor.getBoundingClientRect();
          kBox.style.display = 'flex';
          kBox.style.left = Math.max(8, rect.left) + 'px';
          kBox.style.bottom = Math.max(8, window.innerHeight - rect.top + 4) + 'px';
        } else kBox.style.display = 'none';
      }
    } catch { kBox.style.display = 'none'; }
    setTimeout(kontextTakt, 5000);
  }
  kontextTakt();
})();
