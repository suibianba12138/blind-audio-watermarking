# V3 8-bit Candidate Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the independently validated V3 8-bit Soft-Code operating point behind a blind public API and a localhost Gradio/CLI demonstration without changing Course V2 or any frozen research algorithm.

**Architecture:** Add a thin V3 adapter over the existing B1/Soft-Code modules, with one subprocess detector boundary and a per-session temporary-file manager. Add a new integration GUI and CLI that delegate Legacy Course V2 calls to the existing pipeline and V3 calls to the new adapter; leave `gradio_app.py`, `app/gui.py`, and frozen research modules unchanged.

**Tech Stack:** Python 3.13, NumPy, SciPy, FFmpeg/libmp3lame 128 kbps, Gradio 4.x, pytest, existing `AudioData`/pipeline abstractions.

## Global Constraints

- V3 uses exactly the P2-V validated 8-bit Soft-Code configuration: strength `1.60`, threshold `0.7855073980199624`, REAL_TOP32, watermark seed 7, 48 kHz mono, six-second block.
- V3 accepts integer messages in `[0, 255]`; its detector has no expected-message, clean-audio, filename-label, or ground-truth input.
- V3 exposes only the validated six-second protocol; Course V2 retains its existing 6/15/30-second identity modes.
- Do not modify `src/audio_watermark/b1.py`, `b1_soft.py`, `b2_capacity.py`, `embed.py`, `detect.py`, `course_v2.py`, the REAL_TOP32 map, Course V2 GUI, historical metrics, P1/P2/P2-V artifacts, production Render, or public pages.
- Reuse the existing 64 MiB input limit, 30-second decoded-duration limit, and 120-second FFmpeg timeout.
- All GUI launches default to `127.0.0.1` with `share=False`; no public deployment or push is allowed in this plan.
- Formal perceptual quality remains `NOT_ESTABLISHED`; generated A/B files may support preliminary user listening only.

---

### Task 1: Freeze the V3 Candidate and Define the API Contract

**Files:**
- Create: `scripts/v3_p3_freeze_config.py`
- Create: `configs/v3_8bit_candidate_freeze.json`
- Create: `tests/test_v3_p3_freeze.py`
- Create: `tests/test_v3_api_contract.py`
- Reference: `experiments/v3_p2_v/CONFIG_FREEZE.json`, `V3_P2_V_INDEPENDENT_VALIDATION.md`

**Interfaces:**
- Freeze record stage: `V3_P3_V3_8BIT_CANDIDATE`.
- Public signatures: `embed_message(audio: AudioData, message: int) -> V3EmbedResult` and `detect_message(audio: AudioData) -> V3DetectionResult`.

- [ ] **Step 1: Write failing freeze/API tests.**

```python
def test_v3_freeze_records_the_p2v_operating_point():
    data = json.loads(Path("configs/v3_8bit_candidate_freeze.json").read_text())
    assert data["stage"] == "V3_P3_V3_8BIT_CANDIDATE"
    assert data["strength"] == 1.60
    assert data["presence_threshold"] == 0.7855073980199624
    assert data["protocol"]["duration_seconds"] == 6

def test_public_api_exports_the_blind_contract():
    from app.v3_api import detect_message, embed_message
    assert tuple(inspect.signature(embed_message).parameters) == ("audio", "message")
    assert tuple(inspect.signature(detect_message).parameters) == ("audio",)
```

- [ ] **Step 2: Run the focused tests and confirm the missing-artifact failure.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_v3_p3_freeze.py tests/test_v3_api_contract.py`

Expected: failure because the V3-P3 freeze record and API module do not exist.

- [ ] **Step 3: Implement the freeze generator.**

Hash `b1.py`, `b1_soft.py`, `b2_capacity.py`, `embed.py`, `detect.py`,
`v3_p2.py`, `app/public_config.py`, the REAL_TOP32 map, P1/P2/P2-V freeze
records, and the P2-V reports. Fail if the base is not
`2c6f53cddf7ba67ffcabe9f3f3744f6279a71cdc`.

```python
FREEZE = {
    "stage": "V3_P3_V3_8BIT_CANDIDATE",
    "base": "research/v3-p2-validation@2c6f53cddf7ba67ffcabe9f3f3744f6279a71cdc",
    "strength": 1.60,
    "presence_threshold": 0.7855073980199624,
    "protocol": {"sample_rate_hz": 48000, "duration_seconds": 6,
                 "physical_payload_bits": 32, "effective_payload_bits": 8,
                 "selector": "REAL_TOP32", "watermark_seed": 7},
    "mp3": {"codec": "libmp3lame", "bitrate": "128k"},
    "parameter_selection_on_p2v": False,
}
```

- [ ] **Step 4: Generate, inspect, and test the freeze record.**

Run: `PYTHONPATH=src:scripts:. python scripts/v3_p3_freeze_config.py --output configs/v3_8bit_candidate_freeze.json`

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_v3_p3_freeze.py`

