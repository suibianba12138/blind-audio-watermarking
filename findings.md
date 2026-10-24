# V3 P0/P1/P2 Findings

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

## B1 Soft-Code Pilot Evidence

- `CONFIRMED`: a second frozen manifest contains 60 source-disjoint records (20 per category,
  10 dev/10 test); it has zero path/SHA overlap with the R1 manifest.
- `CONFIRMED`: the additive soft detector returns continuous frozen-QIM margins and uses a
  fixed deterministic `[32,8,8]` codebook; expected payload and clean audio are not detector inputs.
- `CONFIRMED`: the corrected fixed pilot produced 2,880 rows with one clean and one clean-MP3
  negative row per source/method/strength/condition, avoiding the earlier duplicate-negative bug.
- `CONFIRMED`: on 30 source-disjoint test recordings with two paired messages, soft-code at
  strength 1.60 achieved MP3 logical BER `0.004167`, exact recovery `59/60`, and two-message
  source recovery `29/30`; the repeat-4 wrapper at the same strength achieved BER `0.029167`,
  exact `48/60`, and `23/30` sources.
- `CONFIRMED`: at soft-code strength 1.60, clean and clean-MP3 test FPR were both `0/30`,
  positive MP3 wrong-message acceptance was `0/60`, and wrong-key MP3 acceptance was `2/60`
  trials from one source.
- `CONFIRMED`: at strength 1.60 the paired embedding SNR was `53.698 dB` for soft-code and
  `53.692 dB` for repeat-4; this is a paired numerical fidelity check, not a perceptual study.
- `BLOCKED`: WavMark CPU inference was not attempted because local Python 3.13.5 has no torch,
  torchaudio, wavmark package, or local weight; no dependency or model was downloaded.
- `CONDITIONAL_GO`: the finite pilot supports only a narrow, separately authorized V3-P1
  review; it does not authorize production integration, broad parameter search, or a claim
  about arbitrary 32-bit messages.

## V3-P1 Freeze Evidence

- `CONFIRMED`: branch `research/v3-p1` was created from clean `research/v3-p0@34411a9`.
- `CONFIRMED`: the new P1 manifest has 60 source records, 20 per category, 10 dev/10 test,
  minimum duration 7.5 seconds, and unique source group/path/SHA values.
- `CONFIRMED`: P1 manifest path and SHA overlap with both R1 and Soft-Code Pilot manifests is
  zero; the two audited Course V2 manifests were also supplied as exclusions.
- `CONFIRMED`: Pilot operating point is frozen at strength `1.60`, soft threshold
  `0.7855073980199624`, repeat/hard physical-evidence threshold `0.47678591988959035`,
  selector seed `7`, message seeds `101/202`, 48 kHz, and 6 seconds.
- `CONFIRMED`: hard-code control reuses the fixed `[32,8,8]` codeword but decodes only hard
  physical bits by minimum Hamming distance; all four TDD contract tests pass.
- `CONFIRMED`: `CONFIG_FREEZE.json` records source SHA256, manifest SHA256, codebook SHA256,
  FFmpeg version, selector/map provenance, and the blind detector contract.

## V3-P1 Independent Validation Evidence

- `CONFIRMED`: the final P1 rerun generated 720 positive rows and 720 negative rows for 60
  source recordings, two fixed messages, three methods, and clean/no-attack plus MP3 conditions.
- `CONFIRMED`: on the 30-source formal test split, Repeat-4 exact recovery was `46/60` trials
  and `20/30` sources with both messages exact; Hard-Code was `58/60` and `28/30`.
- `CONFIRMED`: Soft-Code decoded exact recovery was `60/60` trials and `30/30` sources with
  both messages exact; the frozen threshold accepted `59/60` MP3 positives because one exact
  decode was below threshold.
