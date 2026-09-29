ARG UPSTREAM_IMAGE=ghcr.io/open-webui/computer:browser
FROM ${UPSTREAM_IMAGE} AS upstream-version
USER root
RUN python -c "import importlib.metadata,pathlib; pathlib.Path('/upstream-version').write_text(importlib.metadata.version('cptr'))"
FROM node:22-bookworm-slim AS node
FROM node AS frontend
RUN apt-get update && apt-get install -y --no-install-recommends git python3 ca-certificates && apt-get clean
COPY --from=upstream-version /upstream-version /upstream-version
RUN git clone --depth 1 --branch "v$(cat /upstream-version)" https://github.com/open-webui/computer.git /source
COPY scripts/patch_frontend.py /patch/scripts/patch_frontend.py
COPY frontend /patch/frontend
RUN python3 /patch/scripts/patch_frontend.py /source/cptr/frontend
WORKDIR /source/cptr/frontend
RUN npm ci --no-audit --no-fund && npm run build
FROM ${UPSTREAM_IMAGE}
USER root
RUN ln -s /home/cptr/.venv /opt/cptr
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && npm install -g @openai/codex @anthropic-ai/claude-code && apt-get update && apt-get install -y --no-install-recommends xvfb xauth curl openssh-client && apt-get clean
COPY patches /opt/selfwebui/patches
COPY scripts /opt/selfwebui/scripts
COPY tests /opt/selfwebui/tests
COPY integrations /opt/selfwebui/integrations
COPY extensions /opt/selfwebui/extensions
COPY --from=frontend /source/cptr/frontend/build /tmp/selfwebui-frontend
RUN python -c "import cptr,pathlib,shutil; shutil.copytree('/tmp/selfwebui-frontend',pathlib.Path(cptr.__file__).parent/'frontend/build',dirs_exist_ok=True)" && rm -rf /tmp/selfwebui-frontend
RUN python /opt/selfwebui/scripts/patch_runtime.py && node /opt/selfwebui/tests/proxy.cjs "$(python -c 'import cptr,pathlib; print(pathlib.Path(cptr.__file__).parent / "frontend/build/browser-runtime.js")')"
RUN python /opt/selfwebui/scripts/install_extensions.py
RUN python /opt/selfwebui/tests/test_controlled_worker.py && python /opt/selfwebui/tests/test_task_plan.py && python /opt/selfwebui/tests/test_loop_guard.py && python /opt/selfwebui/tests/test_extensions.py && node --check /opt/selfwebui/extensions/worker_panel.js && node --check /opt/selfwebui/extensions/direct_browser.js
ARG UPSTREAM_DIGEST=unknown
LABEL org.opencontainers.image.source="https://github.com/s3lfcod3r/selfwebui" io.selfwebui.upstream-digest="${UPSTREAM_DIGEST}"
ENV HOME=/data CPTR_DATA_DIR=/data CODEX_HOME=/data/codex CLAUDE_CONFIG_DIR=/data/claude
USER cptr
WORKDIR /data
EXPOSE 8000
HEALTHCHECK --interval=30s --start-period=45s --timeout=5s CMD curl -fsS http://127.0.0.1:8000/ >/dev/null || exit 1
CMD ["bash", "/opt/selfwebui/scripts/start.sh"]
