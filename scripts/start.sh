#!/bin/bash
set -euo pipefail
mkdir -p /data/workspaces
exec xvfb-run -a -s '-screen 0 1600x1000x24 -nolisten tcp' cptr run --host 0.0.0.0 --port 8000 --headless
