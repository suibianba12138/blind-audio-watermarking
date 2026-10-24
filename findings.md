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

## R1 Real-Source Evidence

- `CONFIRMED`: frozen manifest contains 60 unique local MUSAN source recordings, 20 each for Speech/Music/Environment, with 10 dev and 10 test per category; all are 16 kHz mono WAV and have SHA256 metadata.
- `CONFIRMED`: raw audio was not copied into the repository; the manifest records source paths, license detail, duration, encoding, and audited Course V2 manifest exclusion status.
- `CONFIRMED`: real FFmpeg 128 kbps paired evaluation ran on 6-second prefixes, with two fixed 8-bit messages per source and a frozen candidate strength of 0.02.
- `CONFIRMED`: test MP3 exact recovery was 49/60 for frozen B1 8-bit wrapper versus 39/60 for the candidate; test logical BER was 0.033333 versus 0.054167.
- `CONFIRMED`: B1 marked-to-MP3 sign flip and boundary-distance behavior remained content-dependent on the real source manifest, with Environment showing the highest test flip rate (0.1297).
- `CONFIRMED`: development-only candidate threshold was 0.07846780628511643; test clean FPR was 3/30 source recordings and wrong-key acceptance was 4/60 conditions.
- `CONFIRMED`: candidate fidelity was not matched to B1: test embedding SNR was 46.299 dB versus 57.144 dB for B1; formal perceptual testing remains not established.
- `BLOCKED`: WavMark CPU inference was not locally reproduced because the isolated environment has no torch, torchaudio, wavmark package, or local WavMark weight; no paper metric is reported as local evidence.
- `NO_GO`: R1 does not support entry into V3-P1; the candidate is retained as research code only.
