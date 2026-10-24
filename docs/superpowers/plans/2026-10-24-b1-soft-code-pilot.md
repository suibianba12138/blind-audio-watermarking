# V3 B1 Soft-Code Pilot Implementation Plan

> **For agentic workers:** Execute this bounded plan inline in the current isolated worktree. Do not push, merge, deploy, or modify frozen Course V2/R1 evidence.

**Goal:** Evaluate whether a fixed `[32,8,8]` short code plus continuous B1-QIM soft statistics improves 8-bit MP3 recovery on a newly frozen source-disjoint test set.

**Architecture:** Keep `b1.py`, `embed.py`, `detect.py`, and Course V2 untouched. Add a small pure-Python codebook/soft-detector module, reuse the existing B1 embedding path, freeze a second local MUSAN manifest that excludes R1 and audited Course V2 paths, and run a predeclared finite strength curve with dev-only threshold calibration.

**Tech Stack:** Existing NumPy/SciPy runtime, frozen B1/REAL_TOP32 selector, real FFmpeg 128 kbps, pytest, CSV/JSON evidence, and an isolated WavMark prerequisite audit.

## Global Constraints

- Preserve the R1 commit and all R1 evidence as read-only reference.
- Do not modify Course V2, public website, Render, or submitted paper data.
- Do not pass expected payload, correct identity, clean audio, or source filename to the detector.
- Use only the new frozen source-disjoint test set for formal pilot conclusions; R1 remains diagnostic only.
- Use a finite predeclared strength curve `(0.96, 1.28, 1.60)`; no broad search.
- Calibrate soft/rejection thresholds on dev only and freeze them before test evaluation.
- Do not add ECC beyond the fixed `[32,8,8]` code, do not add codec-aware selection, and do not push.

## Tasks

### Task 1: Freeze independent source manifest

Create `configs/v3_b1_soft_pilot_manifest.json` by invoking the existing parameterized manifest freezer with both audited Course V2 manifests and `configs/v3_p0_r1_real_audio_manifest.json` as exclusions. Use 20 new sources per category, split 10 dev/10 test, and record SHA256, duration, encoding and source license detail. No audio is copied into Git.

### Task 2: Define the soft-code contract with tests first

Create `tests/test_b1_soft_code.py` covering: 256 unique codewords, minimum pairwise Hamming distance 8, exact encode/decode on clean soft evidence, rejection of invalid payload size, and the blind detector signature having no expected-payload argument. Run the focused test before implementation and observe the missing-module failure.

### Task 3: Implement the additive soft detector

Create `src/audio_watermark/b1_soft.py` with a deterministic `[32,8,8]` evaluation-code codebook, `detect_watermark_b1_soft(audio, config, selector)`, and `decode_b1_soft_detection(detection)`. Aggregate the existing `_detection_statistic` across the four frozen repetitions per physical bit, retain continuous signed margins, choose the maximum normalized correlation codeword, and expose a diagnostic margin/presence score. No expected payload enters either function.

### Task 4: Run finite paired pilot

Create `scripts/v3_b1_soft_pilot.py`. For two fixed new message seeds and each source, compare the old four-repeat logical wrapper with the fixed code at the three predeclared strengths `(0.96, 1.28, 1.60)` under clean and real FFmpeg 128 kbps MP3. Record physical raw BER, logical exact recovery, SNR, log-spectral distortion, source/category/split, runtime, and per-source paired outcomes.

### Task 5: Calibrate rejection and audit WavMark

Calibrate one presence threshold per method/strength from dev positive and negative scores only. Test clean, clean MP3, wrong-key marked MP3, and accepted-but-wrong-message cases on the new test split. Record WavMark Python/Torch availability, local model availability, disk, and model metadata without downloading weights or modifying Render.

### Task 6: Report and gate

Create `V3_B1_SOFT_CODE_PILOT.md` and the raw pilot CSV under `experiments/v3_b1_soft_pilot/`, update planning evidence, run compileall/pytest/diff-check/status, and stop with `V3_ALGORITHM_DECISION = STOP` unless the new code shows stable improvement at comparable SNR without worse rejection.
