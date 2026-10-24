# V3-P2 Capacity Expansion Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task with tests and fresh verification. Keep all frozen Course V2, B1, R1, Pilot, and P1 artifacts read-only.

**Goal:** Evaluate whether deterministic 12-bit or 16-bit short codes can expand the frozen B1-QIM message capacity in a bounded development-only pilot without changing the physical embedder.

**Architecture:** Freeze the P1 8-bit Soft-Code operating point in a hash-addressed JSON record. Reuse the existing B1 detector to collect signed 32-position statistics, add a small pure-codec module for degree-2 Boolean evaluation codebooks, and run a paired calibration/pilot evaluator on only P1 development sources. Produce raw CSV diagnostics and decision reports that explicitly separate development feasibility from future independent validation.

**Tech Stack:** Python 3.11-compatible source, NumPy/SciPy, existing B1/FFmpeg helpers, pytest, JSON/CSV reports, and no new runtime dependency.

## Global Constraints

- Do not modify frozen Course V2/B1 implementation, P0/R1/Pilot/P1 results, submitted paper data, public pages, or Render configuration.
- Do not use P1 formal test sources to choose a codebook or threshold; use only the pre-existing P1 development split.
- Keep the 8-bit P1 strength, thresholds, seeds, selector, and QIM physical embedding fixed.
- Use real FFmpeg 128 kbps MP3 for channel rows; do not report synthetic or paper metrics as local results.
- Keep candidate count finite: frozen 8-bit reference plus deterministic 12-bit and 16-bit degree-2 evaluation codes.
- Blind decoding receives only received audio and public/keyed configuration; expected payload, clean audio, filename labels, and ground truth are scoring-only inputs.
- No push, merge, public deployment, model training, or large-scale experiment.

### Task 1: Freeze P2 baseline and write channel-analysis contract

**Files:**
- Create: `scripts/v3_p2_freeze_baseline.py`
- Create: `experiments/v3_p2/CONFIG_FREEZE.json`
- Modify: `task_plan.md`, `findings.md`, `progress.md`
- Test: `tests/test_v3_p2_artifacts.py`

**Interfaces:**
- `scripts/v3_p2_freeze_baseline.py` writes a JSON record containing branch/HEAD, P1 operating point, configuration values, manifest hashes, codebook hash, source hashes, FFmpeg version, and a blind-detector contract.
- `tests/test_v3_p2_artifacts.py` verifies required freeze fields and frozen core paths are byte-identical to `82f8013`.

- [x] **Step 1: Add artifact contract tests first.** Assert the freeze JSON has strength `1.60`, thresholds `0.7855073980199624` and `0.47678591988959035`, message seeds `[101,202]`, payload bits `8`, physical bits `32`, and the required source/manifest hash keys.
- [x] **Step 2: Run the focused tests and confirm they fail because the P2 freeze artifact is absent.**
- [x] **Step 3: Implement the freeze script using SHA256 over repository files and JSON manifests, without editing the frozen source files.**
- [x] **Step 4: Generate the freeze JSON to a temporary directory, copy it into `experiments/v3_p2/`, and rerun focused tests.**
- [x] **Step 5: Verify the frozen paths have no diff from `82f8013` and record the result in `findings.md`.**

### Task 2: Add deterministic 12/16-bit code adapters by TDD

**Files:**
- Create: `src/audio_watermark/b2_capacity.py`
- Create: `tests/test_b2_capacity.py`

**Interfaces:**
- `capacity_codebook(payload_bits: int) -> numpy.ndarray`: returns shape `(2**payload_bits, 32)` for payload bits `8`, `12`, or `16`; the 8-bit output must equal the frozen `b1_soft.soft_codebook()`.
- `encode_capacity_payload(payload: Sequence[int], payload_bits: int) -> numpy.ndarray`: deterministic binary 32-bit codeword.
- `decode_soft_capacity(statistics: Sequence[float], payload_bits: int) -> CapacityDecode`: returns `payload_bits`, decoded bits, normalized score, score margin, and signed physical evidence.

- [x] **Step 1: Write tests for 8-bit equivalence, variable 12/16-bit round trips, shape, minimum distance 8 for 12/16, invalid dimensions, and clean-vs-inverted decode behavior.**
- [x] **Step 2: Run `PYTHONPATH=src pytest -q tests/test_b2_capacity.py` and confirm the missing-module failure.**
- [x] **Step 3: Implement the minimal deterministic basis: constant term, five linear terms, and the first required pairwise Boolean terms over all five-bit position labels. Use the 8-bit basis `constant + five linear + (x0*x1) + (x0*x2)` to preserve the current codebook exactly; use all six pairwise terms for 12 bits and all ten for 16 bits.**
- [x] **Step 4: Implement correlation decoding with deterministic lowest-index tie-breaking, score margin, and no hidden clean/reference input.**
- [x] **Step 5: Run the focused tests, then the existing B1/P1 tests.**

