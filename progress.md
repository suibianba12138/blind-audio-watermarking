# V3 P0 Progress Log

## 2026-10-24 Asia/Shanghai

- Created isolated `research/v3-p0` worktree from `main@a89b493`.
- Initialized `task_plan.md`, `findings.md`, and `progress.md`.
- Baseline verification passed: 7 pytest tests, compileall, and diff check.
- Audited frozen embed/detect/B1/Course V2 source and recorded the QIM lattice, signed statistic, repetition aggregation, carrier layout, and confidence semantics.
- Added `scripts/v3_p0_channel_audit.py`; ran deterministic speech-like/music-like/environment-like probes with real FFmpeg libmp3lame 128k round trips. Results are in `/tmp/v3-p0-channel-audit` and summarized in the P0 report.
- Added the isolated `v3_p0.py` keyed spread-spectrum/local-normalized prototype and `tests/test_v3_p0_contracts.py`; watched the import test fail before implementation, then reached 3 passing prototype contract tests.
- Added `scripts/v3_p0_prototypes.py`; ran bounded development strengths 0.02/0.04/0.08 for 1-bit and 8-bit payloads. Full trial ledger is committed as `docs/V3_P0_PROTOTYPE_TRIALS.csv`.
- Added `scripts/v3_p0_open_source_audit.py`; recorded current dependency/CLI/network availability without copying external code.
- Added required P0 audit, comparison, and recommendation reports. Real licensed source evaluation and neural baseline inference remain blocked/not established.
- Audited `/home/nsk/datasets/MUSAN` and froze `configs/v3_p0_r1_real_audio_manifest.json`: 60 source-disjoint metadata records, three categories, 10 dev/10 test per category, no raw audio copied.
- Added `v3_p0_r1.py` presence/rejection helpers with TDD regression coverage; the score penalizes signed repetition disagreement and is explicitly diagnostic rather than probabilistic.
- Added `scripts/v3_p0_r1_experiment.py`; ran the full 60-source paired evaluation with two fixed 8-bit messages, frozen B1 wrapper, P0 candidate, real FFmpeg 128k, and per-physical-bit QIM statistics.
- Saved final R1 evidence under `experiments/v3_p0_r1/` and generated `V3_P0_R1_REAL_AUDIO_REPORT.md`, `V3_P0_R1_DETECTION_REPORT.md`, and `V3_P0_R1_DECISION.md`.
- R1 decision: real-audio evidence is established, but candidate MP3 recovery is below B1, rejection has test false accepts, fidelity is not matched, and WavMark CPU inference is blocked; `V3_P1_READINESS = NO_GO`.
- Added the bounded B1 soft-code pilot contract: fixed strengths `0.96/1.28/1.60`, fixed
  source-disjoint manifest, two paired 8-bit messages, frozen B1 embed path, and dev-only
  presence calibration.
- Added `b1_soft.py` and regression tests for the continuous physical QIM statistics, blind
  detector contract, fixed `[32,8,8]` codebook, and clean-message decoding.
- Corrected a pilot bookkeeping bug before using results: clean and clean-MP3 negatives were
  accidentally repeated across strengths; the corrected run was executed in a fresh `/tmp`
  output directory and contains 2,880 rows with balanced counts.
- Ran the corrected 60-source pilot with real FFmpeg 128 kbps. Soft-code at strength 1.60
  achieved `59/60` MP3 exact trials and `29/30` source recordings with both paired messages
  exact, versus `48/60` and `23/30` for repeat-4 at the same SNR budget.
- Added the pilot report, CSV/JSON evidence, frozen-manifest regression, and no-download
  WavMark CPU feasibility audit. Decision is `CONDITIONAL_GO_NARROW_V3_P1_ONLY`; no V3-P1
  implementation or public integration was started.
