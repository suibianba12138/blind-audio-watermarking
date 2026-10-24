# Blind Audio Watermarking V3 P0 Implementation Plan

> **For agentic workers:** This plan is the execution contract for the isolated `research/v3-p0` worktree. Keep frozen Course V2 source and historical results read-only.

**Goal:** Diagnose the current QIM/MP3 channel, audit and reproduce feasible open-source baselines, and run bounded single-bit/8-bit exploratory prototypes without claiming V3 superiority.

**Architecture:** The worktree is branched from `main` at `a89b493`. Frozen Course V2 modules remain unchanged. New audit scripts, experimental modules, tests, and P0 reports are additive and use separate result directories; calibration and test data are source-disjoint.

**Tech Stack:** Python 3.11-compatible public runtime, NumPy/SciPy, FFmpeg 128 kbps MP3, pytest, isolated third-party environments, and read-only GitHub/source audits.

## Global Constraints

- Do not modify frozen Course V2 implementation or historical results.
- Do not modify submitted SPL paper data, public webpages, or deployment configuration.
- Do not deploy to Render or upload user audio.
- Do not copy external GPL code into the MIT project.
- Do not use test data to choose parameters.
- Use real FFmpeg MP3 encode/decode for MP3 claims.
- Do not report paper metrics as local reproduction results.
- First-round autonomous experiments are limited to single-bit and 8-bit messages.
- Enter V3-P1 only if an independent, matched-fidelity test shows lower BER and better complete-message recovery without materially worse false acceptance or audio quality.

## Phase Gates

- [x] P0-0: isolated worktree from current `main`; baseline tests and clean state.
- [x] P0-A: source-level QIM/channel audit and diagnostic report; real-source data remains unavailable.
- [x] P0-B: open-source license/runtime/weight audit and bounded reproduction attempts; neural inference is blocked by environment.
- [x] P0-C: source/permission manifest and matched evaluation protocol; real legal dev/test split remains NOT_ESTABLISHED.
- [x] P0-D: single-bit/8-bit experimental prototypes on synthetic development probes only.
- [x] P0-E: recommendation and fail-closed NO-GO for V3-P1.
- [x] P0-F: final verification, local commit, and report of all failures/skips.
- [x] R1-A: freeze 60-source MUSAN metadata manifest with 10 dev/10 test per category.
- [x] R1-B: run real-source frozen B1 QIM per-physical-bit and FFmpeg MP3 audit.
- [x] R1-C: run paired 8-bit candidate versus B1 wrapper on the fixed 6-second protocol.
- [x] R1-D: calibrate and freeze a development-only blind presence threshold; evaluate test rejection.
- [x] R1-E: audit WavMark CPU prerequisites; local inference remains blocked.
- [x] R1-F: issue a fail-closed V3-P1 decision and preserve all tabular evidence.

## Planned Files

- Create `scripts/v3_p0_channel_audit.py`: frozen-source diagnostics only; no algorithm edits.
- Create `scripts/v3_p0_open_source_audit.py`: reproducibility/provenance ledger; no third-party source copied.
- Create `scripts/v3_p0_prototypes.py`: additive single-bit/8-bit experimental methods.
- Create `tests/test_v3_p0_contracts.py`: frozen-file immutability and prototype contract tests.
- Create `docs/V3_P0_OPEN_SOURCE_AND_CHANNEL_AUDIT.md`.
- Create `docs/V3_P0_BASELINE_COMPARISON.csv`.
- Create `docs/V3_P0_RECOMMENDATION.md`.
- Keep generated audio, model caches, and large results under `/tmp` or ignored local directories.

## Exact Verification Commands

```bash
python -m compileall src app scripts tests
pytest -q
git diff --check
git status --short --branch
```

The final gate also requires explicit evidence for FFmpeg MP3, source-disjoint data provenance, and each requested algorithm's `PASS`, `PARTIAL`, `SKIPPED`, or `BLOCKED` state.

## R1 Execution Contract

- Source files remain outside the repository; only hashes, metadata, CSV, and JSON results are stored.
- Candidate strength remains the pre-registered P0 development point `0.02`; no test-set tuning was performed.
- Two messages per source are paired observations, not independent recordings.
- The B1 comparison is an 8-bit logical wrapper over frozen 32-bit physical positions.
- The rejector uses only received audio and public/keyed configuration; the expected payload is used only after detection for scoring.
- Any missing WavMark dependency or weight remains `BLOCKED`, not a synthetic PASS.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Public `prepare_for_demo()` rejects local sources longer than 30 s | R1 experiment | Applied the same resample rule, then took the pre-registered first 6 s directly in the R1 script; public demo code was unchanged. |
| Heterogeneous B1/candidate CSV columns | R1 result write | Updated the additive CSV writer to use the union of row fields; experiment was rerun with the same protocol. |
