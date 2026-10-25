# Blind Audio Watermarking — Public Course Demo

This repository is a clean, standalone export of the frozen Course V2 blind
audio watermarking demonstration. It is intended for local teaching demos and
review, not as a claim that the research prototype has passed a new independent
public benchmark.

## What is included

- REAL_TOP32 codec-aware carrier selection with the frozen public map.
- The original arbitrary 32-bit blind payload API.
- Four-identity mode using fixed 32-bit codewords with minimum pairwise Hamming
  distance 21. The effective identity information is 2 bits; identity accuracy
  must not be read as arbitrary 32-bit message recovery.
- Frozen operating point: strength `1.28`, rejection threshold `8`, payload
  seed `7`.
- Real FFmpeg MP3 128 kbps round-trip.
- A small Gradio interface and a separate blind detector process.
- Generated test-signal smoke tests; no raw dataset audio is distributed.

## V3 8-bit local integration candidate

The repository also contains a separate, frozen V3 8-bit Soft-Code local
integration candidate. It uses `strength=1.60`, `REAL_TOP32`, seed `7`, and a
six-second block; the detector is blind and returns `IDENTIFIED` or `UNKNOWN`.
It does not replace the Course V2 entry point or its historical results.

```bash
PYTHONPATH=src:scripts:. python examples/generate_test_audio.py --output /tmp/v3_demo_input.wav
PYTHONPATH=src:scripts:. python scripts/v3_p3_acceptance.py --output-dir /tmp/v3_p3_acceptance
PYTHONPATH=src:scripts:. python gradio_v3_app.py
```

The V3 integration is local-only and has not been deployed to Render. See
[`docs/V3_P3_INTEGRATION.md`](docs/V3_P3_INTEGRATION.md) and the Chinese
acceptance record [`docs/V3_P3_ACCEPTANCE_ZH.md`](docs/V3_P3_ACCEPTANCE_ZH.md)
for the frozen contract, P2-V evidence boundary, and listening limitations.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[gui,dev]'
python examples/generate_test_audio.py --output /tmp/watermark_test_signal.wav
python scripts/demo.py --input /tmp/watermark_test_signal.wav --identity UESTC-003 --codec mp3
python -m app.gui
```

The GUI binds to `127.0.0.1` and does not request a public share URL. FFmpeg is
required for MP3 encoding/decoding. The CLI output directory contains the
prepared original, watermarked WAV, MP3, decoded WAV, and blind-detector JSON
result. Generated audio is intentionally not tracked by Git.

## Blind detector contract

`scripts/detect.py` and `python -m app.detector_worker` accept only the received
audio and optional public map path. They do not accept an expected identity,
clean audio, original payload, filename label, or answer cache. A decoded word
outside the frozen Hamming threshold is reported as `UNKNOWN`.

## Evidence and scope

The historical Course V2 results are reproduced as provenance in
[`docs/RESULTS.md`](docs/RESULTS.md); this clean export does not claim to have
re-run the 48/48 no-attack or 46/48 MP3 validation matrix. See
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) before presenting the demo.

The frozen calibration/validation records used external MUSAN recordings from
[OpenSLR SLR17](https://www.openslr.org/17/). This repository distributes no
MUSAN audio, archive, or per-recording source manifest. It publishes only the
aggregate frozen statistics and cites the source dataset; OpenSLR identifies
SLR17 as CC BY 4.0. Users must preserve the upstream attribution and comply
with the applicable source terms.

## License and data status

The project code in this staging is released under the MIT License. NumPy,
SciPy, pytest, Gradio, FFmpeg, and other dependencies remain external and
retain their own licenses. No MUSAN or other raw audio is included. The frozen
results cite the external source dataset and do not grant permission to
redistribute its recordings.