- [ ] **Step 5: Commit the freeze contract.**

```bash
git add scripts/v3_p3_freeze_config.py configs/v3_8bit_candidate_freeze.json tests/test_v3_p3_freeze.py tests/test_v3_api_contract.py
git commit -m "feat: freeze V3 8-bit candidate contract"
```

### Task 2: Implement the Blind V3 API on the Frozen Channel

**Files:**
- Create: `app/v3_api.py`
- Modify: `tests/test_v3_api_contract.py`
- Create: `tests/test_v3_api_behavior.py`
- Do not modify: `src/audio_watermark/b1.py`, `b1_soft.py`, `b2_capacity.py`, `embed.py`, `detect.py`, `app/public_config.py`

**Interfaces:**
- `embed_message(audio: AudioData, message: int) -> V3EmbedResult`
- `detect_message(audio: AudioData) -> V3DetectionResult`
- Valid status values: `IDENTIFIED` and `UNKNOWN`; accepted result has an integer message, rejected result has `None`.

- [ ] **Step 1: Write failing behavior tests.**

```python
def test_embed_and_detect_round_trip_integer_message():
    clean = AudioData(make_probe(6), 48_000)
    marked = embed_message(clean, 173)
    result = detect_message(marked.audio)
    assert result.status == "IDENTIFIED"
    assert result.message == 173
    assert result.threshold == 0.7855073980199624

def test_api_rejects_non_integer_and_out_of_range_messages():
    clean = AudioData(make_probe(6), 48_000)
    for message in (-1, 256, 1.5, "7"):
        with pytest.raises(ValueError):
            embed_message(clean, message)

def test_clean_audio_is_unknown_and_detector_has_no_expected_message_argument():
    clean = AudioData(make_probe(6), 48_000)
    assert detect_message(clean).status == "UNKNOWN"
    assert "expected" not in inspect.signature(detect_message).parameters
```

- [ ] **Step 2: Run the behavior tests and confirm the missing-module failure.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_v3_api_contract.py tests/test_v3_api_behavior.py`

- [ ] **Step 3: Implement the minimal frozen adapter.**

Use `dataclasses.replace(build_embedding_config(), strength=1.60)`,
`load_public_selector()`, `encode_capacity_payload(message_bits, 8)`,
`embed_watermark_b1`, `detect_watermark_b1_soft`, and
`decode_soft_capacity(detection.physical_statistics, 8)`. Preparation resamples
to 48 kHz, rejects inputs over 30 seconds, takes the first six seconds, and
zero-pads shorter inputs. Acceptance is exactly:

```python
accepted = decoded.presence_score >= 0.7855073980199624
status = "IDENTIFIED" if accepted else "UNKNOWN"
message = int("".join(str(bit) for bit in decoded.message_bits), 2) if accepted else None
```

- [ ] **Step 4: Run API and frozen-code regressions.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_v3_api_contract.py tests/test_v3_api_behavior.py tests/test_b1_soft_code.py tests/test_b2_capacity.py`

- [ ] **Step 5: Commit the API.**

```bash
git add app/v3_api.py tests/test_v3_api_contract.py tests/test_v3_api_behavior.py
git commit -m "feat: expose blind V3 8-bit API"
```

### Task 3: Add Session Isolation and Safe Temporary-File Lifecycle

**Files:**
- Create: `app/session_store.py`
- Create: `tests/test_session_store.py`
- Reference: `app/audio_io.py` limits `MAX_INPUT_BYTES`, `MAX_DEMO_SECONDS`, and `FFMPEG_TIMEOUT_SECONDS`

