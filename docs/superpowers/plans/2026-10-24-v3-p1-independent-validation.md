# V3-P1 Independent Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use inline execution with TDD and verification gates. Do not push, merge, retune frozen parameters, or modify Course V2/SPL/public deployment artifacts.

**Goal:** Validate the frozen B1 repeat-4, hard-code, and soft-code 8-bit methods on a new source-disjoint 60-source test protocol.

**Architecture:** Keep `b1.py`, `embed.py`, `detect.py`, `course_v2.py`, and the committed B1 soft pilot artifacts unchanged. Add a new frozen metadata-only manifest, a small hard-code wrapper, a single paired evaluation script, confidence intervals/McNemar analysis, and P1 reports under separate result names.

**Tech Stack:** Existing NumPy/SciPy runtime, local MUSAN metadata/audio outside Git, FFmpeg `libmp3lame` 128 kbps, pytest, CSV/JSON, and standard-library statistical calculations.

## Global Constraints

- Start from `research/v3-p0@34411a9` and work only on local `research/v3-p1`.
- Freeze current pilot code, thresholds, strength `1.60`, selector seed `7`, message seeds `101/202`, 6-second protocol, and 32 physical positions before evaluation.
- The new manifest must exclude audited Course V2 manifests, R1, and B1 Soft-Code Pilot paths and hashes.
- Use the same source, messages, audio length, selector, encoder, and MP3 parameters for all methods.
- The detector may receive only received audio plus public/keyed configuration; expected payload is post-hoc scoring only.
- Do not adjust thresholds, strength, codebook, or message generation after viewing P1 results.
- Do not copy raw audio into the repository, push, merge, deploy, or modify frozen research/public artifacts.

## Tasks

### Task 1: Freeze P1 baseline and source manifest

**Files:**
- Create: `configs/v3_p1_independent_manifest.json`
- Modify: `task_plan.md`, `findings.md`, `progress.md`

Use `scripts/v3_p0_r1_freeze_manifest.py` with all audited Course V2 manifests plus
`configs/v3_p0_r1_real_audio_manifest.json` and `configs/v3_b1_soft_pilot_manifest.json` as
exclusions. Require exactly 60 records, 20 per category, 10 dev/10 test, unique source groups,
unique SHA256, duration at least 6 seconds, and zero overlap with all excluded manifests.
The manifest must be written before any P1 evaluation output is generated.

### Task 2: Add hard-code wrapper contract tests first

**Files:**
- Create: `src/audio_watermark/b1_hard_code.py`
- Create: `tests/test_b1_hard_code.py`

Write tests before implementation for a hard-code wrapper that uses the existing fixed
`encode_soft_payload()` codeword but discards continuous soft values and decodes the 32 hard
physical bits by minimum Hamming distance. The contract is:

```python
def encode_hard_payload(payload: Sequence[int]) -> tuple[int, ...]: ...
def decode_hard_physical_bits(bits: Sequence[int]) -> tuple[int, ...]: ...
```

Tests must cover exact clean round trips for all eight-bit positions, invalid lengths/values,
and a deterministic tie/error behavior. Run the focused test and observe the expected missing
module failure before adding the minimal implementation.

### Task 3: Freeze configuration and detector contract

**Files:**
- Create: `experiments/v3_p1/CONFIG_FREEZE.json`
- Create: `scripts/v3_p1_freeze_config.py`
- Test: `tests/test_v3_p1_contracts.py`

Record SHA256 for `src/audio_watermark/b1_soft.py`, `src/audio_watermark/b1.py`,
`src/audio_watermark/embed.py`, `src/audio_watermark/detect.py`, the codebook bytes, and the
P1 manifest. Record strength `1.60`, selector/map identity and hash, rejection threshold
`0.7855073980199624` from Pilot calibration, message seeds `101/202`, sample rate `48000`,
duration `6.0`, and FFmpeg command/version. Tests must assert the detector signature does not
contain expected payload, clean audio, or identity parameters.

### Task 4: Run one paired P1 evaluation

**Files:**
- Create: `scripts/v3_p1_independent_validation.py`
- Create: `experiments/v3_p1/V3_P1_PAIRED_RESULTS.csv`
- Create: `experiments/v3_p1/V3_P1_SUMMARY.json`

For each frozen source and both fixed messages, embed and detect three methods at strength
`1.60`: repeat-4, hard-code, and soft-code. Run marked no-attack and real FFmpeg 128 kbps MP3.
Write one row per source/message/method/condition with source id/category/split, physical BER,
logical BER, exact recovery, presence score/acceptance, SNR, spectral distortion, clipping,
embed/detect runtime, and peak memory if measurable. Include blind-detector assertion fields and
do not use the expected payload in detector calls.

### Task 5: Evaluate negative controls and paired statistics

**Files:**
- Create: `experiments/v3_p1/V3_P1_DETECTION_RESULTS.csv`
- Create: `scripts/v3_p1_analyze.py`

Use the same frozen test sources as negative no-watermark controls, their FFmpeg MP3 versions,
and wrong-key MP3 detections. Keep threshold fixed from the Pilot; do not recalibrate on P1.
Report FPR, wrong-key acceptance, wrong-message acceptance, rejection rate, Wilson 95% intervals,
source-level and trial-level results, category breakdowns, paired success/failed tables, and
McNemar exact two-sided p-values for Soft-Code versus Repeat-4 and Hard-Code versus Repeat-4.

### Task 6: Limited audio review and reports

**Files:**
- Create: `V3_P1_INDEPENDENT_VALIDATION.md`
- Create: `V3_P1_DETECTION_REPORT.md`
- Create: `V3_P1_DECISION.md`
- Create: `experiments/v3_p1/PERCEPTUAL_REVIEW_PROTOCOL.md`
- Create: `tests/test_v3_p1_artifacts.py`

Document a finite A/B listening protocol using representative source/category files without
calling it a formal perceptual experiment. Report clipping flags, SNR, LSD, runtimes, memory
availability, and any audible observations. Generate a final decision that distinguishes Pilot
from P1 evidence and sets `V3_P2_READINESS` only from the frozen P1 results.

### Task 7: Final verification and local commit

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/v3-p1-pyc PYTHONPATH=src:. python -m compileall src scripts tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. pytest -q -p no:cacheprovider
git diff --check
git diff 34411a9660c1b8b0bfaf3f6e72b62e18984d8145 -- src/audio_watermark/embed.py src/audio_watermark/detect.py src/audio_watermark/b1.py src/audio_watermark/course_v2.py
git status --short --branch
```

Only after fresh verification may the branch receive one local commit. No push or merge is allowed.

## Stop Conditions

- If the manifest cannot establish 60 source-traceable records, stop with `INDEPENDENT_SOURCE_COUNT < 60`.
- If any algorithm implementation changes after configuration freeze, invalidate the affected P1 rows and report the re-freeze explicitly.
- If Soft-Code does not improve source-level recovery at matched SNR without worse negative acceptance, set `V3_P2_READINESS = NO_GO` and stop without tuning.
- A finite zero-count negative result is not a claim of FPR below 1%; report denominators and confidence intervals.
