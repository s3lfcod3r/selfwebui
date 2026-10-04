'use strict';
// Bonsai & Qwen Image Generator: Oberfläche für den Bild-Dienst (Port 8111). Läuft im Heimnetz, kein Login.
// Adresse des Bild-Dienstes und von Bonsai kommen vom Studio-Server (config.json), damit die Oberfläche auf einem anderen Board laufen kann.
let API = `${location.protocol}//${location.hostname}:8111`;
let BONSAI = `${location.protocol}//${location.hostname}:8085`;
const $ = s => document.querySelector(s);
const LAUFEND = ['wartet', 'laedt', 'rechnet'];
const ZUSTAND = {wartet: 'wartet auf Bonsai', laedt: 'Bonsai wird entladen, Qwen lädt', rechnet: 'rechnet', fertig: 'fertig', fehler: 'Fehler'};

// ---------------------------------------------------------------- Auswahldaten
const FORMATE = [['q', 'Quadrat', 1, 1], ['h34', 'Hoch 3:4', 3, 4], ['q43', 'Quer 4:3', 4, 3], ['h916', 'Hoch 9:16', 9, 16], ['q169', 'Quer 16:9', 16, 9]];
const GROESSEN = [[1024, 'Standard'], [1536, 'Groß'], [2048, 'Maximal']];
const LICHT = [['', 'egal', ''], ['golden', 'Warmes goldenes Licht', 'warm golden hour light'], ['bewoelkt', 'Weiches bewölktes Licht', 'soft overcast light'],
  ['dramatisch', 'Dramatisch und dunkel', 'dramatic low-key lighting, deep shadows'], ['hell', 'Hell und freundlich', 'bright, friendly daylight'], ['studio', 'Studiolicht', 'clean soft studio lighting'],
  ['blau', 'Blaue Stunde', 'blue hour twilight, deep blue sky with warm lights'], ['nebel', 'Nebel und Dunst', 'misty atmosphere, soft diffused haze'],
  ['gegen', 'Gegenlicht', 'backlight with rim light and lens flare'], ['neon', 'Neon und Nacht', 'night scene with glowing neon lights, reflections'],
  ['kerze', 'Kerzenlicht', 'warm candlelight, cozy intimate glow'], ['mittag', 'Grelles Sonnenlicht', 'harsh midday sunlight, strong contrast']];
const AUSSCHNITT = [['', 'egal', ''], ['nah', 'Nahaufnahme', 'close-up shot'], ['halb', 'Halbtotale', 'medium shot'], ['total', 'Totale / Ganzer Ort', 'wide establishing shot'],
  ['vogel', 'Vogelperspektive', "bird's-eye view from above"], ['frosch', 'Froschperspektive', 'low angle shot looking up'], ['weit', 'Weitwinkel', 'ultra wide-angle lens'], ['makro', 'Makro', 'macro photography, extreme close-up detail']];
