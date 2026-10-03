// Löschschutz: Vor dem Löschen eines Arbeitsbereichs kommen zwei Bestätigungs-Popups hintereinander, vor dem Löschen eines Chats eines.
// Die Oberfläche löscht mit DELETE /api/state/workspace?path=...; hier wird genau dieser Aufruf abgefangen.
// Ablehnen bricht den Aufruf ab, der Arbeitsbereich bleibt in der Seitenleiste.
// Gelöscht wird nur der Eintrag in der Seitenleiste; Ordner und Dateien auf dem Board bleiben liegen.
(() => {
  if (window.__selfwebusLoeschschutz) return;
  window.__selfwebusLoeschschutz = true;
  const echt = window.fetch.bind(window);
  window.fetch = function (eingabe, optionen) {
    try {
      const url = String((eingabe && eingabe.url) || eingabe);
      const methode = String((optionen && optionen.method) || (eingabe && eingabe.method) || 'GET').toUpperCase();
      if (methode === 'DELETE' && /\/api\/chats\/[0-9a-fA-F-]{20,}(\?|$)/.test(url)) {
        if (!window.confirm('Diesen Chat wirklich löschen?\n\nDer Verlauf ist danach weg. Dateien im Arbeitsbereich bleiben liegen.')) {
          return Promise.reject(new DOMException('Löschen abgebrochen', 'AbortError'));
        }
      }
      if (methode === 'DELETE' && /\/api\/state\/workspace\?/.test(url)) {
        const treffer = url.match(/[?&]path=([^&]+)/);
        const pfad = treffer ? decodeURIComponent(treffer[1]) : '';
        const name = pfad.split('/').filter(Boolean).pop() || pfad || 'dieser Arbeitsbereich';
        const erste = window.confirm(`Arbeitsbereich „${name}“ wirklich löschen?\n\nEr verschwindet aus der Seitenleiste. Ordner und Dateien auf dem Board bleiben liegen.`);
        const zweite = erste && window.confirm(`Letzte Frage: „${name}“ jetzt endgültig aus der Liste entfernen?\n\nBei einem Update kommt er NICHT von selbst zurück.`);
        if (!zweite) return Promise.reject(new DOMException('Löschen abgebrochen', 'AbortError'));
      }
    } catch (fehler) {
      if (fehler && fehler.name === 'AbortError') throw fehler;
    }
    return echt(eingabe, optionen);
  };
})();