**Interfaces:**
- `SessionStore(root: Path | None = None, ttl_seconds: int = 3600)`
- `create() -> SessionHandle`
- `SessionHandle.path(name: str) -> Path`
- `SessionHandle.cleanup() -> None`
- `SessionStore.cleanup_expired(now: float | None = None) -> int`

- [ ] **Step 1: Write failing isolation tests.**

```python
def test_sessions_have_distinct_roots_and_cannot_escape(tmp_path):
    store = SessionStore(tmp_path)
    first, second = store.create(), store.create()
    assert first.root != second.root
    assert first.path("marked.wav").parent == first.root
    with pytest.raises(ValueError):
        first.path("../outside.wav")

def test_expired_session_cleanup_is_scoped_to_session_root(tmp_path):
    store = SessionStore(tmp_path, ttl_seconds=1)
    handle = store.create()
    handle.path("marker.txt").write_text("x")
    assert store.cleanup_expired(now=handle.created_at + 2) == 1
    assert not handle.root.exists()
    assert tmp_path.exists()
```

- [ ] **Step 2: Run tests and confirm the missing-module failure.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_session_store.py`

- [ ] **Step 3: Implement scoped session creation and cleanup.**

Use `tempfile.mkdtemp(prefix="blind_audio_v3_", dir=root)` and reject names
whose resolved path is not inside the session root. Never recursively remove
the workspace, repository root, or arbitrary user paths.

- [ ] **Step 4: Add input-limit tests.**

Cover a file over 64 MiB, decoded audio over 30 seconds, empty/non-finite
samples, and unsupported FFmpeg input. Assert a readable exception and no
detector result.

- [ ] **Step 5: Run session/public-contract tests and commit.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_session_store.py tests/test_public_contracts.py tests/test_public_payload.py`

```bash
git add app/session_store.py tests/test_session_store.py
git commit -m "feat: isolate V3 demo sessions"
```

### Task 4: Build the V3 Pipeline, Blind Worker, CLI, and MP3 Flow

**Files:**
- Create: `app/v3_detector_worker.py`
- Create: `app/v3_pipeline.py`
- Create: `scripts/v3_demo.py`
- Create: `tests/test_v3_pipeline.py`
- Create: `tests/test_v3_detector_worker.py`
- Reuse without modification: `app/mp3_codec.py`, `app/audio_io.py`, `app/v3_api.py`

**Interfaces:**
- `run_v3_demo(input_path, message, codec="identity", output_dir=None) -> V3DemoRun`
- `detect_uploaded_file(input_path) -> V3DetectionResult`
- Worker: `python -m app.v3_detector_worker --input PATH --json`
- CLI: `python scripts/v3_demo.py --input INPUT --message 173 --codec mp3 --output-dir OUT`

- [ ] **Step 1: Write failing pipeline/worker tests.**

```python
def test_v3_pipeline_writes_mp3_outputs_and_detects_blindly(tmp_path):
    run = run_v3_demo(make_wav(tmp_path / "input.wav", seconds=6), 173,
                      codec="mp3", output_dir=tmp_path / "run")
    assert run.original_wav.is_file() and run.marked_wav.is_file()
    assert run.compressed_mp3.is_file()
    assert run.detection.status == "IDENTIFIED"
    assert run.detection.message == 173

def test_worker_has_no_expected_message_option():
    result = subprocess.run([sys.executable, "-m", "app.v3_detector_worker", "--help"], capture_output=True, text=True)
    assert "expected" not in result.stdout.lower()
```

