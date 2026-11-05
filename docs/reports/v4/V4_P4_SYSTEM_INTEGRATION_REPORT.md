# V4-P4 System Integration Report

**System:** Robust Audio Watermarking Studio\
**Scope:** Local Gradio Blocks integration of the frozen SilentCipher and V3 engines\
**Result:** `V4_P4_STATUS = PARTIAL`

## 1. Summary

The local studio now has four tabs: Watermark, Channel Lab, Blind Detection, and Signal Analysis. Both frozen backends run through one Gradio service on CPU. SilentCipher remains the default neural candidate; V3 remains a distinct DSP backend and is loaded through its existing public API. No model was trained, no third watermark engine was added, and the V3 checkout and online service were not changed.

All core operation endpoints were exercised against a running localhost Gradio service: neural and classic embedding, independent detection, real MP3 round trips, positive and negative cases, channel transforms, invalid input, and aligned plots. A Chromium screenshot was visually reviewed, and a browser-side upload followed by the Embed button returned a real result. The blind-detection endpoint passed independent upload tests through Gradio's client. The headless browser's synthetic file-selection event did not propagate a selected file to that tab's callback, so direct browser interaction for blind detection and playback was not fully verified. This is the reason for `PARTIAL`; it is not evidence of a SilentCipher or V3 detector failure.

## 2. Architecture and components

| Layer | Implementation |
|---|---|
| GUI | `app/v4_studio_gui.py`: Gradio Blocks tabs and bounded callback surface |
| Audio processing | `app/v4_audio_processing.py`: preflight, decode, mono conversion, resampling, fixed backend lengths, FFmpeg codec round trips, deterministic noise/crop, signal alignment, SNR/LSD, Plotly figures |
| SilentCipher backend | `app/v4_backends.py` delegates to the existing `SilentCipherAdapter`; official 44.1 kHz weights remain external |
| Frozen V3 backend | `app/v4_backends.py` imports the existing V3 `v3_api.py` under a private package namespace and calls only `embed_message()` / `detect_message()` |
| Presence policy | SilentCipher retains the P1 provisional policy (`0.680556`); V3 retains its frozen threshold (`0.7855073980199624`) |
| Temporary files | Existing `ArtifactStore` is used inside a unique mode-0700 run directory; Gradio's own cache is placed under that directory and removed on exit, with one-hour expiry cleanup during subsequent jobs |

The detector callback accepts only the received upload and backend selection. It has no expected-message, reference-audio, embed-session, or ground-truth parameter. SilentCipher's official `status=True` is not itself treated as presence. A candidate is diagnostic; only a valid candidate plus the selected presence policy produces `IDENTIFIED`. Ordinary model decode failure without a candidate returns `UNKNOWN`; handled input/model exceptions return `DECODE_ERROR`. There is no cross-backend fallback.

The application limits uploads to 16 MiB and preflight duration to 60 seconds. FFmpeg calls use argument arrays (no shell) and bounded timeouts. Gradio runs on `127.0.0.1`, does not enable public sharing, disables analytics, and uses a finite queue with one inference worker. The launcher caps numerical CPU thread pools at four; the observed process had 16 total OS threads including service/runtime threads.

## 3. Backend contracts and UI functions

### Advanced Neural

- Official SilentCipher 44.1 kHz / 73999-iteration checkpoint, loaded once per process.
- 40-bit payload: exactly five bytes, displayed as ten hex digits.
- Input is converted to mono 44.1 kHz and prepared to exactly 12 seconds.
- The UI returns prepared original audio, watermarked WAV, download file, embedding SNR, CPU time, model-initialization timing, and input format information.
- Presence threshold remains provisional and is shown with each detection result.

### Classic DSP

- Frozen V3 public API and parameters; 8-bit integer payload.
- Input is converted to mono 48 kHz and prepared to exactly 6 seconds.
- The UI labels its FFT/QIM + REAL_TOP32 + Soft-Code configuration and capacity explicitly.
- V3 code, configuration, history, and Render service were not edited.

### Channel Lab

