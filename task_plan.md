# Blind Audio Watermarking V3 P0/P1/P2 Implementation Plan

> **For agentic workers:** This plan is the execution contract for the isolated `research/v3-p2` worktree. Keep frozen Course V2 source, R1/Pilot/P1 evidence, and historical results read-only.

**Goal:** Preserve completed V3-P0/P1 evidence and run a bounded, development-only V3-P2 capacity design pilot without changing the frozen B1 physical channel.

**Architecture:** The current branch is `research/v3-p2`, based on `research/v3-p1@82f8013`. Frozen Course V2/B1/P1 modules and P0/R1/Pilot/P1 evidence remain unchanged. P2 adds only a baseline freeze record, development-only channel diagnostics, deterministic 12/16-bit evaluation-code adapters, a paired pilot, and reports.

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
- P2 uses only the pre-existing P1 development split for design diagnostics and pilot; no P1 formal test source is used to select an encoder or threshold.
- The 8-bit Soft-Code strength, thresholds, selector seed, QIM implementation, and P1 evidence remain immutable.
- P2 thresholds for 12/16-bit candidates are selected from a deterministic calibration subset of P1 development sources and evaluated on a held-out development pilot subset; this is not independent validation.
- No push, merge, public-site change, Render change, neural training, or large-scale experiment is permitted.

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
- [x] B1-SC-1: freeze a second source-disjoint 60-source pilot manifest.
- [x] B1-SC-2: add tested continuous B1 soft-decoder and fixed [32,8,8] code.
- [x] B1-SC-3: run finite strength/SNR curve and paired clean/MP3 evaluation.
- [x] B1-SC-4: calibrate dev-only rejection, audit WavMark CPU feasibility, and decide stop/go.
- [x] P1-A: freeze Pilot configuration, code/source hashes, and the new independent manifest.
- [x] P1-B: add and test the hard-code control without changing frozen B1/Soft-Code code.
- [x] P1-C: run the three-method paired no-attack/MP3 evaluation.
- [x] P1-D: run fixed-threshold negative controls and source-level paired statistics.
- [x] P1-E: document limited perceptual review, final decision, and fresh verification.
- [x] P2-D0: freeze the 8-bit baseline source/configuration hashes and operating point.
- [x] P2-D1: run development-only 32-position channel diagnostics and model checks.
- [x] P2-D2: add tested deterministic 12-bit and 16-bit evaluation codes without QIM changes.
- [x] P2-D3: run the finite paired capacity pilot on calibration/pilot development subsets.
- [x] P2-D4: evaluate capacity-specific rejection and wrong-key/negative controls.
- [x] P2-D5: issue a bounded decision and preserve all raw results without independent-validation claims.
- [ ] P2-D6: run full verification, commit locally, and report no-push status.

## Planned Files

- Create `scripts/v3_p0_channel_audit.py`: frozen-source diagnostics only; no algorithm edits.
- Create `scripts/v3_p0_open_source_audit.py`: reproducibility/provenance ledger; no third-party source copied.
- Create `scripts/v3_p0_prototypes.py`: additive single-bit/8-bit experimental methods.
- Create `tests/test_v3_p0_contracts.py`: frozen-file immutability and prototype contract tests.
- Create `docs/V3_P0_OPEN_SOURCE_AND_CHANNEL_AUDIT.md`.
- Create `docs/V3_P0_BASELINE_COMPARISON.csv`.
- Create `docs/V3_P0_RECOMMENDATION.md`.
- Create `src/audio_watermark/b1_soft.py`, `scripts/v3_b1_soft_pilot.py`, and
  `scripts/v3_b1_wavmark_audit.py` as additive pilot-only artifacts.
- Create `configs/v3_b1_soft_pilot_manifest.json` and keep raw source audio outside the repository.
- Create `experiments/v3_b1_soft_pilot/` results and `V3_B1_SOFT_CODE_PILOT.md`.
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

## B1 Soft-Code Pilot Contract

- The pilot is finite and local; it is not a new long-term V3 branch.
- The fixed strength curve is `(0.96, 1.28, 1.60)` and is not expanded after seeing test results.
- The new manifest excludes both audited Course V2 manifests and the full R1 manifest; R1 test sources are diagnostic only for this pilot.
- The code is a deterministic evaluation-code `[32, 8, 8]` with 256 codewords; only the 8-bit logical payload is scored as the effective message.
- Soft detection uses only received audio, frozen B1 config/selector, and the codebook. Expected payload is used only after detection for scoring.

## V3-P1 Independent Validation Contract

- Branch is `research/v3-p1`, based on local commit `34411a9660c1b8b0bfaf3f6e72b62e18984d8145`.
- Frozen Pilot operating point is strength `1.60`, threshold `0.7855073980199624`, selector seed `7`, message seeds `101/202`, and 6-second 48 kHz audio.
- P1 manifest excludes all audited Course V2, R1, and B1 Soft-Code Pilot records by path and SHA256 before evaluation.
- Controls are Repeat-4, Hard-Code using hard minimum-Hamming decode of the same `[32,8,8]` code, and Soft-Code using the frozen continuous correlation decoder.
- Threshold is not re-fit on P1; P1 negative counts are evidence with confidence intervals, not a claim of a population FPR bound.
- Primary independent unit is source recording; two messages per source are paired trials.

