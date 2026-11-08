#!/usr/bin/env bash
set -euo pipefail
: "${SILENTCIPHER_SOURCE_ROOT:?Set SILENTCIPHER_SOURCE_ROOT to the existing official SilentCipher source checkout}"
: "${SILENTCIPHER_MODEL_DIR:?Set SILENTCIPHER_MODEL_DIR to the existing official 44.1 kHz weights}"
: "${V3_SOURCE_ROOT:?Set V3_SOURCE_ROOT to the frozen V3 checkout}"
PYTHON=${V4_STUDIO_PYTHON:-python3.12}
# The local-only UI has no outbound dependency; prevent incompatible inherited
# SOCKS proxy settings from breaking Gradio/httpx initialization.
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export GRADIO_ANALYTICS_ENABLED=False
THREADS=${V4_CPU_THREADS:-4}
export V4_CPU_THREADS="$THREADS"
export OMP_NUM_THREADS="$THREADS"
export MKL_NUM_THREADS="$THREADS"
export OPENBLAS_NUM_THREADS="$THREADS"
export NUMEXPR_NUM_THREADS="$THREADS"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec "$PYTHON" -m app.v4_studio_gui