- MP3 128 kbps (`libmp3lame`) and AAC 128 kbps are actual FFmpeg encode/decode round trips. The encoded file is downloadable and the decoded WAV is playable.
- Additive white noise uses a user-visible seed and target SNR; fixed crop uses explicit start and duration.
- The UI reports the applied operation, output type, duration, byte count, and codec time. It states that providing a transform does not claim watermark robustness against that transform.
- Phase-shift/crop search is not enabled.

### Signal Analysis

- Compares reference and processed samples after resampling to a common 48 kHz rate.
- Estimates a bounded time offset and calculates metrics over the true aligned overlap; it does not backend-pad or truncate unequal signals before calculating quality metrics.
- Produces waveform, STFT magnitude (dB), and aligned spectral-difference plots.
- SNR uses aligned time-domain signal/error power. LSD is the RMS dB difference between aligned STFT magnitudes (4096-sample Hann window, 2048-sample hop).
- If alignment confidence is below policy, SNR/LSD are withheld and reported unavailable.

## 4. Runtime verification

Tests used existing authorized P1/P3 audio sources and the frozen model. This was a bounded system smoke check, not a new dataset benchmark or a new generalization claim.

| Runtime case | Observed result |
|---|---|
| SilentCipher clean, music sample | `IDENTIFIED`, exact `123456789A`, confidence `1.000000` |
| SilentCipher clean, speech sample | `IDENTIFIED`, exact `123456789A`, confidence `0.996032` |
| SilentCipher clean, environment sample | `IDENTIFIED`, exact `123456789A`, confidence `0.976190` |
| SilentCipher MP3 128 kbps, music positive | `IDENTIFIED`, exact `123456789A`, confidence `0.992063`; actual FFmpeg encode/decode |
| SilentCipher known P1 `music_03` MP3 failure, exact source decode/crop/message protocol | `UNKNOWN`, no candidate, no confidence; the historical failure remained a failure |
| SilentCipher unwatermarked clean speech | `UNKNOWN`; legal candidate `FAF856194C` was diagnostic only, confidence `0.373016` |
| SilentCipher unwatermarked MP3 speech | `UNKNOWN`, no candidate and no confidence |
| V3 clean speech | `IDENTIFIED`, byte `0x12`, score `1.000000` |
| V3 MP3 128 kbps speech | `IDENTIFIED`, byte `0x12`, score `1.000000`; actual FFmpeg round trip |
| V3 unwatermarked clean speech | `UNKNOWN`, score `0.677798` |
| V3 unwatermarked MP3 speech | `UNKNOWN`, score `0.639740` |
| Invalid neural message | Rejected with a bounded validation message; no model invocation |
| Invalid non-audio upload | `DECODE_ERROR` with a safe user message; no path or traceback exposed |
| Analysis on matching 12-second music pair | Three Plotly figures returned; aligned SNR `48.48 dB`, LSD `3.439 dB`, lag `0.0000 s`, 12.00 seconds compared |
| Browser visual review | Chromium screenshot showed the Watermark tab, backend capacity, upload control, message field, embed button, audio outputs, and WAV download component |
| Browser-side interaction | A browser-created file upload plus Embed button returned an `Embedded` status and populated the output/download components. A synthetic file event on the Blind Detection tab displayed a filename but the callback received no file; normal interactive file-picker detection was therefore not claimed as browser-verified. |

The message shown in a positive UI test is known by the test harness, but it was not passed to either detector. The negative candidate above is deliberately not treated as an accepted watermark. No formal false-acceptance rate is inferred from these few clips.

The selected V3 speech sample succeeds on MP3. A separate initial smoke using the P1 music excerpt returned `UNKNOWN` after V3 MP3, with score `0.558111`; this is retained as a real channel/source limitation. The V3 and SilentCipher modes also differ in payload size, sample rate, and processing length, so these observations are not a head-to-head performance ranking.

## 5. DSP and resource results

### Signal quality

- SilentCipher embedding SNR in the three representative clean samples: `48.49–48.95 dB`.
- V3 embedding SNR for the final speech smoke: `60.38 dB`.
- The reported analysis pair was the same music source before/after SilentCipher embedding, aligned at zero lag over 12 seconds. It returned `48.48 dB` SNR and `3.439 dB` LSD.
- These are source-specific engineering observations. The V3 and SilentCipher capacities and block lengths differ; SNR values alone do not establish overall quality superiority.