## V3-P2 Capacity Design Contract

- Branch is `research/v3-p2`, based on `research/v3-p1@82f80138654b283e05da4d41bea71144a20f1120`.
- Frozen 8-bit baseline is the P1 Soft-Code `[32,8,8]` code, strength `1.60`, soft threshold `0.7855073980199624`, physical threshold `0.47678591988959035`, selector seed `7`, and message seeds `101/202`.
- Development sources are the P1 manifest records with `split=dev`; an immutable category-balanced first-five/last-five subdivision supplies calibration and pilot roles. P1 `split=test` records are diagnostic-only and cannot select code or thresholds.
- New candidates are deterministic degree-2 Boolean evaluation codes over 5-bit position labels: 12-bit and 16-bit message dimensions, both 32 physical bits and minimum Hamming distance 8. At most these two new candidates are evaluated.
- Candidate embedding uses the existing B1 QIM embed path and public detector contract. The detector receives only received audio, selector/configuration, and the candidate codebook; expected messages and clean audio are not detector inputs.
- Thresholds for 12/16-bit presence are calibrated only from the P2 calibration subset, then frozen for the held-out development pilot subset. P2 results are feasibility evidence, not independent validation.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Public `prepare_for_demo()` rejects local sources longer than 30 s | R1 experiment | Applied the same resample rule, then took the pre-registered first 6 s directly in the R1 script; public demo code was unchanged. |
| Heterogeneous B1/candidate CSV columns | R1 result write | Updated the additive CSV writer to use the union of row fields; experiment was rerun with the same protocol. |
| `DetectionResult` field is `payload_bits`, not `payload` | First P1 evaluator run | Added a focused regression helper, changed only the evaluator field access, and reran the full P1 evaluation from a fresh output directory. |
| No-attack rows store MP3 fidelity as `NOT_APPLICABLE` | First P1 analysis run | Analysis now excludes non-applicable values instead of coercing them; raw results were unchanged. |
| Focused pytest initially could not import `app` and attempted to write `.pytest_cache` | RC1 TDD red test | Re-ran with the repository contract `PYTHONPATH=src:.` and `-p no:cacheprovider`; the new 16 MiB assertion then failed for the expected 64 MiB implementation reason. |
| Docker client could not access `/var/run/docker.sock` | RC1 Docker audit | Kept the Docker build gate BLOCKED; audited the separate public-staging Legacy Dockerfile as a reference and did not claim V3 container evidence. |
| Legacy session-store refactor initially passed `SessionHandle` where the MP3 helper requires a filesystem path | RC1 Legacy mode smoke | Added a focused regression asserting `session.root`; changed only the callback storage boundary, then reran 6/15/30-second flows successfully. |
| Gradio could not bind the requested port 7863 | RC1 isolated GUI startup | Port 7863 was occupied; changed only the local test port to 7865 for the same localhost runtime. |
| Gradio client could not connect from the restricted sandbox | RC1 client smoke | The server was reachable with escalated localhost HTTP; rerun the client smoke with the same isolated external permission, without changing application code. |
| Gradio client passed a raw string to a FileData input | RC1 client smoke | Changed the client harness to use the pinned `gradio_client.handle_file()` representation; this was a test-harness input-shape issue, not an application callback failure. |
| Independent reviewer could not be spawned | RC1 final review | Agent thread limit was already reached; performed the required local diff/frozen-file/test audit instead and recorded the limitation. |
| Formatting-only EOF cleanup was blocked in the restricted worktree | RC1 final docs | Re-ran the exact four-file whitespace cleanup with the required local escalation; `git diff --check` then passed. |

## V3-RC1 Addendum (2026-10-25)

**Goal:** Validate the frozen V3-8bit integration for release-candidate readiness without changing the algorithm, frozen parameters, historical evidence, public site, Render, or remote Git state.

### RC1 phases

- [x] RC1-A: audit current branch, prior acceptance evidence, V3/Legacy launch paths, and clean state.
- [ ] RC1-B: attempt real browser interaction; keep browser evidence fail-closed if no controllable browser is available. **PARTIAL: backend unavailable.**
- [x] RC1-C: verify WAV/MP3 download, re-upload, decoded PCM, file hashes, and session isolation.
- [ ] RC1-D: audit/build/run Docker locally where the daemon permits; record resource and Render limitations. **PARTIAL: Legacy reference only; V3 descriptor missing.**
- [x] RC1-E: perform regression, input-limit, cleanup, and finite audio-quality screening checks. **Audio formal gate remains NOT_ESTABLISHED.**
- [x] RC1-F: write RC1 acceptance, browser checklist, Docker report, deployment plan; commit locally only if all evidence is recorded.

### RC1 constraints

- No algorithm, QIM, Soft-Code, capacity, strength, threshold, selector, or fusion changes.
- No push, fetch, merge, production deployment, or public-service mutation.
- Browser PASS requires actual browser interaction; HTTP/client smoke is separate evidence.
- Formal perceptual quality remains unestablished unless an actual documented listening session occurs.
- Render readiness is not inferred from local Docker alone.
