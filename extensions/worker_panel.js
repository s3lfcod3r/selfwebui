(() => {
  if (window.top !== window || document.getElementById('selfwebui-worker')) return;
  const WIDTH = 320, RAIL = 40, KEY = 'selfwebui-worker-collapsed';
  const host = document.createElement('div'); host.id = 'selfwebui-worker';
  host.style.cssText = 'position:fixed;top:0;right:0;bottom:0;z-index:90;font:13px system-ui;color:#e8edf3';
  const shadow = host.attachShadow({mode:'open'});
  shadow.innerHTML = `<style>
    *{box-sizing:border-box}
    aside{height:100%;display:flex;flex-direction:column;background:#0f1922;border-left:1px solid #2c3b47}
    header{display:flex;align-items:center;gap:8px;padding:12px 12px 10px;border-bottom:1px solid #2c3b47}
    header strong{flex:1;font-size:13px;letter-spacing:.02em}
    button{font:inherit;color:inherit;cursor:pointer;border:1px solid #3d5262;border-radius:8px;background:#14212b;padding:4px 9px}
    button:hover{background:#1b2c39}
    .state{padding:8px 12px;font-size:12px;color:#acbac9;border-bottom:1px solid #2c3b47;display:flex;align-items:center;gap:8px}
    .chips{display:flex;flex-wrap:wrap;gap:6px;padding:8px 10px;border-bottom:1px solid #2c3b47}
    .chip{padding:3px 9px;border-radius:12px;font-size:11.5px;background:#14212b}
    .chip.on{background:#2b6b93;border-color:#6cc4ff}
    .list{flex:1;overflow:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
    h3{margin:6px 2px 0;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#7f93a4}
    .job{display:grid;grid-template-columns:22px 1fr;gap:4px 9px;padding:10px;border:1px solid #2c3b47;border-radius:10px;background:#131f29}
    .job.ok{border-color:#2f6b45}
    .job.err{border-color:#8a3a3a}
    .job.warn{border-color:#8a6d2a}
    .job.flash{animation:flash 1.6s ease-out 4}
    @keyframes flash{0%{box-shadow:0 0 0 0 #3fb96866}100%{box-shadow:0 0 0 12px #3fb96800}}
    .ico{width:22px;height:22px;flex:none;border-radius:50%;display:grid;place-items:center;font-size:13px;font-weight:700;line-height:1}
    .ico.ok{background:#3fb968;color:#07210f}
    .ico.err{background:#e05252;color:#2b0808}
    .ico.warn{background:#e0a93a;color:#2b1d05}
    .ico.idle{background:#33424f;color:#c5d0da}
    .ico.run{border:2.5px solid #38566b;border-top-color:#6cc4ff;background:none;animation:spin .9s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .title{font-weight:600;line-height:1.3;overflow-wrap:anywhere}
    .meta{grid-column:2;font-size:11.5px;color:#9aabba;line-height:1.5;white-space:pre-line}
    .bar{grid-column:2;height:4px;border-radius:2px;background:#25343f;overflow:hidden}
    .bar i{display:block;height:100%;background:#6cc4ff}
    .job.ok .bar i{background:#3fb968}
    details{grid-column:2;margin-top:2px}
    summary{cursor:pointer;color:#6cc4ff;font-size:12px}
    .body{max-height:220px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;margin-top:6px;color:#cbd6df}
    .empty{color:#7f93a4;padding:6px 2px}
    .foot{padding:8px 12px;border-top:1px solid #2c3b47;font-size:10.5px;color:#7f93a4}
    .rail{display:none;height:100%;width:${RAIL}px;flex-direction:column;align-items:center;gap:10px;padding-top:12px;background:#0f1922;border-left:1px solid #2c3b47}
    .badge{min-width:22px;padding:2px 5px;border-radius:11px;font-size:11px;text-align:center;background:#33424f}
    .badge.run{background:#2b6b93}
    .badge.ok{background:#2f8a52}
    .badge.err{background:#a04040}
    .rail .t{writing-mode:vertical-rl;font-size:11px;color:#9aabba;letter-spacing:.06em}
    :host(.collapsed) aside{display:none}
    :host(.collapsed) .rail{display:flex}
    :host([hidden]){display:none}
  </style>
  <aside aria-label="RTX2000 Arbeiter-Status">
    <header><strong>RTX2000 · Arbeiter</strong><button type="button" id="min" title="Einklappen" aria-label="Spalte einklappen">›</button></header>
    <div class="state" id="state">Status wird geladen …</div>
    <div class="chips" id="chips" hidden></div>
    <div class="list" id="jobs"></div>
    <div class="foot">Token/s: Messung des Modellservers inkl. Denktokens. Werkzeug- und Wartezeiten zählen nicht.</div>
  </aside>
  <div class="rail"><button type="button" id="max" title="Ausklappen" aria-label="Spalte ausklappen">‹</button><span class="badge" id="badge">–</span><span class="t">Arbeiter</span></div>`;
  document.body.append(host);
  const $ = id => shadow.getElementById(id);
  const list = $('jobs'), state = $('state'), badge = $('badge'), chips = $('chips');
  const FILTER_KEY = 'selfwebui-worker-filter';
  let filter = '';
  try { filter = localStorage.getItem(FILTER_KEY) || ''; } catch {}
  const phases = {waiting:'Übergabe',starting:'Startet',prompt:'Liest Kontext',generating:'Erzeugt Tokens',evaluating:'Prüft Antwort',tool:'Werkzeug läuft',fertig:'Fertig',erledigt:'Fertig',teilweise:'Teilweise fertig',gescheitert:'Fehlgeschlagen',bonsai_beschaeftigt:'Belegt',bonsai_nicht_verfuegbar:'Nicht verfügbar',unknown:'Status unbekannt'};
  const terminal = new Set(['fertig','erledigt','teilweise','gescheitert','bonsai_beschaeftigt','bonsai_nicht_verfuegbar']);
  const isOk = job => job.phase === 'fertig' || job.phase === 'erledigt';
  const kindOf = job => isOk(job) ? 'ok'
    : job.phase === 'gescheitert' ? 'err'
    : job.phase === 'teilweise' ? 'warn'
    : terminal.has(job.phase) || job.stale ? 'idle' : 'run';
  const glyph = {ok:'✓', err:'✕', warn:'!', idle:'–', run:''};
  const expanded = new Set(), seen = new Map(), flashUntil = new Map();
  let firstPoll = true, collapsed = false;
  try { collapsed = localStorage.getItem(KEY) === '1'; } catch {}

  function layout() {
    const px = (collapsed ? RAIL : WIDTH) + 'px';
    host.classList.toggle('collapsed', collapsed);
    host.style.width = px;
    // Shrink the app instead of overlaying it: a fixed column, not a floating popup.
    document.body.style.width = document.body.style.maxWidth = `calc(100% - ${px})`;
  }
  function setCollapsed(value) {
    collapsed = value;
    try { localStorage.setItem(KEY, value ? '1' : '0'); } catch {}
    layout();
  }
  $('min').onclick = () => setCollapsed(true);
  $('max').onclick = () => setCollapsed(false);
  layout();

  function label(job) { return job.stale ? 'Keine aktuellen Messwerte' : phases[job.phase] || 'Unbekannt'; }
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function card(job) {
    const kind = kindOf(job);
    const item = el('div', 'job' + (kind === 'ok' || kind === 'err' || kind === 'warn' ? ' ' + kind : ''));
    if ((flashUntil.get(job.id) || 0) > Date.now()) item.classList.add('flash');
    const icon = el('div', 'ico ' + kind, glyph[kind]);
    icon.setAttribute('aria-label', label(job));
    item.append(icon, el('div', 'title', (job.projekt ? job.projekt + ' · ' : '') + (job.titel || 'RTX-Arbeiterauftrag')));
    const seconds = Math.max(0, Math.round((job.ended || Date.now() / 1000) - (job.started || Date.now() / 1000)));
    const rate = terminal.has(job.phase) ? job.last_tps : job.tps;
    const step = job.schritt ? `Schritt ${job.schritt}/${job.gesamt} · ` : '';
    item.append(el('div', 'meta',
      `${step}${label(job)} · ${seconds}s\n${job.tokens || 0} Tokens · ${Number.isFinite(rate) ? rate.toFixed(1) + ' Token/s' : 'Rate n. v.'} · ${job.tools || 0} Werkzeuge`));
    if (job.schritt && job.gesamt) {
      const bar = el('div', 'bar'), fill = document.createElement('i');
      const done = isOk(job) ? job.gesamt : Math.max(0, job.schritt - 1) + (terminal.has(job.phase) ? 1 : 0.5);
      fill.style.width = Math.min(100, Math.round(done / job.gesamt * 100)) + '%';
      bar.append(fill); item.append(bar);
    }
    if (job.bericht) {
      const details = document.createElement('details');
      details.append(el('summary', '', 'Ergebnis ansehen'), el('div', 'body', 'Auftrag-ID: ' + (job.plan || job.id) + '\n\n' + job.bericht));
      details.open = expanded.has(job.id);
      details.ontoggle = () => { if (details.open) expanded.add(job.id); else expanded.delete(job.id); };
      item.append(details);
    }
    return item;
  }
  function renderChips(jobs) {
    const projects = [...new Set(jobs.map(j => j.projekt).filter(Boolean))].sort();
    if (filter && !projects.includes(filter)) filter = '';
    chips.hidden = projects.length < 2;
    chips.replaceChildren();
    for (const name of ['', ...projects]) {
      const count = name ? jobs.filter(j => j.projekt === name).length : jobs.length;
      const chip = el('button', 'chip' + (name === filter ? ' on' : ''), `${name || 'Alle'} · ${count}`);
      chip.type = 'button';
      chip.onclick = () => {
        filter = name;
        try { localStorage.setItem(FILTER_KEY, filter); } catch {}
        poll(true);
      };
      chips.append(chip);
    }
  }
  function section(name, jobs) {
    return jobs.length ? [el('h3', '', `${name} (${jobs.length})`), ...jobs.map(card)] : [];
  }
  function trackDone(jobs) {
    for (const job of jobs) {
      const before = seen.get(job.id);
      if (!firstPoll && before && !terminal.has(before) && isOk(job)) flashUntil.set(job.id, Date.now() + 7000);
      seen.set(job.id, job.phase);
    }
    firstPoll = false;
  }
  let timer = 0;
  async function poll(now) {
    if (now) clearTimeout(timer);
    try {
      if (document.hidden) return;
      const response = await fetch('/api/selfwebui/worker/status', {cache: 'no-store'});
      if (response.status === 401 || response.status === 403) {
        host.hidden = true; document.body.style.width = document.body.style.maxWidth = ''; return;
      }
      if (!response.ok) throw Error('offline');
      if (host.hidden) { host.hidden = false; layout(); }
      const {jobs: all, bonsai} = await response.json();
      trackDone(all);
      renderChips(all);
      const jobs = filter ? all.filter(j => j.projekt === filter) : all;
      const allRunning = all.filter(j => kindOf(j) === 'run');
      const running = jobs.filter(j => kindOf(j) === 'run');
      const finished = jobs.filter(j => kindOf(j) !== 'run');
      const active = allRunning[0];
      const model = {bereit: ['ok', '✓', 'Bonsai bereit'], laedt: ['warn', '…', 'Bonsai lädt das Modell'], aus: ['err', '✕', 'Bonsai aus (GPU belegt oder gestoppt)']}[bonsai];
      const idle = model ? model[2] : 'Bereit';
      state.replaceChildren(el('span', 'ico ' + (active ? 'run' : model ? model[0] : 'ok'), active ? '' : model ? model[1] : '✓'),
        el('span', '', active ? label(active) + (Number.isFinite(active.tps) ? ` · ${active.tps.toFixed(1)} Token/s` : '') : idle));
      const okCount = all.filter(j => kindOf(j) === 'ok').length;
      const errCount = all.filter(j => kindOf(j) === 'err').length;
      const bonsaiAus = bonsai === 'aus';
      badge.className = 'badge ' + (bonsaiAus ? 'err' : allRunning.length ? 'run' : errCount ? 'err' : okCount ? 'ok' : '');
      badge.textContent = bonsaiAus ? 'aus' : allRunning.length ? String(allRunning.length) : errCount ? '✕' : okCount ? '✓' : '–';
      list.replaceChildren();
      if (!jobs.length) list.append(el('div', 'empty', filter ? 'Keine Aufträge in diesem Projekt.' : 'Noch kein Arbeiterauftrag gemessen.'));
      else list.append(...section('Läuft', running), ...section('Erledigt', finished.slice(0, 12)));
    } catch { state.textContent = 'Status nicht erreichbar'; badge.className = 'badge err'; badge.textContent = '?'; }
    finally { timer = setTimeout(poll, 1000); }
  }
  poll();
})();
