// Auswahl-Knöpfe: Schlägt Bonsai Varianten vor ("Antworte mit der Nummer"), erscheinen sie als farbige Knöpfe
// unter der Antwort. Ein Klick schreibt die Nummer in den Chat und sendet sie.
(() => {
  if (window.__selfwebusAuswahl) return;
  window.__selfwebusAuswahl = true;
  const COLORS = ['#2f8a52', '#2b6b93', '#8a5fb0', '#b07a2a', '#a04a6a', '#3f7f86'];
  const TRIGGER = /antworte mit der nummer|sag mir die nummer|ich antworte nur mit der nummer/i;
  const style = document.createElement('style');
  style.textContent = '.sw-wahl{display:flex;flex-direction:column;gap:8px;margin:14px 0 4px}'
    + '.sw-wahl button{display:flex;align-items:center;gap:12px;text-align:left;padding:10px 14px;border-radius:12px;border:1px solid transparent;color:#fff;cursor:pointer;font:inherit;line-height:1.35}'
    + '.sw-wahl button:hover{filter:brightness(1.12)}.sw-wahl button:active{transform:scale(.99)}'
    + '.sw-wahl .n{flex:none;width:30px;height:30px;border-radius:50%;background:rgba(0,0,0,.28);display:grid;place-items:center;font-weight:700}'
    + '.sw-wahl .t{flex:1;overflow-wrap:anywhere}.sw-wahl .e{font-size:11px;font-weight:700;letter-spacing:.05em;background:rgba(255,255,255,.22);border-radius:8px;padding:2px 7px}'
    + '.sw-hinweis{font-size:12px;opacity:.7;margin-bottom:2px}';
  document.head.append(style);

  // Der Senden-Knopf ist der letzte Knopf im Eingabebereich (Anhang, Modell, Mikrofon, Senden).
  function sendeKnopf(editor) {
    for (let root = editor, i = 0; root && i < 8; root = root.parentElement, i++) {
      const knoepfe = [...root.querySelectorAll('button')];
      if (knoepfe.length >= 3) return knoepfe[knoepfe.length - 1];
    }
    return null;
  }

  function senden(zahl) {
    const editor = document.querySelector('.chat-prosemirror[contenteditable=true], .tiptap[contenteditable=true]');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertText', false, String(zahl));
    const enter = type => new KeyboardEvent(type, {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true});
    editor.dispatchEvent(enter('keydown'));
    editor.dispatchEvent(enter('keyup'));
    // Reicht Enter nicht (die Zahl steht noch im Feld), klickt der Knopf selbst auf Senden.
    setTimeout(() => {
      if ((editor.innerText || '').trim() !== String(zahl)) return;
      const knopf = sendeKnopf(editor);
      // Läuft Bonsai gerade, ist der letzte Knopf "Stopp" (Kreis mit Quadrat): den nie anklicken.
      if (knopf && !knopf.disabled && !/M2\.25 12c0-5\.385/.test(knopf.innerHTML)) knopf.click();
    }, 300);
  }

  window.__swSenden = senden;   // wird auch vom Weiter-Knopf (meldung.js) benutzt

  function kurz(text) {
    const clean = text.replace(/\s+/g, ' ').replace(/^\(?Empfehlung\)?\s*/i, '').trim();
    return clean.length > 150 ? clean.slice(0, 147) + '…' : clean;
  }

  // Die Liste der Varianten steht unter einer Überschrift oder einem Satz wie "Vorschlag" / "Varianten" / "Optionen".
  const UEBERSCHRIFT = /vorschlag|variante|option|wie weiter|auswahl|umsetzung/i;
  function wahlListe(nachricht) {
    const listen = [...nachricht.querySelectorAll('ol')].filter(l => l.children.length >= 2 && l.children.length <= 6);
    const mitTitel = listen.filter(l => {
      for (let el = l.previousElementSibling, i = 0; el && i < 2; el = el.previousElementSibling, i++) {
        if (UEBERSCHRIFT.test(el.innerText)) return true;
      }
      return false;
    });
    if (mitTitel.length) return mitTitel[mitTitel.length - 1];
    // Überschrift anders benannt (z. B. "Nächster Punkt?"): die Liste, auf die direkt "Antworte mit der Nummer" folgt.
    return listen.filter(l => {
      let weiter = 0;
      for (let el = l.nextElementSibling; el; el = el.nextElementSibling) weiter++;
      return weiter <= 2 && TRIGGER.test(l.parentElement.innerText.slice(-250));
    }).pop();
  }

  function pruefen() {
    const prosen = [...document.querySelectorAll('.prose')];
    const letzte = prosen[prosen.length - 1];
    if (!letzte || letzte.dataset.swWahl) return;
    if (!TRIGGER.test(letzte.innerText.slice(-250))) return;
    const liste = wahlListe(letzte);
    if (!liste) return;
    letzte.dataset.swWahl = '1';
    const box = document.createElement('div');
    box.className = 'sw-wahl';
    const hinweis = document.createElement('div');
    hinweis.className = 'sw-hinweis';
    hinweis.textContent = 'Klick sendet die Nummer:';
    box.append(hinweis);
    [...liste.children].forEach((li, index) => {
      const text = li.innerText;
      const empfohlen = /empfehlung/i.test(text) || index === 0 && !/empfehlung/i.test(liste.innerText);
      const knopf = document.createElement('button');
      knopf.type = 'button';
      knopf.style.background = empfohlen ? COLORS[0] : COLORS[(index % (COLORS.length - 1)) + 1];
      const n = document.createElement('span'); n.className = 'n'; n.textContent = String(index + 1);
      const t = document.createElement('span'); t.className = 't'; t.textContent = kurz(text);
      knopf.append(n, t);
      if (/empfehlung/i.test(text)) { const e = document.createElement('span'); e.className = 'e'; e.textContent = 'EMPFEHLUNG'; knopf.append(e); }
      knopf.onclick = () => { senden(index + 1); box.remove(); };
      box.append(knopf);
    });
    letzte.append(box);
  }

  let timer = 0;
  new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(pruefen, 500); }).observe(document.body, {childList: true, subtree: true, characterData: true});
  setTimeout(pruefen, 1500);
})();
