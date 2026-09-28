# SelfDashboard adapter

Small read-only compatibility service for the existing `llm-token` and `openclaw-status` widgets. `/tokens` reads llama.cpp `/metrics` and persists daily deltas. `/status` reads project STATUS.md files plus the latest SelfWebUI worker telemetry. It never reads chat bodies, login files or API keys.

Run `python service.py` with Python 3.12. The container listens on 8098; the existing installation publishes both 8097 and 8098 to this port so widget URLs remain valid. Mount:

- this directory at `/app:ro`, workdir `/app`
- writable history directory at `/daten` (UID 1000)
- `/usr/share/zoneinfo:ro` for Europe/Berlin daylight-saving time
- existing worker `brain/live` at `/worker-live:ro` (same UID as the worker telemetry writer)
- project roots at `/projekte:ro` and `/code:ro`
- SelfWebUI workspaces at `/workspaces:ro`
- optional Bonsai update directory at `/updates:ro`

Set `SERVER=RTX2000=http://YOUR-MODEL-SERVER:8085`, `PROJEKTE==/projekte,Code=/code,SelfWebUI=/workspaces`, and optionally `ABSTAND_SEKUNDEN=15`. Use `python:3.12-alpine` with a read-only root filesystem, no added capabilities, no-new-privileges, 128 MB memory and a small /tmp tmpfs. Health endpoint: `/health`.

Back up the old `verlauf.json` before migrating. Copy it into the new history directory. If renaming the same model server (for example Board to RTX2000), rename its `server|NAME|ein` and `server|NAME|aus` keys in `roh` and every `tage` entry, and its name in every `spitze` entry, **before the first poll**. Otherwise the existing cumulative counter would be counted a second time. Historical OpenClaw agent rows remain explicitly labelled as historical. Totals follow model-server counters, so agent rows are not added again. ChatGPT/Claude subscription usage is not included in RTX totals.

Project states come from existing files, not guesses about chat text. A completed worker job is not proof that an entire project is complete. The worker row therefore describes only the latest job. Update STATUS.md during real project work, using `## Aufgaben` entries like `- Feature — in Arbeit: remaining work` and `## Offene Fragen`. Remove questions only after they have been resolved.

Run `python test_dashboard.py` for counter deduplication, reset handling and separation of historical agent totals.
