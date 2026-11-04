# V3 P3 Integration Candidate

This document packages the frozen V3 8-bit Soft-Code candidate for local
integration. It does not change the Course V2 implementation, the B1/QIM
core, the REAL_TOP32 map, historical experiments, or the public deployment.

## Frozen candidate

The operating point is inherited from the V3-P2-V source-disjoint validation;
it was not selected from the P3 acceptance smoke:

| Item | Frozen value |
| --- | --- |
| Effective payload | 8 bits (`0..255`) |
| Physical channel | 32 bits, frozen B1 Soft-Code |
| Strength | `1.60` |
| Presence threshold | `0.7855073980199624` |
| Selector | `REAL_TOP32` |
| Watermark seed | `7` |
| Sample rate | 48 kHz mono |
| V3 block | 6 seconds, zero-padding for shorter input |
| MP3 check | FFmpeg `libmp3lame`, 128 kbps |

The hash-complete freeze record is
`configs/v3_8bit_candidate_freeze.json`. The legacy Course V2 public operating
point remains strength `1.28` with rejection threshold `8`; the legacy values
inside selector provenance are historical metadata and are not V3 parameters.

## Blind API

```python
from app.v3_api import embed_message, detect_message

marked = embed_message(clean_audio, 173)
result = detect_message(marked.audio)
```

The public V3 adapter exposes `embed_message(audio, message)` and
`detect_message(audio)`. The message is an integer in `0..255`. Detection
receives only the received `AudioData` plus the frozen public configuration and
selector; it does not receive expected payload, clean audio, filename labels,
or embedding-session state. A decision is `IDENTIFIED` with an integer message
or `UNKNOWN` with no message.

Input is converted to 48 kHz mono and the V3 candidate uses a six-second
block. Audio longer than the public 30-second input limit is rejected. The
accepted demo input limit is 64 MiB. These are local demo limits, not a claim
of production service hardening.

## Local commands

```bash
PYTHONPATH=src:scripts:. python examples/generate_test_audio.py \
  --output /tmp/v3_demo_input.wav
PYTHONPATH=src:scripts:. python scripts/v3_demo.py \
  --input /tmp/v3_demo_input.wav --message 173 --codec mp3 \
  --output-dir /tmp/v3_demo_run
PYTHONPATH=src:scripts:. python scripts/v3_demo.py \
  --detect-input /tmp/v3_demo_run/compressed_128k_decoded.wav
PYTHONPATH=src:scripts:. python scripts/v3_p3_acceptance.py \
  --output-dir /tmp/v3_p3_acceptance
PYTHONPATH=src:scripts:. python scripts/v3_p3_listening_pack.py \
  --input /tmp/v3_demo_input.wav --output-dir /tmp/v3_p3_listening
```

`v3_p3_acceptance.py` writes metadata/results only to the requested report
directory. Generated audio for the smoke is temporary. The listening command
intentionally writes an explicit A/B pack to the requested path; keep that path
outside Git and delete it when no longer needed.

Real FFmpeg is a hard acceptance prerequisite: when it is unavailable, the
report records `mp3_roundtrip = BLOCKED`, `status = BLOCKED`, and the blocker
`FFMPEG_UNAVAILABLE`; it must never report overall PASS. The wrong-key gate is
also strict: it passes only when the detector returns `UNKNOWN` with
`message = None`. The CLI fallback has a bounded 120-second timeout, and
unexpected acceptance exceptions are retained in the JSON report.

The local GUI entry point is:

```bash
PYTHONPATH=src:scripts:. python gradio_v3_app.py
```

It binds to localhost with `share=False`. A pinned Gradio 4.44.1 environment
is optional and is not installed by the core package.

## GUI mode separation

The integration GUI has two explicit modes:

- **V3 8-bit Soft-Code**: the frozen six-second V3 adapter, independent blind
  detection, and real MP3 128 kbps round trip.
- **Legacy Course V2**: the existing Course V2 identity/payload flow, including
  its historical 6/15/30-second controls.

The current Course V2 entry point and callbacks remain unchanged. V3 is an
additional local integration entry point, not a replacement for the historical
demo or its results.

## Evidence boundary

The V3-P2-V independent validation reported the following MP3 128 kbps
results:

| Candidate | Accepted exact trials | Accepted exact sources |
| --- | ---: | ---: |
| 8-bit Soft-Code | 117/120 | 58/60 |
| 12-bit Soft-Code | 97/120 | 45/60 |

Those values are prior source-disjoint validation evidence, not new P3 smoke
results. The P3 acceptance command checks four deterministic local messages,
clean-audio rejection, a wrong-key probe, guards, session cleanup, CLI
fallback, and one real FFmpeg round trip. It must not be used to expand the
historical benchmark.

The P2-V negative controls were finite: for 8-bit, clean FPR was 0/60 and
clean-MP3 FPR was 1/60; wrong-key MP3 acceptance was 0/120. These observations
do not establish a population FPR below 1%. The detector reports `UNKNOWN`
when its frozen presence rule rejects an input; no cached expected answer is
used.

The formal reliability evidence covers six seconds and one V3 block only. The
Course V2 15/30-second modes remain historical/legacy functionality and must
not be described as V3 validation. Real MP3 support here means local FFmpeg
`libmp3lame` 128 kbps encode/decode.

`FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`. The listening pack is only a
preliminary listening screening aid and does not prove imperceptibility.

## Deployment boundary

This stage is local-only. No Render deployment, public website replacement,
cloud upload service, or public share URL is part of this candidate. The
acceptance report therefore records:

`RENDER_FEASIBILITY = LOCAL_PROXY_ONLY`

Any future deployment requires a separate resource, privacy, browser, and
multi-user security review.
