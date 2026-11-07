#!/usr/bin/env bash
set -euo pipefail
: "${SILENTCIPHER_SOURCE_ROOT:?Set SILENTCIPHER_SOURCE_ROOT to the existing official source checkout}"
: "${SILENTCIPHER_MODEL_DIR:?Set SILENTCIPHER_MODEL_DIR to the existing official 44.1 kHz model directory}"
PYTHON=${V4_P2_PYTHON:-python3}
exec "$PYTHON" -m app.v4_p2_gui
