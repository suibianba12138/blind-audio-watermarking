# V3 8-bit Candidate Integration Design

## Status

Approved direction: separate V3 adapter and integration entry point, while
preserving the existing Course V2 implementation and entry point.

Base branch:

`research/v3-p2-validation@2c6f53cddf7ba67ffcabe9f3f3744f6279a71cdc`

Integration branch:

`feat/v3-8bit-integration`

## Goals and non-goals

The goal is to package the independently validated V3 8-bit Soft-Code method
as a formal local candidate and make it ready for later GitHub Pages/Render
integration. The implementation must support a real local flow: decode or
upload audio, embed a chosen integer message, listen to original and marked
audio, perform real FFmpeg MP3 128 kbps round-trip, and blind-detect an
independently uploaded received file.

The following are explicitly out of scope:

- Any QIM, codebook, strength, selector, threshold, or fusion change.
- Restarting the rejected 12-bit or 16-bit candidates.
- Claiming arbitrary 32-bit message recovery.
- Claiming 15/30-second V3 performance. The validated V3 protocol is one
  six-second block; Course V2 retains its existing 6/15/30-second identity
  modes.
- Replacing or silently changing the existing Course V2 API, historical
  metrics, public pages, or production Render service.

## Frozen V3 configuration

The candidate uses the exact V3-P2-V validated operating point:

- 48 kHz mono processing, six-second first-prefix block, zero-padding for
  shorter audio after the existing bounded input checks.
- Existing 32-position `REAL_TOP32` carrier selector and watermark seed 7.
- Existing B1 embedding and detection implementation.
- Embedding strength `1.60`, represented as a V3-specific wrapper around the
  existing embedding configuration. The Course V2 public strength `1.28`
  remains unchanged.
- Existing 8-bit Soft-Code codebook, which is identical to the frozen B1
  8-bit codebook.
- Soft signed-statistic decoding through `decode_soft_capacity(..., 8)`.
- Presence acceptance threshold `0.7855073980199624`.
- Source and result provenance from `V3_P2_V_INDEPENDENT_VALIDATION.md`;
  MP3 claims are limited to the 60-source independent validation.

The branch will add a hash-addressed V3 freeze record containing the relevant
source/configuration SHA256 values and the P2-V result references. The freeze
record is documentation/provenance, not a second algorithm implementation.

## Public API

Create `app/v3_api.py` as a narrow adapter over the frozen modules:

```python
def embed_message(audio: AudioData, message: int) -> V3EmbedResult:
    """Embed one integer message in the bounded six-second V3 block."""

def detect_message(audio: AudioData) -> V3DetectionResult:
    """Blindly detect one V3 message from received audio."""
```

`message` must be an integer in `[0, 255]`. It is converted to exactly eight
bits and then to the existing 32-position physical codeword. The detector has
no expected-message parameter and receives only prepared received audio plus
the frozen public selector/configuration.

`V3EmbedResult` contains the prepared marked `AudioData`, integer message,
duration, sample rate, and non-sensitive provenance. `V3DetectionResult`
contains `status` (`IDENTIFIED` or `UNKNOWN`), decoded integer or `None`,
presence score, frozen threshold, score margin, duration, sample rate, and
provenance. Invalid input raises a clear `ValueError`/`RuntimeError` at the
API boundary; a valid but unaccepted audio returns `UNKNOWN` rather than an
invented message.

The adapter accepts decoded mono `AudioData` and applies the fixed V3
preparation policy: resample to 48 kHz, reject inputs above the existing
30-second public bound, take the first six seconds, and zero-pad shorter
inputs. This makes alignment explicit and keeps the V3 detector and embedder
on the same protocol.

## Data flow and isolation

The new V3 path is split into small units:

1. `app/v3_api.py` owns only validation, preparation, frozen V3 embedding, and
   blind decoding.
2. `app/v3_detector_worker.py` is a subprocess boundary that accepts only an
   input file and emits structured detection JSON. It cannot receive an
   expected message, original audio, or GUI state.
3. `app/v3_pipeline.py` owns the local end-to-end workflow: session directory,
   original/marked WAV files, FFmpeg MP3 files, and a separate uploaded-file
   detection path.
4. `app/session_store.py` owns per-session temporary paths, size/age checks,
   cleanup, and safe deletion within a dedicated temporary root. No session
   may resolve a path belonging to another session.
5. `app/integration_gui.py` exposes a new Gradio entry point with two explicit
   modes: `V3 8-bit Soft-Code` and `Legacy Course V2`. Legacy actions delegate
   to the existing pipeline; V3 actions delegate to the new V3 pipeline. The
   existing `gradio_app.py` remains unchanged until a later deployment review.

The standalone CLI `scripts/v3_demo.py` provides the same V3 embed, optional
MP3 round-trip, blind detection, and separate-file detection path for use when
browser interaction is unavailable.

## GUI behavior

The new integration page follows the existing Audio Signal Studio style but
keeps the mode boundary visible:

- Mode and input selection.
- V3 message integer or Legacy identity selection.
- Original/prepared and watermarked audio playback.
- Real MP3 128 kbps encode/decode and playback.
- Separate received-file upload for blind detection.
- Detection headline `DETECTED: <0..255>` or `UNKNOWN / NO VALID WATERMARK`.
- Score, threshold, duration, sample rate, and processing time.
- A provenance note that the V3 MP3 evidence is independent 60-source
  validation, not universal accuracy.

The GUI may compare a detected message to the embedding label only after
detection for display. That comparison is never passed into the detector.

## Error and resource policy

Reuse the existing public limits unless a V3-specific test proves a narrower
safe bound:

- Maximum input file size: 64 MiB.
- Maximum decoded duration before preparation: 30 seconds.
- V3 processing block: exactly 6 seconds at 48 kHz mono.
- FFmpeg encode/decode timeout: 120 seconds per subprocess call.
- Localhost-only launch by default; no `share=True`.
- Per-session temporary directory with cleanup on success, failure, and TTL
  expiration. Cleanup must never use a broad workspace path.
- Malformed, empty, non-finite, unsupported, or over-limit inputs produce a
  user-readable error and do not create a detector result.

## Testing and evidence gates

Tests are added before implementation for:

- Message range and exact 8-bit conversion.
- No-attack V3 embed/detect on fixed 6-second audio.
- Blind detector signature and no expected-message data flow.
- Correct message, wrong message scoring, UNKNOWN clean audio, and wrong-key
  behavior.
- Real FFmpeg MP3 128 kbps end-to-end behavior.
- 6/15/30 duration handling: V3 explicitly remains six-second-only at the
  algorithm boundary; Legacy Course V2 continues its existing modes.
- File-size, duration, invalid-file, timeout, and cleanup behavior.
- Session path isolation and expiry cleanup.
- GUI construction smoke and CLI fallback.

Completion requires fresh compileall, full pytest, `git diff --check`, a real
local Gradio launch/smoke, real MP3 flow, negative UNKNOWN control, and a
limited preliminary listening screen. Without a formal listening study, the
documentation must say `FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`.

## Deployment boundary

This branch prepares an integration-ready local candidate and documents Render
Free feasibility from observed local resource/timeout behavior. It does not
modify production Render, push, merge `main`, or claim hosted readiness before
the local acceptance gates pass.
