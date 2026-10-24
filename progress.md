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