- `CONFIRMED`: Soft-Code physical BER was `0.06458`, essentially the same channel-level range
  as Repeat-4 `0.06302`; logical BER was `0` versus `0.03333`, so the improvement is decoded
  code performance rather than a physical-BER claim.
- `CONFIRMED`: source-level McNemar exact p-values were `0.001953125` for Soft-Code versus
  Repeat-4 and `0.0078125` for Hard-Code versus Repeat-4; discordant pairs favored the new controls.
- `CONFIRMED`: Soft-Code clean and clean-MP3 FPR were `0/30` each, wrong-key acceptance was
  `0/60`, and positive wrong-message acceptance was `0/60`. Wilson upper bounds remain 6.02%
  for the 60-trial negative denominators; no `<1%` population claim is made.
- `CONFIRMED`: mean embedding SNR was `57.657 dB` for Soft/Hard versus `57.788 dB` for
  Repeat-4; mean LSD difference was `0.00053 dB`, but the maximum paired SNR difference was
  `6.413 dB`, so fidelity is partial rather than exact per-source matching.
- `CONFIRMED`: four test Environment sources had pre-existing peak values above 1.0, giving
  eight message rows with clipping flags; introduced clipping was `0/60` for all methods.
- `NOT_ESTABLISHED`: no formal human listening study was completed; the protocol is documented
  and the perceptual gate remains not established.
- `CONDITIONAL_GO`: P1 supports a narrow V3-P2 design review, not immediate deployment or
  claims about arbitrary messages/codecs.

## V3-P2 Design Evidence

- `CONFIRMED`: the isolated worktree was clean at `research/v3-p1@82f80138654b283e05da4d41bea71144a20f1120`; P2 work is being performed on a new local `research/v3-p2` branch.
- `IN_PROGRESS`: P2-D0 baseline freeze and development-only channel diagnostics. No P2 candidate result is a validated independent result until a future source-disjoint validation.
- `CONFIRMED`: `experiments/v3_p2/CONFIG_FREEZE.json` records the P1 Soft-Code strength `1.60`, frozen soft threshold `0.7855073980199624`, physical threshold `0.47678591988959035`, selector seed `7`, message seeds `101/202`, 48 kHz/6 s, FFmpeg libmp3lame 128k, and source/configuration hashes.
- `CONFIRMED`: P2 D0 declares the detector blind-input contract and explicitly marks P1 formal test data as unavailable for code/threshold selection; future independent validation is `NOT_ESTABLISHED`.
- `CONFIRMED`: P2 channel analysis used 30 P1 development sources, 60 paired messages, and 1,920 MP3 physical observations. Marked/no-attack BER was 0; MP3 physical BER was 0.0546875. Error-count dispersion was 2.1081 times IID expectation, with mean off-diagonal error correlation 0.03683 and maximum contiguous error run 2.
- `CONFIRMED`: Full deterministic Boolean evaluation codebooks have 32 positions and minimum Hamming distance 8 for 8, 12, and 16 message bits. The 12-bit and 16-bit adapters are additive and leave the physical QIM path unchanged.
- `CONFIRMED`: Held-out development pilot results were 30 paired MP3 message trials from 15 unique source recordings per method. Soft8 raw/accepted-exact was 30/30 and 28/30, with 14/15 sources accepting both messages; 12-bit was 30/30 and 27/30, with 13/15 sources accepting both; 16-bit was 28/30 and 26/30, with 12/15 sources accepting both. Clean FPR, clean-MP3 FPR, wrong-key acceptance, and wrong-message acceptance were zero at the source level (0/15 each; 30 paired rows).
- `CONDITIONAL_GO`: P2 supports only a new independent validation of the frozen 12-bit candidate. The 16-bit branch is stopped; no capacity tuning or independent-validation claim is authorized.
- `CONFIRMED`: final compileall and full pytest passed after all P2 changes; frozen-core comparison and diff checks passed. Local commit `72a781d` contains the P2 design, code, tests, and raw/statistical artifacts; nothing was pushed.
