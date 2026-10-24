# V3 P0 Findings

This file records evidence as `CONFIRMED`, `INFERRED`, `UNAVAILABLE`, or `NOT_ESTABLISHED`. It is not a results claim until the source, command, and dataset provenance are recorded.

## Baseline

- Worktree: `/home/nsk/blind-audio-watermarking-v3-p0`
- Branch: `research/v3-p0`
- Base: `main@a89b493`
- Frozen implementation: not modified at initialization.

## Evidence Log

- `CONFIRMED`: `pytest -q -p no:cacheprovider` passed 7 tests on the base worktree.
- `CONFIRMED`: `compileall` passed using `PYTHONPYCACHEPREFIX=/tmp/v3-p0-baseline-pyc`.
- `CONFIRMED`: initial `git diff --check` passed; only the three planning files are untracked.
- `CONFIRMED`: frozen B1 QIM uses a binary lattice over A/B log-magnitude difference, with symmetric correction preserving pair midpoints; `strength=1.28` produced exact marked-frame signed margins on synthetic probes.
- `CONFIRMED`: synthetic FFmpeg 128k diagnostics produced MP3 BER 0.375 speech-like, 0.0 music-like, and 0.40625 environment-like; this is diagnostic-only, not a real-data result.
- `CONFIRMED`: synthetic MP3 repetition-statistic correlation differed by content (about -0.03, 0.96, -0.03 respectively); fixed repetition does not imply independent evidence.
- `CONFIRMED`: additive keyed local-normalized spread-spectrum prototype passed 3 contract tests and bounded 1/8-bit synthetic development trials.
- `CONFIRMED`: local environment has FFmpeg but no `torch`, `torchaudio`, `soundfile`, `librosa`, or audited third-party watermark packages; `audiowmark` CLI is absent.
- `CONFIRMED`: upstream audit found audiowmark GPLv3-or-later; WavMark and SilentCipher MIT repository licenses; AudioSeal official README states MIT code/weights; CRAW license chain remains REVIEW_REQUIRED; OmniSealBench common code MIT but model licenses vary.
- `UNAVAILABLE`: GitHub `git ls-remote` and local third-party source fetches were blocked by the current proxy, so no external repository was copied or run.
- `NOT_ESTABLISHED`: licensed real-source manifest, source-disjoint dev/test comparison, false-acceptance rates, and formal perceptual gate.