const ARTEN = {
  foto: {name: 'Foto', format: 'h34', stile: [['real', 'Fotorealistisch', 'photorealistic photograph, natural detail, sharp focus'], ['natur', 'Naturfoto', 'professional nature photograph, shallow depth of field, creamy bokeh'],
    ['portraet', 'Porträt', 'portrait photograph, 85mm lens, soft blurred background'], ['produkt', 'Produktfoto', 'clean studio product photograph, crisp detail'],
    ['reportage', 'Reportage / Straße', 'candid street photography, documentary style, natural moment'], ['luft', 'Luftbild / Drohne', 'aerial drone photograph from high above'],
    ['archi', 'Architektur', 'architectural photograph, clean lines, perfect perspective'], ['food', 'Food', 'appetizing food photography, shallow depth of field, styled'],
    ['sw', 'Schwarzweiß', 'black and white photograph, rich contrast, fine grain'], ['film', 'Analogfilm', 'vintage analog film photograph, grain, faded colors'],
    ['kino', 'Kino-Look', 'cinematic still, anamorphic lens, color graded film look'], ['tele', 'Tier / Tele', 'wildlife telephoto photograph, crisp fur or feathers, creamy bokeh']]},
  illu: {name: 'Illustration', format: 'q', stile: [['aquarell', 'Aquarell', 'watercolor painting, soft washes'], ['comic', 'Comic', 'comic book illustration, bold outlines, vivid colors'],
    ['oel', 'Ölgemälde', 'oil painting, visible brush strokes'], ['retro', 'Retro-Poster', 'retro vintage poster style'], ['render', '3D-Render', '3D render, soft studio lighting'],
    ['flach', 'Flach / Vektor', 'flat vector illustration, simple shapes'], ['anime', 'Anime / Manga', 'anime illustration, clean line art, vibrant cel shading'],
    ['pixel', 'Pixel Art', 'pixel art, limited color palette, crisp pixels'], ['blei', 'Bleistift', 'detailed pencil drawing, graphite shading'],
    ['tusche', 'Tusche / Kohle', 'ink and charcoal drawing, expressive strokes'], ['pop', 'Pop-Art', 'pop art, halftone dots, bold flat colors'],
    ['lowpoly', 'Low Poly', 'low poly 3D illustration, faceted geometric shapes'], ['cyber', 'Cyberpunk', 'cyberpunk illustration, neon city, rain, futuristic'],
    ['fantasy', 'Fantasy', 'epic fantasy illustration, detailed, magical atmosphere'], ['kinder', 'Kinderbuch', "children's book illustration, warm friendly colors, soft shapes"],
    ['iso', 'Isometrisch', 'isometric illustration, clean geometry, soft shadows'], ['papier', 'Papierschnitt', 'layered paper cut art, depth and soft shadows'],
    ['steam', 'Steampunk', 'steampunk illustration, brass gears, Victorian machinery'], ['clay', 'Knetfiguren / Clay', 'claymation style, handmade clay figures, soft studio light']]},
  logo: {name: 'Logo / Icon', format: 'q', stile: [['minimal', 'Flach und minimal', 'flat minimal logo, vector style, simple clean shapes'], ['emblem', 'Emblem / Wappen', 'emblem crest logo, symmetrical'],
    ['3d', '3D-Look', 'glossy 3D icon'], ['hand', 'Handgezeichnet', 'hand-drawn logo, ink lines'], ['maskottchen', 'Maskottchen', 'friendly mascot character logo, bold outline'],
    ['mono', 'Monogramm / Buchstabe', 'monogram logo built from a single letter, elegant'], ['linie', 'Linienkunst', 'single weight line art logo, outline only'],
    ['verlauf', 'Farbverlauf', 'modern gradient logo, smooth color transitions'], ['badge', 'Retro-Badge', 'retro badge logo, circular, vintage'],
    ['geo', 'Geometrisch', 'geometric logo made of clean shapes, strong symmetry'], ['app', 'App-Icon', 'app icon, rounded square, simple bold symbol']]},
  poster: {name: 'Poster / Werbung', format: 'h34', stile: [['modern', 'Modern', 'modern poster design, strong composition'], ['retro', 'Retro', 'retro vintage poster'],
    ['foto', 'Fotorealistisch', 'photorealistic advertising photograph'], ['comic', 'Comic', 'comic style poster'], ['swiss', 'Minimal / Swiss', 'minimalist Swiss style poster, grid layout, bold typography space'],
    ['deco', 'Art Deco', 'Art Deco poster, gold and black geometric ornaments'], ['event', 'Konzert / Event', 'energetic concert event poster, dynamic lighting'],
    ['film', 'Filmposter', 'cinematic movie poster composition, dramatic'], ['reise', 'Vintage-Reiseposter', 'vintage travel poster, flat colors, scenic'], ['produkt', 'Produktwerbung', 'premium product advertisement, glossy, studio set']]},
  wall: {name: 'Wallpaper', format: 'q169', stile: [['foto', 'Fotorealistisch', 'photorealistic scenic wallpaper'], ['illu', 'Illustration', 'detailed illustrated wallpaper'],
    ['minimal', 'Minimal', 'minimalist abstract wallpaper, calm gradients'], ['land', 'Landschaft', 'breathtaking landscape wallpaper, epic scale'],
    ['raum', 'Weltraum / Galaxie', 'deep space nebula and galaxy wallpaper, stars'], ['abstrakt', 'Abstrakt', 'abstract fluid art wallpaper, flowing shapes and colors'],
    ['anime', 'Anime-Szene', 'anime style scenic wallpaper, painterly sky'], ['cyber', 'Cyberpunk-Stadt', 'cyberpunk city at night wallpaper, neon and rain'],
    ['wald', 'Natur / Wald', 'serene forest wallpaper, light rays through trees'], ['dunkel', 'Dunkel / Elegant', 'dark elegant wallpaper, subtle texture, deep colors']]},
};
const ZIELE = [['profi', 'Profi-Look', 'Make it look like a professional photograph: sharper details, balanced exposure, natural colors.'],
  ['stil', 'Anderer Stil', 'Render the whole image as a painting in the requested style.'], ['hintergrund', 'Hintergrund tauschen', 'Replace only the background.'], ['frei', 'Nur etwas ändern', '']];
// grobe Rechenzeit in Minuten je Variante (gemessen: neu 1024 ca. 1,5; Foto ändern 1536 ca. 4 je Variante)
const MIN_NEU = {1024: 1.5, 1536: 2.5, 2048: 4.5}, MIN_AEND = {1024: 2, 1536: 4, 2048: 7};

