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
- Created branch `research/v3-p1` from clean `34411a9` and wrote the P1 implementation plan.
- Froze `configs/v3_p1_independent_manifest.json`: 60 new source recordings, three categories,
  10 dev/10 test per category, no path/SHA overlap with R1 or the Soft-Code Pilot.
- Added and TDD-tested the hard-code control. The focused hard-code and freeze-contract tests
  pass (`6 passed`); no frozen B1/Course V2 file was modified.
- Wrote `experiments/v3_p1/CONFIG_FREEZE.json` with the Pilot threshold/strength, source and
  code hashes, selector provenance, and FFmpeg 128 kbps version.
- Added and ran the fixed P1 evaluator on all 60 sources. After one field-name fix and one
  report-layer applicability fix, the final rerun was written to a new `/tmp` directory and
  copied as the P1 evidence artifacts.
- Added fixed-threshold negative analysis, Wilson intervals, source-level aggregation, and exact
  McNemar comparisons. Soft-Code vs Repeat-4 was `10/0` discordant sources with exact p-value
  `0.001953125`.
- Added clipping provenance fields that distinguish pre-existing input over-amplitude from
  embedding-introduced clipping; P1 introduced clipping was `0/60`.
- Added the independent validation report, detection report, decision, A/B listening protocol,
  artifact tests, and P1 analysis JSON. Current decision is `V3_P2_READINESS = CONDITIONAL_GO`.
- Confirmed clean `research/v3-p1@82f8013` and created the isolated local branch `research/v3-p2`; no push or merge performed.
- Started P2-D0/P2-D1 planning. The P2 scope is a development-only capacity design pilot over the pre-existing P1 development split; P1 formal test records remain unavailable for encoder or threshold selection.
- Added and executed the P2 baseline freeze script. The focused P2 artifact tests first failed because the freeze artifact was absent, then passed after writing `experiments/v3_p2/CONFIG_FREEZE.json`.
- Added and tested deterministic 12/16-bit Boolean evaluation-code adapters, preserving exact equivalence with the frozen 8-bit codebook. Added development-only physical channel diagnostics and real MP3 paired rows; reran once to remove a zero-variance correlation warning without changing values.
- Ran the finite capacity pilot with calibration-only candidate thresholds and protocol-identical reruns after adding physical/logical BER and source-level aggregation. Generated `V3_P2_CAPACITY_DESIGN.md`, `V3_P2_CAPACITY_PILOT.csv`, `V3_P2_CHANNEL_ERROR_ANALYSIS.md`, and `V3_P2_DECISION.md`; current bounded decision is `CONDITIONAL_GO_12BIT_ONLY`.
- Created local commit `72a781d` (`research: evaluate V3-P2 capacity expansion`) after the final compileall, 47-test suite, diff check, and frozen-core check. No push or merge was performed.

## 2026-10-25 — V3-RC1

- Reconfirmed the integration branch, actual HEAD, and clean starting worktree.
- Read the persistent planning and browser-control procedures; added an RC1-specific execution addendum without changing frozen algorithm scope.
- Next: audit launch/deployment configuration, perform isolated runtime and browser availability checks, then write RC1 evidence reports.
- Audited entry points, GUI callbacks, audio limits, and session store. Found and corrected the RC1 deployment/security mismatch from 64 MiB to 16 MiB with a red/green regression test; frozen algorithm files were not touched.
- Docker client exists (`29.5.0`) but the daemon socket is inaccessible in this environment; the V3 branch also contains no Dockerfile/compose/Render blueprint. The public staging Dockerfile is Legacy-only and was retained as an audit reference.
- Full regression passed: `106 passed, 1 skipped`; compileall and diff check passed after the security-layer change.
- Added Legacy opaque-session hardening and TDD regressions. After correcting the path argument at the encoder boundary, real callback flows passed for UESTC-003 at 6/15/30 seconds and no-watermark returned UNKNOWN.
- Added Gradio launcher queue/upload limits (`default_concurrency_limit=1`, `max_size=4`, `max_file_size=16mb`) with regression coverage. The pinned isolated runtime then passed HTTP/config and final V3/Legacy client smoke.
- Browser connection was attempted using the required browser surface; no browser backend was available, so browser acceptance remains NOT_ESTABLISHED. Existing Legacy Docker built/ran as a limited reference; V3 Docker remains BLOCKED by missing descriptors.
- Wrote the four RC1 reports. Final verification is `110 passed, 1 skipped`, compileall PASS, diff-check PASS; status remains CONDITIONAL because browser, V3 Docker, Render, and formal perceptual gates are not established.