- [ ] **Step 2: Run focused tests and confirm missing pipeline/worker failure.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_v3_pipeline.py tests/test_v3_detector_worker.py`

- [ ] **Step 3: Implement the worker boundary.**

The worker accepts only `--input` and optional public map path, decodes via
`decode_audio_file`, calls `detect_message`, prints one JSON object, and maps
exceptions to `{"status": "ERROR", "error": ...}` with exit code 2. It must
not accept a message argument or import GUI/session state.

- [ ] **Step 4: Implement the pipeline and independent-file detector.**

Decode input, call `embed_message`, write original/marked WAV, call
`encode_decode_mp3` only for `codec="mp3"`, and invoke the worker on the
received path. `detect_uploaded_file` creates a separate session and never
reads embedding state. Cleanup runs on exceptions and through explicit/TTL
cleanup, while successful output paths remain available for listening.

- [ ] **Step 5: Implement and test the CLI fallback.**

Support `--input`, `--message`, `--codec identity|mp3`, `--output-dir`, and
`--detect-input`; reject missing message for embed mode and print structured
JSON. Run real FFmpeg and clean UNKNOWN checks:

```bash
PYTHONPATH=src:scripts:. python scripts/v3_demo.py --input /tmp/v3_demo_input.wav --message 173 --codec mp3 --output-dir /tmp/v3_demo_run
```

- [ ] **Step 6: Commit the pipeline.**

```bash
git add app/v3_detector_worker.py app/v3_pipeline.py scripts/v3_demo.py tests/test_v3_pipeline.py tests/test_v3_detector_worker.py
git commit -m "feat: add V3 blind demo pipeline and CLI"
```

### Task 5: Add the Local Gradio Integration Entry Point

**Files:**
- Create: `app/integration_gui.py`
- Create: `gradio_v3_app.py`
- Create: `tests/test_integration_gui.py`
- Do not modify: `app/gui.py`, `gradio_app.py`

**Interfaces:**
- `build_integration_demo() -> gr.Blocks`
- Mode values: `V3 8-bit Soft-Code` and `Legacy Course V2`.
- V3 detection callback receives only an uploaded received file.

- [ ] **Step 1: Write failing GUI construction tests.**

```python
def test_integration_gui_builds_without_launching():
    demo = build_integration_demo()
    assert demo is not None

def test_v3_detection_callback_does_not_accept_expected_message():
    assert "expected" not in inspect.signature(detect_uploaded_file).parameters
```

- [ ] **Step 2: Run the focused test and confirm the missing-entry-point failure.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_integration_gui.py`

- [ ] **Step 3: Implement the integration layout.**

Use the existing visual style and sections: mode/input, embed/listen, real
MP3, independent received upload, and detection result. V3 exposes only the
integer message and six-second protocol; Legacy delegates to existing Course
V2 callbacks and keeps 6/15/30 controls. Show `DETECTED: <integer>` or
`UNKNOWN / NO VALID WATERMARK`, score, threshold, duration, sample rate, and
timing. Any “correct” comparison happens after blind detection in display code.

- [ ] **Step 4: Add a localhost-only launcher.**

`gradio_v3_app.py` must call
`build_integration_demo().launch(server_name="127.0.0.1", share=False, inbrowser=False)`
and honor `GRADIO_SERVER_PORT`.

- [ ] **Step 5: Run GUI smoke tests and commit.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_integration_gui.py`

```bash
git add app/integration_gui.py gradio_v3_app.py tests/test_integration_gui.py
git commit -m "feat: add V3 and Course V2 integration GUI"
```

### Task 6: Add Acceptance, Resource, Listening, and Documentation Artifacts

**Files:**
- Create: `scripts/v3_p3_acceptance.py`
- Create: `scripts/v3_p3_listening_pack.py`
- Create: `docs/V3_P3_INTEGRATION.md`
- Create: `docs/V3_P3_ACCEPTANCE_ZH.md`
- Create: `tests/test_v3_p3_acceptance.py`
- Update only if needed: `README.md`, `README_ZH.md`, `docs/LIMITATIONS.md`

**Interfaces:**
- Acceptance command: `python scripts/v3_p3_acceptance.py --output-dir PATH`
- Listening pack command: `python scripts/v3_p3_listening_pack.py --input PATH --output-dir PATH`
- Documentation must state `FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`.

- [ ] **Step 1: Write failing acceptance tests.**

```python
def test_acceptance_report_contains_required_gates(tmp_path):
    report = run_acceptance(output_dir=tmp_path)
    assert report["blind_detection"] == "PASS"
    assert report["negative_unknown"] == "PASS"
    assert report["formal_perceptual_gate"] == "NOT_ESTABLISHED"
```

- [ ] **Step 2: Run the focused test and confirm the missing-script failure.**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q tests/test_v3_p3_acceptance.py`

- [ ] **Step 3: Implement deterministic acceptance checks.**