### CPU and memory

Observed in the final local process on CPU:

- SilentCipher embedding callback: approximately `3.22–4.72 s` per 12-second block in this smoke; the first reported model-initialization interval was `0.08 s` (warm filesystem/runtime conditions).
- SilentCipher detection callback: approximately `5.72–6.29 s` per 12-second block.
- V3 embedding callback: approximately `0.05 s`; V3 detection callback: approximately `0.01–0.04 s` per 6-second block.
- FFmpeg 128 kbps codec round trips: approximately `0.13–0.21 s` per 6–12-second sample.
- SilentCipher process peak RSS (`VmHWM`): `1,581,248 kB` (about 1.51 GiB); current RSS after requests: `539,612 kB` (about 527 MiB).
- Total observed process threads: 16, with numerical libraries and Torch configured for at most four computation threads and Gradio configured for one queued worker.

The peak memory figure includes model initialization and runtime imports; use a machine with headroom above the observed peak. CPU-only local demonstration is feasible, but SilentCipher detection is noticeably slower than V3.

## 6. Startup

The single startup script is `scripts/run_v4_studio.sh`. In the isolated Python environment already containing the P2-compatible dependencies, set these deployment-local variables once:

```bash
export V4_STUDIO_PYTHON=/path/to/isolated/python
export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher/source
export SILENTCIPHER_MODEL_DIR=/path/to/official/Models/44_1_khz/73999_iteration
export V3_SOURCE_ROOT=/path/to/frozen/v3/checkout
```

Then start the local service:

```bash
./scripts/run_v4_studio.sh
```

Optional settings: `V4_STUDIO_PORT` (default `7862`), `V4_STUDIO_TMP_ROOT` (parent for a unique private run directory), and `V4_CPU_THREADS` (default `4`). The script deliberately does not embed machine-specific paths. SilentCipher checkpoint files are not bundled or copied into this repository; confirm applicable weight redistribution terms before any packaging. The service is localhost-only and is not configured for public deployment.

## 7. Files added for P4

- `app/v4_audio_processing.py`
- `app/v4_backends.py`
- `app/v4_studio_gui.py`
- `scripts/run_v4_studio.sh`
- `tests/test_v4_p4_audio_processing.py`
- `tests/test_v4_p4_backends.py`
- `docs/superpowers/specs/2026-11-05-v4-p4-system-design.md`
- `docs/superpowers/plans/2026-11-05-v4-p4-system-integration.md`

The pre-existing P0–P3 reports and result files were not edited in this work. The V3 checkout remained clean on its existing branch at the previously observed revision. No commit, push, Render change, checkpoint copy, or dataset addition was made.

## 8. Limitations and remaining validation

1. The current SilentCipher presence policy is still provisional; the P4 negatives are too small for an operational false-acceptance claim.
2. SilentCipher retains source-dependent MP3 failures, including the frozen P1 music failure. The UI correctly displays `UNKNOWN` for that exact case.
3. V3 and SilentCipher differ in capacity and block contract. The UI exposes them as separate modes; this smoke does not claim a fair head-to-head ranking.
4. AAC, deterministic noise, and fixed crop processing were exercised, but no robustness claim is made for these channels. Crop recovery and phase-shift search remain unimplemented.
5. Browser screenshot review and actual browser embedding were completed. Browser-driven blind-detection submission and audible playback were not fully verified with the available headless interaction method; the independent `/detect` Gradio upload endpoint did pass runtime checks.
6. Model weight redistribution permission remains external to this P4 implementation. No public packaging or deployment is authorized by this report.

## 9. Final status

`V4_P4_STATUS = PARTIAL`

The integrated localhost system and backend operations are runtime-validated, and the service is suitable for local course demonstration with explicit backend limitations. The remaining status gap is browser-level verification of the blind-detection file-picker flow and actual audible playback, not the independent detector endpoint itself. Do not present P4 as a generalized robustness benchmark or as a public deployment.