### Task 3: Run development-only 32-position channel diagnostics

**Files:**
- Create: `scripts/v3_p2_channel_analysis.py`
- Create: `experiments/v3_p2/V3_P2_CHANNEL_DIAGNOSTICS.csv`
- Create: `experiments/v3_p2/V3_P2_CHANNEL_ANALYSIS.json`
- Create: `V3_P2_CHANNEL_ERROR_ANALYSIS.md`

**Interfaces:**
- Script consumes `configs/v3_p1_independent_manifest.json` records with `split=dev`, fixed messages from seeds `101/202`, existing B1 embed/detect helpers, and real FFmpeg MP3.
- Output contains one row per physical bit per paired source/message/condition with expected sign, statistic, normalized margin, boundary distance, error flag, and source/category/role metadata; analysis JSON contains BER, error-count distribution, per-bit concentration, reliability calibration, error-correlation, run-length, and iid-dispersion diagnostics.

- [x] **Step 1: Add a test for deterministic calibration/pilot role assignment and required diagnostic columns.**
- [x] **Step 2: Run the focused test before implementation and confirm it fails.**
- [x] **Step 3: Implement source preparation using existing `load_source`, fixed six-second 48 kHz processing, existing embed path, and real FFmpeg helper; restrict records to P1 `split=dev` and use first five sources/category for calibration and last five for pilot.**
- [x] **Step 4: Collect clean/MP3 physical statistics and compute the requested 32-position channel metrics without fitting an encoder or selecting from P1 formal test rows.**
- [x] **Step 5: Run the bounded diagnostic and generate the analysis CSV/JSON and report with `CONFIRMED`/`NOT_ESTABLISHED` labels.**

### Task 4: Run finite capacity pilot with calibration-only thresholds

**Files:**
- Create: `scripts/v3_p2_capacity_pilot.py`
- Create: `V3_P2_CAPACITY_PILOT.csv`
- Create: `experiments/v3_p2/V3_P2_CAPACITY_PILOT_SUMMARY.json`
- Create: `V3_P2_CAPACITY_DESIGN.md`
- Create: `V3_P2_DECISION.md`

**Interfaces:**
- Evaluates methods `soft8_frozen`, `degree2_12`, and `degree2_16` on paired messages and conditions `clean`, `mp3`; evaluates clean/MP3 negatives and wrong-key controls.
- Calibrates only candidate thresholds for 12/16 on the deterministic calibration subset; evaluates metrics on the held-out P2 pilot subset, which remains development evidence.
- CSV rows include source identity, category, role, method, capacity, message seed, condition, expected payload only in scoring metadata, decoded payload, presence score, threshold, accepted, exact, wrong-message, SNR/LSD, embed/detect time, and clipping flags.

- [x] **Step 1: Add unit tests for calibration isolation, paired message generation, and metric aggregation by source.**
- [x] **Step 2: Run focused tests and confirm the missing evaluator/API failure.**
- [x] **Step 3: Implement fixed paired evaluation using existing QIM and FFmpeg helpers; use fixed `101/202` seed schedule for all capacities; do not inspect P1 formal test rows.**
- [x] **Step 4: Calibrate 12/16 thresholds from calibration positive/negative presence scores, freeze them in the summary, and evaluate the pilot rows.**
- [x] **Step 5: Generate raw CSV, summary JSON, design report, and decision report with no post-hoc parameter changes.**

### Task 5: Final verification and local commit

**Files:**
- Modify: `task_plan.md`, `findings.md`, `progress.md`

- [x] **Step 1: Re-read this plan and verify each P2 requirement against generated artifacts.**
- [x] **Step 2: Run `PYTHONPYCACHEPREFIX=/tmp/v3-p2-pyc PYTHONPATH=src:. python -m compileall src app scripts tests`.**
- [x] **Step 3: Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. pytest -q -p no:cacheprovider`.**
- [x] **Step 4: Run `git diff --check`, frozen-core diff checks, and `git status --short --branch`.**
- [x] **Step 5: Commit locally with `research: evaluate V3-P2 capacity expansion`; do not push or merge.**
- [x] **Step 6: Rerun status and report exact HEAD, commit, metrics, limitations, and `INDEPENDENT_VALIDATION_READINESS`.**

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| NumPy emitted a zero-variance correlation warning during the first channel run | 1 | Replaced the diagnostic correlation calculation with an explicit zero-variance-safe matrix operation and reran; numerical summaries were unchanged. |