Generate a small local test WAV, test messages 0, 1, 173, and 255, run clean
UNKNOWN, wrong-key detector, invalid input, size/duration guards, session
cleanup, CLI fallback, and a real MP3 round-trip. Measure elapsed time, peak
RSS, and FFmpeg availability. Write only metadata/results. Report Render
feasibility as `LOCAL_PROXY_ONLY` unless an authorized container test exists.

- [ ] **Step 4: Implement an A/B listening pack.**

Write original, watermarked, MP3, and decoded-MP3 files plus a Chinese
checklist. Mark it as preliminary listening screening material, not a formal
perceptual experiment.

- [ ] **Step 5: Write integration documentation.**

Record the frozen V3 configuration, API usage, local commands, GUI mode
separation, P2-V numbers (8-bit 117/120 accepted trials and 58/60 sources;
12-bit 97/120 and 45/60), negative-control limits, MP3 scope, six-second-only
limitation, and no-deployment boundary. Preserve existing Course V2 results.

- [ ] **Step 6: Run acceptance and listening-pack commands.**

```bash
PYTHONPATH=src:scripts:. python scripts/v3_p3_acceptance.py --output-dir /tmp/v3_p3_acceptance
PYTHONPATH=src:scripts:. python scripts/v3_p3_listening_pack.py --input /tmp/v3_demo_input.wav --output-dir /tmp/v3_p3_listening
```

- [ ] **Step 7: Commit acceptance and documentation artifacts.**

```bash
git add scripts/v3_p3_acceptance.py scripts/v3_p3_listening_pack.py docs/V3_P3_INTEGRATION.md docs/V3_P3_ACCEPTANCE_ZH.md tests/test_v3_p3_acceptance.py README.md README_ZH.md docs/LIMITATIONS.md
git commit -m "docs: record V3 P3 local acceptance and limits"
```

### Task 7: Fresh Full Verification and Handoff

**Files:**
- Verify all files created by Tasks 1-6.
- Do not modify frozen algorithm or historical result paths.

- [ ] **Step 1: Run compile, regression, and whitespace checks.**

```bash
PYTHONPYCACHEPREFIX=/tmp/v3-p3-pyc PYTHONPATH=src:scripts:. python -m compileall -q src app scripts tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:. pytest -q -p no:cacheprovider
git diff --check
```

Expected: compileall exit 0, pytest 0 failures, and diff check exit 0.

- [ ] **Step 2: Run real local Gradio smoke.**

Start: `GRADIO_ANALYTICS_ENABLED=False PYTHONPATH=src:scripts:. python gradio_v3_app.py`

Verify on localhost: page opens, WAV upload, V3 message selection,
original/marked playback, real MP3 encode/decode, separate received upload,
blind detection, clean UNKNOWN, Legacy mode, and restart without stale session.
Record the result in `docs/V3_P3_ACCEPTANCE_ZH.md`.

- [ ] **Step 3: Run frozen-core and data checks.**

```bash
test -z "$(git diff --name-only 2c6f53cddf7ba67ffcabe9f3f3744f6279a71cdc -- src/audio_watermark/b1.py src/audio_watermark/b1_soft.py src/audio_watermark/b2_capacity.py src/audio_watermark/course_v2.py src/audio_watermark/embed.py src/audio_watermark/detect.py configs/real_top32_stability_map.json experiments/v3_p1 experiments/v3_p2 experiments/v3_p2_v)"
git ls-files | rg '\.(wav|mp3|flac|ogg|m4a|pt|pth|ckpt)$' && exit 1 || true
git status --short --branch
```

- [ ] **Step 4: Decide readiness from evidence.**

Set `V3_P3_STATUS` to `PASS`, `PARTIAL`, or `BLOCKED`; set
`PUBLIC_INTEGRATION_READINESS = CONDITIONAL` unless every local gate passes.
If browser or resource evidence is unavailable, report the exact blocker and
retain the CLI fallback. Never change frozen parameters to force a green status.

- [ ] **Step 5: Final handoff.**

Run:

```bash
git status --short
git diff --check
git log -1 --oneline
```

Report HEAD, test count, API/MP3/GUI/negative-control status, listening status,
Render feasibility, and explicit no-push/no-merge state. Create the final local
commit only after fresh verification.
