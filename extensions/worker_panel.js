(() => {
  if (window.top !== window || document.getElementById('selfwebui-worker')) return;
  const host = document.createElement('div'); host.id = 'selfwebui-worker';
  host.style.cssText = 'position:fixed;right:16px;bottom:14px;z-index:90;font:13px system-ui;color:#e8edf3';
  const shadow = host.attachShadow({mode:'open'});
  shadow.innerHTML = `<style>button{font:inherit;color:inherit;cursor:pointer;border:1px solid #3d5262;border-radius:10px;background:#14212b;padding:9px 13px}section{width:300px;max-height:45vh;overflow:auto;background:#111b24;border:1px solid #3d5262;border-radius:12px;padding:14px;margin-bottom:8px;box-shadow:0 8px 28px #0008}p{margin:8px 0;color:#acbac9}.job{border-top:1px solid #32404b;padding:9px 0;line-height:1.6}.muted{font-size:11px;color:#9aabba}[hidden]{display:none}</style><section hidden><strong>RTX2000 · Arbeiter</strong><p>Alle Arbeiteraufträge dieser Installation</p><div id="jobs"></div><p class="muted">Token/s: Messung des Modellservers, einschließlich Denktokens. Werkzeug- und Wartezeiten zählen nicht zur Rate.</p></section><button type="button" aria-expanded="false">RTX2000 · Status laden</button>`;
  document.body.append(host);
  const button = shadow.querySelector('button'), panel = shadow.querySelector('section'), list = shadow.querySelector('#jobs');
  button.onclick = () => {panel.hidden = !panel.hidden;button.setAttribute('aria-expanded',String(!panel.hidden));};
  const phases = {waiting:'Übergabe',starting:'Startet',prompt:'Liest Kontext',generating:'Erzeugt Tokens',evaluating:'Prüft Antwort',tool:'Werkzeug läuft',fertig:'Abgeschlossen',erledigt:'Abgeschlossen',gescheitert:'Fehlgeschlagen',bonsai_beschaeftigt:'Belegt',bonsai_nicht_verfuegbar:'Nicht verfügbar',unknown:'Status unbekannt'};
  const terminal = new Set(['fertig','erledigt','gescheitert','bonsai_beschaeftigt','bonsai_nicht_verfuegbar']);
  function label(job) {return job.stale ? 'Keine aktuellen Messwerte' : phases[job.phase] || 'Unbekannt';}
  async function poll() {
    try {
      if (document.hidden) return;
      const response = await fetch('/api/selfwebui/worker/status',{cache:'no-store'});
      if (response.status === 401 || response.status === 403) {host.hidden=true;return;}
      if (!response.ok) throw Error('offline');
      host.hidden=false;
      const {jobs} = await response.json();
      const active = jobs.find(j=>!terminal.has(j.phase)&&!j.stale);
      button.textContent = 'RTX2000 · ' + (active ? label(active) + (Number.isFinite(active.tps)?` · ${active.tps.toFixed(1)} Token/s`:'') : 'Bereit');
      list.replaceChildren();
      if (!jobs.length) list.textContent='Noch kein Arbeiterauftrag gemessen.';
      for (const job of jobs.slice(0,8)) {
        const item=document.createElement('div');item.className='job';
        const seconds=Math.max(0,Math.round((job.ended||Date.now()/1000)-(job.started||Date.now()/1000)));
        const rate=terminal.has(job.phase)?job.last_tps:job.tps;
        item.textContent=`${label(job)} · ${seconds}s\n${job.tokens||0} Tokens · ${Number.isFinite(rate)?rate.toFixed(1)+' Token/s':'Rate noch nicht verfügbar'} · ${job.tools||0} Werkzeuge`;
        item.style.whiteSpace='pre-line';list.append(item);
      }
    } catch {button.textContent='RTX2000 · Status nicht erreichbar';}
    finally {setTimeout(poll,1000);}
  }
  poll();
})();
