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
      ? `Bonsai liest den Chat: ${zahl(a.gelesen)} von ${zahl(a.gesamt)} Token. Noch keine Ausgabe, das dauert bei langen Chats.`
      : `Bonsai schreibt: ${zahl(a.geschrieben)} Token`;
    bar.style.display = lesen && a.gesamt ? '' : 'none';
    fill.style.width = a.gesamt ? Math.min(100, Math.round(a.gelesen / a.gesamt * 100)) + '%' : '0';
    const rect = editor.getBoundingClientRect();
    box.style.display = 'flex';
    box.style.left = Math.max(8, rect.left) + 'px';
    box.style.bottom = Math.max(8, window.innerHeight - rect.top + 56) + 'px';
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
})();
