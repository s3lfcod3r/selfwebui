# selfwebui — Packaging for Open WebUI Computer

Community Docker build for **Open WebUI Computer (`cptr`)**, not the classic Open WebUI chat frontend. Upstream branding is preserved.

## Image and updates

`ghcr.io/s3lfcod3r/selfwebui:latest` (linux/amd64)

The workflow checks the official `ghcr.io/open-webui/computer:browser` image every six hours and on each push. It resolves an immutable upstream digest, applies guarded patches, runs URL regression tests and boots a fresh container before publishing. If upstream changes invalidate a patch, the build fails and the previous `latest` stays available. `build-N` tags support rollback. This creates updated images; it does **not** silently restart Unraid containers. GitHub can disable scheduled workflows in inactive public repositories after 60 days; check Actions if updates stop.

## Included

- Official Computer browser image with Chromium; Xvfb, Codex CLI and Claude Code CLI.
- Proxy fix for dynamically assigned script/image URLs and stylesheet URLs.
- Proxy fix for absolute URLs pointing at the embedding origin.
- Optional Bonsai worker MCP bridge and planner wrappers in `/opt/selfwebui/integrations`.
- Unraid template with upstream icon, project/support links and persistent `/data`.

## Unraid

Template: [unraid/selfwebui.xml](unraid/selfwebui.xml). Copy to `/boot/config/plugins/dockerMan/templates-user/my-selfwebui.xml`, then select it through Docker → Add Container. Prepare the appdata directory writable by UID/GID 1000:1000. No privileged mode, Docker socket or host filesystem mount is required. The browser worker and model server remain separate services.

For migration: stop the old container, back up `/data`, and reuse the existing data path in this template. Start only one container against that database. Existing chats, profiles, CLI logins and `/data/brain` files stay on disk. The old `/runtime` bind mount and `bash /runtime/start.sh` override are no longer needed. Keep the old image and backup for rollback. Review the limitations below before migrating production data.

## Browser limitations

Direct proxy mode renders HTML instead of video. Select proxy mode in Computer's browser settings. Login and Home widgets were tested in the customized 0.9.21 installation. **Office/Smart navigation in SelfDashboard remains unresolved.** CrowdSec sometimes reports a timeout. CI checks startup and URL handling, not authenticated dashboard functionality. Arbitrary websites are not guaranteed to work through a rewriting proxy.

## Subscription and worker configuration

Existing `/data` configuration is preserved; no credentials are shipped. For a fresh installation, log in through the CLI's supported flow. Optionally copy the files from `/opt/selfwebui/integrations` into `/data/brain`; configure the CLI MCP command as `python /data/brain/bonsai_mcp.py`. Store the existing worker token in `/data/brain/worker.key` (mode 600), and set `BONSAI_WORKER_URL` if required. The worker must expose the existing Bonsai API. Wrapper restrictions are workflow controls, not an OS security boundary. The new admin-only RTX panel reports worker phases, generated tokens and token/s from the model server. It shows all worker jobs in this installation, not only the current chat. Existing bridge copies in /data/brain must be updated to enable the default telemetry channel.

## Development

## Planner / worker setup

After restoring your existing worker credentials and bridge, run inside the container:

```sh
RTX_BASE_URL=http://YOUR-MODEL-SERVER:8085/v1 python /opt/selfwebui/scripts/configure_brains.py
```

Then restart Computer to refresh its configuration caches. The opt-in script preserves other connections and registers `RTX2000/bonsai-2-27b` (override `RTX_MODEL` if needed). ChatGPT and Claude use the existing planner wrappers and external RTX worker. The local RTX planner uses Computer's real child chats through `delegate_task`; each child has its own context and calls the existing Bonsai worker bridge. Child chats cannot recursively delegate. Jobs are sequential, background delegation is disabled, and direct local filesystem/shell tools are disabled for this local model. These are separate contexts on one GPU, not extra GPU instances. Existing child-chat tool approval behavior is inherited from Computer.

The script requires `/data/brain/worker.key` and `/data/brain/bonsai_mcp.py`; it does not create or publish secrets. A backup before changing configuration is recommended. The worker API and model server are separate existing services.

## Build locally

`docker build -t selfwebui:test .`

The build runs the patch regression test. Runtime settings, accounts, chats, SSH keys and model credentials must never be committed. See [NOTICE.md](NOTICE.md) for upstream attribution.

## Direct worker browser

Open **Arbeiter-Browser**, enter a URL, and log in manually. Click **Arbeiter verbinden** to let the existing worker read and operate that same visible HTML frame. **Selbst übernehmen** returns manual control. Keep this tab visible; inactive tabs stop polling. This is direct HTML, not a video stream. Only one browser controller is connected at a time. Ordinary Computer browser tabs are not automatically connected.

The optional integration requires the existing Bonsai worker service and matching worker key on both sides. On the worker host, copy `integrations/direct_browser_client.py` and `integrations/install_worker_bridge.py` together, then run:

```sh
python install_worker_bridge.py --app-dir /PATH/TO/WORKER/app --config-dir /PATH/TO/WORKER/geheim --computer-url http://OpenWebUI-Computer:8000
```

Set `direct-browser.json` ownership to the worker service UID (99:100 for the existing Unraid service), preserve mode 600, and restart the worker. Both containers must share a Docker network. This installer patches only the supported existing `browser_tools.py`; it is not a replacement worker service. Disable the relay by moving `direct-browser.json` aside and restarting the worker; the original browser implementation remains present.

The worker receives visible text and element references, with form values omitted. Clicks and text entry still require the worker job's interactive flag. Credential entry remains manual. Screenshots of this local HTML view are unsupported by the server; the worker returns an explicit explanation rather than an image from another session. Modern web applications can still have proxy compatibility limitations.