const zustand = {art: 'foto', vorlage: null, vorlageUrl: '', archiv: [], queue: [], filter: '', detail: null, idx: 0};
const speicher = {
  lesen(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch { return null; } },
  schreiben(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ohne Speicher weiter */ } },
};

// ---------------------------------------------------------------- Hilfen
function toast(text, art = 'ok') {
  const t = $('#toast'); t.textContent = text; t.className = 'toast show ' + art;
  clearTimeout(toast.zeit); toast.zeit = setTimeout(() => { t.className = 'toast'; }, art === 'err' ? 7000 : 3500);
}
async function api(pfad, methode = 'GET', daten = null, roh = null) {
  const optionen = {method: methode, cache: 'no-store'};
  if (roh) optionen.body = roh; else if (daten) { optionen.body = JSON.stringify(daten); optionen.headers = {'Content-Type': 'application/json'}; }
  const antwort = await fetch(API + pfad, optionen);
  const kopf = antwort.headers.get('Content-Type') || '';
  const inhalt = kopf.includes('json') ? await antwort.json() : await antwort.blob();
  if (!antwort.ok) throw new Error((inhalt && inhalt.fehler) || `Fehler ${antwort.status}`);
  return inhalt;
}
function auswahl(behaelter, optionen, start, bei) {
  let wert = start;
  const knoepfe = optionen.map(([w, label, sub]) => {
    const b = document.createElement('button'); b.type = 'button'; b.dataset.w = String(w); b.textContent = label;
    if (sub && !sub.includes(' ') ) { const s = document.createElement('small'); s.textContent = sub; b.append(s); }
    b.onclick = () => setzen(w, true);
    behaelter.append(b); return b;
  });
  function setzen(w, ausloesen) { wert = w; knoepfe.forEach(b => b.classList.toggle('on', b.dataset.w === String(w))); if (ausloesen && bei) bei(w); }
  setzen(start, false);
  return {get: () => wert, set: w => setzen(w, false), neu(opt, s) { behaelter.textContent = ''; return auswahl(behaelter, opt, s, bei); }};
}
const zahl = (n, nachkomma = 1) => Number(n).toLocaleString('de-DE', {maximumFractionDigits: nachkomma});
const gb = b => b >= 1e9 ? zahl(b / 1e9) + ' GB' : zahl(b / 1e6, 0) + ' MB';
const zeit = s => s ? new Date(s * 1000).toLocaleString('de-DE', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'}) : '';
function masse(formatId, lang) {
  const [, , w, h] = FORMATE.find(f => f[0] === formatId);
  const kurz = Math.max(512, Math.round(lang * Math.min(w, h) / Math.max(w, h) / 16) * 16);
  return w >= h ? [lang, kurz] : [kurz, lang];
}
const bildUrl = (j, datei) => `${API}/ergebnis/${j.id}/${datei}`;
function vorschauUrl(j, i = 0) {
  const nr = (j.dateien[i] || 'ergebnis-0.png').replace('ergebnis-', '').replace('.png', '');
  return (j.thumbs || []).includes(`thumb-${nr}.jpg`) ? bildUrl(j, `thumb-${nr}.jpg`) : bildUrl(j, j.dateien[i] || 'ergebnis-0.png');
}

// ---------------------------------------------------------------- Neues Bild
const nArt = auswahl($('#n-art'), Object.entries(ARTEN).map(([k, a]) => [k, a.name]), 'foto', w => { zustand.art = w; artGewaehlt(); });
let nStil, nFormat, nLicht, nGroesse, nAnzahl;
nLicht = auswahl($('#n-licht'), LICHT.map(([w, l]) => [w, l]), '');
const nAusschnitt = auswahl($('#n-ausschnitt'), AUSSCHNITT.map(([w, l]) => [w, l]), '');
nFormat = auswahl($('#n-format'), FORMATE.map(([w, l]) => [w, l]), 'h34', neuSumme);
nGroesse = auswahl($('#n-groesse'), GROESSEN, 1024, neuSumme);
nAnzahl = auswahl($('#n-anzahl'), [[1, '1'], [2, '2'], [3, '3'], [4, '4']], 1, neuSumme);
function artGewaehlt() {
  const art = ARTEN[zustand.art];
  nStil = nStil ? nStil.neu(art.stile.map(([w, l]) => [w, l]), art.stile[0][0]) : auswahl($('#n-stil'), art.stile.map(([w, l]) => [w, l]), art.stile[0][0]);
  nFormat.set(art.format);
  $('#n-logo').classList.toggle('hidden', zustand.art !== 'logo');
  neuSumme();
}
function neuSumme() {
  const [b, h] = masse(nFormat.get(), nGroesse.get()), n = nAnzahl.get();
  const min = Math.max(1, Math.round(MIN_NEU[nGroesse.get()] * n + 1));
  $('#n-summe').textContent = `${b} x ${h} Pixel (${zahl(b * h / 1e6)} MP) · ${n} Variante${n > 1 ? 'n' : ''} · ca. ${min} Min (Bonsai wird währenddessen entladen)`;
}
function stilWort(art, id) { return (ARTEN[art].stile.find(s => s[0] === id) || [])[2] || ''; }
function lichtWort(id) { return (LICHT.find(l => l[0] === id) || [])[2] || ''; }
function ausschnittWort(id) { return (AUSSCHNITT.find(l => l[0] === id) || [])[2] || ''; }
function baueNeu() {
  const t = $('#n-text').value.trim();
  if (t.length < 3) throw new Error('Bitte erst eine Beschreibung eintippen (mindestens 3 Zeichen).');
  const teile = [];
  if (zustand.art === 'logo') {
    const name = $('#n-logotext').value.trim(), farben = $('#n-farben').value.trim();
    teile.push('A logo design: ' + t);
    teile.push(name ? `The logo contains the text "${name}" in clean bold letters` : 'Symbol only, no text, no letters');
    if (farben) teile.push('Colors: ' + farben);
    teile.push('centered on a plain solid background');
  } else teile.push(t);
  teile.push(stilWort(zustand.art, nStil.get()), lichtWort(nLicht.get()), ausschnittWort(nAusschnitt.get()));
  if (zustand.art !== 'logo' || !$('#n-logotext').value.trim()) teile.push('no readable text');
  return teile.filter(Boolean).join('. ') + '.';
}
async function bonsaiSchreiben(modus, text, hinweise, ziel, knopf) {
  knopf.disabled = true; const alt = knopf.textContent; knopf.textContent = 'Bonsai schreibt …';
  try { ziel.value = (await api('/prompt', 'POST', {text, modus, hinweise})).prompt; }
  catch (e) { toast(e.message, 'err'); } finally { knopf.disabled = false; knopf.textContent = alt; }
}
$('#n-bonsai').onclick = () => {
  try { baueNeu(); } catch (e) { return toast(e.message, 'err'); }
  const h = [stilWort(zustand.art, nStil.get()), lichtWort(nLicht.get()), ausschnittWort(nAusschnitt.get())].filter(Boolean).join(', ');
  bonsaiSchreiben('neu', $('#n-text').value + ($('#n-logotext').value && zustand.art === 'logo' ? `. Logo text: ${$('#n-logotext').value}` : ''), h, $('#n-prompt'), $('#n-bonsai'));
};
$('#n-los').onclick = async () => {
  try {
    const [breite, hoehe] = masse(nFormat.get(), nGroesse.get());
    const prompt = $('#n-prompt').value.trim() || baueNeu();
    const seed = $('#n-seed').value.trim();
    const auftrag = {modus: 'neu', prompt, breite, hoehe, anzahl: nAnzahl.get()};
    if (/^\d+$/.test(seed)) auftrag.seed = Number(seed);
    await api('/auftrag', 'POST', auftrag);
    toast('Auftrag angenommen. Er läuft, sobald Bonsai seinen Zug beendet hat.'); ladeQueue();
  } catch (e) { toast(e.message, 'err'); }
};

// ---------------------------------------------------------------- Bild ändern
const aZiel = auswahl($('#a-ziel'), ZIELE.map(([w, l]) => [w, l]), 'profi');
const aLicht = auswahl($('#a-licht'), LICHT.map(([w, l]) => [w, l]), '');
const STIL_ALLE = [['', 'egal', ''], ...Object.values(ARTEN).flatMap(a => a.stile).filter((x, i, l) => l.findIndex(y => y[0] === x[0]) === i && !['real', 'foto'].includes(x[0]))];
const aStil = auswahl($('#a-stil'), STIL_ALLE.map(([w, l]) => [w, l]), '');
const aGroesse = auswahl($('#a-groesse'), GROESSEN.map(([w, l]) => [w, l]), 1024, aendSumme);
const aAnzahl = auswahl($('#a-anzahl'), [[1, '1'], [2, '2'], [3, '3'], [4, '4']], 1, aendSumme);
function aendSumme() {
  const n = aAnzahl.get(), min = Math.max(2, Math.round(MIN_AEND[aGroesse.get()] * n + 1));
  $('#a-summe').textContent = `Auflösung ${aGroesse.get()} (Ergebnis etwa ${zahl(aGroesse.get() ** 2 / 1e6)} MP in der Form des Fotos) · ${n} Variante${n > 1 ? 'n' : ''} · ca. ${min} Min`;
}
aendSumme();
function vorlageSetzen(name, url) {
  zustand.vorlage = name; zustand.vorlageUrl = url;
  const bild = $('#a-vorschau'); bild.src = url || ''; bild.classList.toggle('hidden', !name);
  $('#a-leer').classList.toggle('hidden', !!name); $('#a-weg').classList.toggle('hidden', !name);
}
async function dateiHochladen(datei) {
  if (!datei || !/^image\/(png|jpeg|webp)$/.test(datei.type)) return toast('Bitte ein png-, jpg- oder webp-Bild wählen.', 'err');
  if (datei.size > 25 * 1024 * 1024) return toast('Das Bild ist größer als 25 MB.', 'err');
  try {
    const ende = datei.type === 'image/png' ? 'png' : datei.type === 'image/webp' ? 'webp' : 'jpg';
    const name = `foto-${Date.now()}.${ende}`;
    await api('/vorlage/' + name, 'PUT', null, datei);
    vorlageSetzen(name, URL.createObjectURL(datei));
  } catch (e) { toast(e.message, 'err'); }
}
$('#a-datei').onchange = e => dateiHochladen(e.target.files[0]);
const drop = $('#a-drop');
['dragenter', 'dragover'].forEach(n => drop.addEventListener(n, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(n => drop.addEventListener(n, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => dateiHochladen(e.dataTransfer.files[0]));
$('#a-weg').onclick = () => vorlageSetzen(null, '');
function baueAendern() {
  if (!zustand.vorlage) throw new Error('Bitte erst ein Foto wählen.');
  const ziel = ZIELE.find(z => z[0] === aZiel.get()), wunsch = $('#a-text').value.trim();
  if (aZiel.get() === 'frei' && wunsch.length < 3) throw new Error('Bitte beschreiben, was sich ändern soll.');
  const stilText = STIL_ALLE.find(x => x[0] === aStil.get() && x[0])?.[2] || '';
  const teile = ['Edit the reference photo. Keep the people and the main objects exactly as in the photo: same face, hair, clothes, pose and position. Do not add, remove or duplicate any object or person',
    ziel[2], stilText ? `Render the whole image in this style: ${stilText}` : '', wunsch, lichtWort(aLicht.get()), 'Photorealistic, same camera angle and framing, no readable text on new surfaces'];
  return teile.filter(Boolean).join('. ').replace(/\.\.+/g, '.') + '.';
}
$('#a-bonsai').onclick = () => {
  const wunsch = $('#a-text').value.trim();
  if (wunsch.length < 3) return toast('Bitte erst im Feld „Wunsch" beschreiben, was sich ändern soll.', 'err');
  bonsaiSchreiben('bearbeiten', `${ZIELE.find(z => z[0] === aZiel.get())[1]}: ${wunsch}`, [lichtWort(aLicht.get()), (STIL_ALLE.find(x => x[0] === aStil.get() && x[0]) || [])[2]].filter(Boolean).join(', '), $('#a-prompt'), $('#a-bonsai'));
};
$('#a-los').onclick = async () => {
  try {
    const prompt = $('#a-prompt').value.trim() || baueAendern();
    if (!zustand.vorlage) throw new Error('Bitte erst ein Foto wählen.');
    await api('/auftrag', 'POST', {modus: 'bearbeiten', vorlage: zustand.vorlage, prompt, aufloesung: aGroesse.get(), anzahl: aAnzahl.get()});
    toast('Auftrag angenommen. Er läuft, sobald Bonsai seinen Zug beendet hat.'); ladeQueue();
  } catch (e) { toast(e.message, 'err'); }
};

// ---------------------------------------------------------------- Warteschlange
async function ladeQueue() {
  try { zustand.queue = (await api('/archiv?limit=40')).auftraege; } catch { return; }
  const gesehen = new Set(speicher.lesen('sbq-gesehen') || []);
  if (!speicher.lesen('sbq-gesehen')) {   // erster Start: alles, was älter als 2 Stunden ist, gilt als gesehen
    zustand.queue.filter(j => j.zustand === 'fertig' && Date.now() / 1000 - (j.geaendert || 0) > 7200).forEach(j => gesehen.add(j.id));
    speicher.schreiben('sbq-gesehen', [...gesehen]);
  }
  const jetzt = Date.now() / 1000;
  const zeilen = zustand.queue.filter(j => LAUFEND.includes(j.zustand) || (j.zustand === 'fertig' && !gesehen.has(j.id) && jetzt - (j.geaendert || 0) < 86400)
    || (j.zustand === 'fehler' && !gesehen.has(j.id) && jetzt - (j.geaendert || 0) < 3600));
  const feld = $('#warteschlange'); feld.textContent = '';
  feld.classList.toggle('hidden', !zeilen.length);
  const fertigVorher = zustand.vorherFertig || new Set();
  for (const j of zeilen) {
    const z = document.createElement('div'); z.className = 'qitem ' + (j.zustand === 'fertig' ? 'fertig' : j.zustand === 'fehler' ? 'fehler' : '');
    if (j.zustand === 'fertig') { const i = document.createElement('img'); i.src = vorschauUrl(j); z.append(i); }
    const t = document.createElement('div'); t.className = 't'; t.textContent = (j.prompt || '').slice(0, 90);
    const s = document.createElement('div'); s.className = 's';
    s.textContent = j.zustand === 'fehler' ? (j.meldung || 'Fehler') : j.zustand === 'fertig' ? 'fertig · klicken zum Ansehen' : ZUSTAND[j.zustand] + (j.gestartet ? ` · seit ${Math.round((jetzt - j.gestartet) / 60)} Min` : '');
    z.append(t, s);
    if (j.zustand === 'wartet') { const b = document.createElement('button'); b.className = 'btn btn-small'; b.textContent = 'Abbrechen';
      b.onclick = async () => { try { await api(`/auftrag/${j.id}/abbrechen`, 'POST'); ladeQueue(); } catch (e) { toast(e.message, 'err'); } }; z.append(b); }
    if (j.zustand === 'fertig' || j.zustand === 'fehler') {
      const zu = document.createElement('button'); zu.className = 'btn btn-small'; zu.textContent = 'ausblenden';
      zu.onclick = e => { e.stopPropagation(); gesehen.add(j.id); speicher.schreiben('sbq-gesehen', [...gesehen].slice(-300)); ladeQueue(); }; z.append(zu);
      if (j.zustand === 'fertig') z.onclick = () => { gesehen.add(j.id); speicher.schreiben('sbq-gesehen', [...gesehen].slice(-300)); oeffneDetail(j); ladeQueue(); };
    }
    feld.append(z);
  }
  const jetztFertig = new Set(zustand.queue.filter(j => j.zustand === 'fertig').map(j => j.id));
  if (zustand.vorherFertig && [...jetztFertig].some(id => !fertigVorher.has(id))) { document.title = '✓ Bild fertig – Bonsai & Qwen'; toast('Ein Bild ist fertig.'); if (location.hash === '#archiv') ladeArchiv(); }
  zustand.vorherFertig = jetztFertig;
}
window.addEventListener('focus', () => { document.title = 'Bonsai & Qwen Image Generator'; });
async function bonsaiPill() {
  const p = $('#bonsaiPill');
  try {
    const b = await api('/bonsai');
    p.textContent = b.bereit ? (b.beschaeftigt ? 'Bonsai arbeitet' : 'Bonsai bereit') : 'Bonsai aus';
    p.className = 'pill ' + (b.bereit ? 'ok' : 'none');
  } catch { p.textContent = 'Bild-Dienst ?'; p.className = 'pill bad'; }
}

// ---------------------------------------------------------------- Archiv
async function ladeArchiv() {
  try { zustand.archiv = (await api('/archiv?limit=500')).auftraege; } catch (e) { return toast(e.message, 'err'); }
  zeichneArchiv();
}
function kachel(j, bei) {
  const k = document.createElement('div'); k.className = 'kachel';
  const bild = document.createElement('div'); bild.className = 'bild';
  if (j.zustand === 'fertig' && j.dateien.length) { const i = document.createElement('img'); i.loading = 'lazy'; i.src = vorschauUrl(j); i.alt = ''; bild.append(i); }
  else bild.textContent = ZUSTAND[j.zustand] || j.zustand;
  const info = document.createElement('div'); info.className = 'info';
  const p = document.createElement('p'); p.textContent = j.prompt || '';
  const m = document.createElement('div'); m.className = 'm';
  m.textContent = `${zeit(j.angelegt || j.geaendert)} · ${j.modus === 'bearbeiten' ? 'geändert' : 'neu'}${j.breite && j.modus === 'neu' ? ` · ${j.breite}x${j.hoehe}` : ''}`;
  info.append(p, m); k.append(bild, info);
  if (j.dateien.length > 1) { const z = document.createElement('span'); z.className = 'chip zahl'; z.textContent = `${j.dateien.length} Bilder`; k.append(z); }
  if (bei) k.onclick = () => bei(j);
  return k;
}
function zeichneArchiv() {
  const q = $('#s-text').value.trim().toLowerCase(), f = zustand.filter;
  const liste = zustand.archiv.filter(j => (!q || (j.prompt || '').toLowerCase().includes(q)) && (!f || (f === 'fav' ? j.favorit : j.modus === f)));
  const grid = $('#s-grid'); grid.textContent = '';
  for (const j of liste) {
    const k = kachel(j, oeffneDetail);
    const stern = document.createElement('button'); stern.className = 'stern' + (j.favorit ? ' an' : ''); stern.textContent = j.favorit ? '★' : '☆'; stern.title = 'Favorit (wird nie automatisch gelöscht)';
    stern.onclick = async e => { e.stopPropagation(); await favorit(j); }; k.append(stern);
    grid.append(k);
  }
  $('#s-zahl').textContent = `${liste.length} von ${zustand.archiv.length}`;
  $('#s-leer').classList.toggle('hidden', liste.length > 0);
}
async function favorit(j) {
  try { j.favorit = (await api(`/auftrag/${j.id}/favorit`, 'POST', {an: !j.favorit})).favorit; zeichneArchiv(); if (zustand.detail === j) detailKopf(); }
  catch (e) { toast(e.message, 'err'); }
}
$('#s-text').oninput = zeichneArchiv;
$('#s-filter').onclick = e => { const b = e.target.closest('button'); if (!b) return; zustand.filter = b.dataset.f;
  [...$('#s-filter').children].forEach(x => x.classList.toggle('active', x === b)); zeichneArchiv(); };

// ---------------------------------------------------------------- Detail
function detailKopf() {
  const j = zustand.detail;
  $('#d-fav').textContent = j.favorit ? '★ Favorit' : '☆ Favorit';
  $('#d-titel').textContent = (j.modus === 'bearbeiten' ? 'Geändertes Bild' : 'Neues Bild') + (j.dateien.length > 1 ? ` · Variante ${zustand.idx + 1} von ${j.dateien.length}` : '');
  const dauer = j.fertig && j.gestartet ? ` · ${Math.round((j.fertig - j.gestartet) / 60)} Min Rechenzeit` : '';
  $('#d-sub').textContent = `${zeit(j.angelegt || j.geaendert)} · Seed ${j.seed ?? '?'} · ${j.modus === 'bearbeiten' ? 'Auflösung ' + j.aufloesung : j.breite + 'x' + j.hoehe}${dauer}`;
}
function oeffneDetail(j) {
  zustand.detail = j; zustand.idx = 0;
  $('#d-prompt').textContent = j.prompt || '';
  $('#d-orig').classList.toggle('hidden', !j.vorlage);
  const minis = $('#d-minis'); minis.textContent = '';
  j.dateien.forEach((d, i) => { const m = document.createElement('img'); m.src = vorschauUrl(j, i); m.alt = ''; m.onclick = () => zeigeBild(i); minis.append(m); });
  minis.classList.toggle('hidden', j.dateien.length < 2);
  zeigeBild(0); $('#detail').classList.add('open');
}
function zeigeBild(i) {
  const j = zustand.detail; zustand.idx = i;
  $('#d-bild').src = bildUrl(j, j.dateien[i]); $('#d-dl').href = bildUrl(j, j.dateien[i]); $('#d-dl').download = `${j.id}-${i + 1}.png`;
  [...$('#d-minis').children].forEach((m, n) => m.classList.toggle('on', n === i)); detailKopf();
}
$('#d-zu').onclick = () => $('#detail').classList.remove('open');
$('#detail').onclick = e => { if (e.target.id === 'detail') $('#detail').classList.remove('open'); };
$('#d-fav').onclick = () => favorit(zustand.detail);
$('#d-orig').onclick = () => { $('#d-bild').src = `${API}/vorlage-bild/${zustand.detail.id}`; toast('Ausgangsfoto. Klick auf eine Variante zeigt wieder das Ergebnis.'); };
$('#d-weg').onclick = async () => {
  const j = zustand.detail;
  if (!confirm('Dieses Bild mit allen Varianten endgültig löschen?')) return;
  try { await api('/auftrag/' + j.id, 'DELETE'); $('#detail').classList.remove('open'); toast('Gelöscht.'); ladeArchiv(); ladeQueue(); }
  catch (e) { toast(e.message, 'err'); }
};
async function alsVorlage(j, datei) {
  const r = await api('/vorlage-aus-ergebnis', 'POST', {id: j.id, datei});
  vorlageSetzen(r.vorlage, bildUrl(j, datei));
}
$('#d-aendern').onclick = async () => {
  const j = zustand.detail;
  try { await alsVorlage(j, j.dateien[zustand.idx]); $('#detail').classList.remove('open'); location.hash = '#aendern'; toast('Bild ist als Vorlage eingesetzt.'); }
  catch (e) { toast(e.message, 'err'); }
};
$('#d-nochmal').onclick = async () => {
  const j = zustand.detail;
  $('#detail').classList.remove('open');
  if (j.modus === 'bearbeiten') {
    try {
      const blob = await api('/vorlage-bild/' + j.id);
      await dateiHochladen(new File([blob], 'foto.' + (blob.type.includes('png') ? 'png' : blob.type.includes('webp') ? 'webp' : 'jpg'), {type: blob.type}));
    } catch (e) { toast(e.message, 'err'); }
    $('#a-prompt').value = j.prompt || ''; aGroesse.set(j.aufloesung || 1024); aAnzahl.set(j.anzahl || 1); aendSumme(); location.hash = '#aendern';
  } else {
    $('#n-prompt').value = j.prompt || ''; $('#n-text').value = '';
    const f = FORMATE.map(x => [x[0], Math.abs(x[2] / x[3] - j.breite / j.hoehe)]).sort((a, b) => a[1] - b[1])[0][0];
    nFormat.set(f); nGroesse.set(GROESSEN.map(g => g[0]).sort((a, b) => Math.abs(a - Math.max(j.breite, j.hoehe)) - Math.abs(b - Math.max(j.breite, j.hoehe)))[0]);
    nAnzahl.set(j.anzahl || 1); neuSumme(); location.hash = '#neu';
  }
  toast('Einstellungen übernommen. Seed leer = anderes Ergebnis.');
};
$('#a-archiv').onclick = async () => {
  await ladeArchiv();
  const grid = $('#w-grid'); grid.textContent = '';
  for (const j of zustand.archiv.filter(x => x.zustand === 'fertig' && x.dateien.length)) {
    grid.append(kachel(j, async () => { try { await alsVorlage(j, j.dateien[0]); $('#wahl').classList.remove('open'); } catch (e) { toast(e.message, 'err'); } }));
  }
  $('#wahl').classList.add('open');
};
$('#w-zu').onclick = () => $('#wahl').classList.remove('open');

// ---------------------------------------------------------------- Einstellungen
async function ladeEinstellungen() {
  try {
    const e = await api('/einstellungen');
    $('#e-tage').value = String(e.aufbewahren_tage);
    if ($('#e-tage').value !== String(e.aufbewahren_tage)) { const o = document.createElement('option'); o.value = e.aufbewahren_tage; o.textContent = `${e.aufbewahren_tage} Tagen`; $('#e-tage').append(o); $('#e-tage').value = String(e.aufbewahren_tage); }
    const feld = $('#e-stats'); feld.textContent = '';
    for (const [num, cap] of [[e.auftraege, 'Aufträge im Archiv'], [gb(e.bytes), 'Speicher belegt'], [gb(e.frei), 'Platz frei auf dem Board']]) {
      const s = document.createElement('div'); s.className = 'stat'; const n = document.createElement('div'); n.className = 'num'; n.textContent = num;
      const c = document.createElement('div'); c.className = 'cap'; c.textContent = cap; s.append(n, c); feld.append(s);
    }
  } catch (e) { toast(e.message, 'err'); }
}
$('#e-speichern').onclick = async () => { try { await api('/einstellungen', 'POST', {aufbewahren_tage: Number($('#e-tage').value)}); toast('Gespeichert.'); ladeEinstellungen(); } catch (e) { toast(e.message, 'err'); } };
$('#e-jetzt').onclick = async () => {
  if (!confirm('Jetzt alle Bilder löschen, die älter als die eingestellte Zeit sind? Favoriten bleiben.')) return;
  try { const r = await api('/aufraeumen', 'POST', {}); toast(`${r.geloescht} Einträge gelöscht.`); ladeEinstellungen(); } catch (e) { toast(e.message, 'err'); }
};

// ---------------------------------------------------------------- Seiten
function seite() {
  const tab = (location.hash || '#neu').slice(1);
  const bekannt = ['neu', 'aendern', 'archiv', 'einstellungen'].includes(tab) ? tab : 'neu';
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('hidden', t.id !== 'tab-' + bekannt));
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('active', a.dataset.tab === bekannt));
  if (bekannt === 'archiv') ladeArchiv(); else if (bekannt === 'einstellungen') ladeEinstellungen();
}
window.addEventListener('hashchange', seite);
function start() {
  artGewaehlt(); seite(); ladeQueue(); bonsaiPill();
  setInterval(ladeQueue, 4000); setInterval(bonsaiPill, 10000);
  setInterval(() => { if (location.hash === '#archiv' && !$('#detail').classList.contains('open')) ladeArchiv(); }, 20000);
}
const urlApi = new URLSearchParams(location.search).get('api');
fetch('config.json', {cache: 'no-store'}).then(r => r.json()).then(c => { if (c.api) API = c.api; if (c.bonsai) BONSAI = c.bonsai; }).catch(() => {})
  .finally(() => { if (urlApi) API = urlApi; start(); });
