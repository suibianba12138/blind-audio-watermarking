# V4-P8 AAC Channel Correction Report

**Date:** 2026-11-05\
**Status:** `V4_P8_STATUS = PASS`\
**Scope:** Audit the existing P4 channel path, make a bounded correction to the locally generated AAC/M4A decoded output range, and re-run P6’s 12 frozen sources. No model, threshold, V3, P0–P7 result, GUI layout, or online service was changed.

## 1. Finding: P4 Studio did not use P6’s ADTS path

The P6 experiment encoded AAC-LC into ADTS and decoded by taking the first 12 seconds of FFmpeg PCM output. P7 showed that this path retains one 1,024-sample leading priming frame.

The P4 Studio implementation is different: `app/v4_audio_processing.py` already encodes AAC as `.m4a` using FFmpeg AAC-LC and decodes that M4A through FFmpeg. The MP4/M4A packet metadata reports `skip_samples=1024`; FFmpeg handles the priming at decode time. Therefore the P4 Studio did **not** have P6’s measured leading-priming defect.

The remaining issue in the generated Channel Lab artifact was trailing padding: for a 12-second 44.1 kHz file, FFmpeg returned 529,408 decoded samples although the original valid range is 529,200 samples. The old function returned that extra 208-sample tail in the playable decoded WAV and duration.

## 2. Bounded correction

`_encode_codec()` keeps the existing AAC-LC/M4A encode and FFmpeg metadata-aware decode. For this application-generated AAC round trip only, it now:

1. Probes the generated M4A and verifies its sample rate matches the input and it is mono.
2. Leaves the beginning intact; it discards **zero** leading samples because FFmpeg has already applied M4A priming metadata.
3. Refuses to continue if decoded PCM is shorter than the known input sample count.
4. Trims only decoded samples beyond the known input count, rewrites the playable float WAV to that effective range, and returns the encoded metadata, pre-trim decoded count, valid sample range, leading samples discarded, and tail padding removed.

For the tested 44.1 kHz / 12 s path, the range is `[0, 529200)`, with 208 tail samples removed. The encoded stream reports AAC-LC, mono, 44.1 kHz, 12.0 s; its first packet carries `skip_samples=1024` and a PTS of -1024 samples. The decode output contains 529,408 samples before the bounded tail trim and 529,200 afterward.

This rule is scoped to the Studio’s own M4A round trip, where the original sample count is known. External uploads still use the ordinary FFmpeg decoder path. No fixed 1,024-sample trimming was added to `load_audio_file()` or to arbitrary ADTS inputs.

The test-first regression initially failed at the expected length assertion (`529408 != 529200`). After the change, the audio-processing suite passed: **8 tests, all passing**. The 12-source experiment below also exercised the actual shared `process_channel()` AAC/M4A implementation for all marked and unmarked M4A conditions.

## 3. Frozen protocol and pairing

The P8 run reused the exact P6 source manifest and its SHA-256, the same 12 unique recordings/crops, and one fixed message per source. All P6 sources are 16 kHz recordings resampled to SilentCipher’s 44.1 kHz input; therefore this is not a native high-rate music test. The protocol remained:

- Sony SilentCipher official 44.1 kHz `73999_iteration` checkpoint; each checkpoint hash was verified against the P1 frozen result.
- 40-bit message `D3916B24E8`; default `message_sdr=47 dB`.
- P1 presence threshold `0.6805555373430252`, unchanged; phase-shift decoding disabled.
- One model embedding per source, written once to a shared PCM16 WAV. WAV, ADTS, and M4A positive conditions consumed the same marked PCM16 samples. Per-source SHA-256 of this shared marked WAV is included in the results JSON.
- ADTS B used the original P6 FFmpeg AAC-LC 128 kbps ADTS encode/decode and first-12-second slicing protocol. M4A C used the corrected shared Studio `process_channel()` round trip.
- Negative WAV, ADTS, and M4A cases used the same unmarked source crop. Detector calls received only the received waveform and frozen model/policy. Expected payload was used only after decoding to calculate offline exact-recovery metrics.

This is a paired channel-protocol regression on previously used P6 sources, **not** a new independent holdout set or a formal AAC generalization estimate.

## 4. Results by source

`UNKNOWN` includes a valid candidate below the frozen presence threshold, as in `environment_04` M4A. Exact candidate recovery and correct accepted recovery are reported separately.

| Source | Type | WAV clean | P6 ADTS raw | Corrected AAC M4A |
|---|---|---|---|---|
| music_01 | Music | exact / 0.968 | no candidate / UNKNOWN | exact / 0.865 / IDENTIFIED |
| music_02 | Music | exact / 0.996 | `4F516FE0A0` / 0.583 / UNKNOWN | exact / 0.988 / IDENTIFIED |
| music_03 | Music | exact / 0.968 | `D391AB54E8` / 0.548 / UNKNOWN | exact / 0.909 / IDENTIFIED |
| music_04 | Music | exact / 0.996 | no candidate / UNKNOWN | exact / 0.940 / IDENTIFIED |
| speech_01 | Speech | exact / 0.984 | `816FA7E0D4` / 0.591 / UNKNOWN | exact / 0.925 / IDENTIFIED |
| speech_02 | Speech | exact / 0.976 | no candidate / UNKNOWN | exact / 0.929 / IDENTIFIED |
| speech_03 | Speech | exact / 0.976 | no candidate / UNKNOWN | exact / 0.921 / IDENTIFIED |
| speech_04 | Speech | exact / 0.976 | no candidate / UNKNOWN | exact / 0.917 / IDENTIFIED |
| environment_01 | Environment | exact / 1.000 | no candidate / UNKNOWN | exact / 0.996 / IDENTIFIED |
| environment_02 | Environment | exact / 0.929 | `5351AC10A8` / 0.508 / UNKNOWN | exact / 0.821 / IDENTIFIED |
| environment_03 | Environment | exact / 1.000 | `B052834281` / 0.623 / UNKNOWN | exact / 1.000 / IDENTIFIED |
| environment_04 | Environment | exact / 0.794 | no candidate / UNKNOWN | exact / 0.639 / UNKNOWN |

### Aggregate by condition

| Positive condition | Raw exact recovery | Correct accepted | Wrong-message accepted | UNKNOWN |
|---|---:|---:|---:|---:|
| WAV clean | 12/12 | 12/12 | 0/12 | 0/12 |
| Original P6 ADTS | 0/12 | 0/12 | 0/12 | 12/12 |
| Corrected AAC M4A | 12/12 | 11/12 | 0/12 | 1/12 |

The M4A result for `environment_04` is an exact candidate but confidence `0.638889`, below the unchanged threshold, so the correct system outcome is `UNKNOWN`. The policy was not tuned to accept it. The two other source classes had 4/4 correct accepted messages each; environment had 3/4 correct accepted and one exact-but-rejected candidate.

P8’s ADTS candidate and confidence matched the original P6 AAC records on **all 12/12 sources**. Thus the historical P6 `0/12` correct-accepted result is reproduced under the same ADTS protocol, while the M4A result isolates the container/priming correction.

### Unwatermarked negative cases

| Negative condition | Accepted | UNKNOWN | Decode error | Negative acceptance |
|---|---:|---:|---:|---:|
| Clean WAV | 0/12 | 12/12 | 0/12 | 0/12 |
| P6 ADTS | 0/12 | 11/12 | 1/12 | 0/12 |
| Corrected M4A | 0/12 | 12/12 | 0/12 | 0/12 |

The one negative ADTS decode error was `speech_04`; it failed closed and was not accepted. No positive condition produced a wrong-message acceptance.

## 5. Detection cost and signal handling

- SilentCipher model load: `0.037 s`; CPU threads: 4; process peak RSS: `1,604,820 KiB` (about 1.53 GiB).
- Mean embed time across 12 sources: `3.468 s` (range `3.313–3.745 s`).
- Mean detector time: clean WAV `6.015 s`, ADTS `5.967 s`, M4A `5.947 s` per decode.
- Mean AAC encode/decode time per item: ADTS `0.226 s`; corrected M4A `0.224 s` (P8 process observations).
- Every M4A encoded stream reported AAC-LC, mono, 44.1 kHz, 12.0 s. Every decoded M4A had 529,408 samples pre-trim, with effective samples `[0, 529200)` and 208 tail padding samples removed. No leading samples were discarded.

These are local CPU observations, not throughput guarantees. Presence remains provisional. The negative sample size is too small for a formal false-accept-rate claim.

## 6. Interpretation and next algorithm work

The corrected M4A protocol yielded 12/12 raw exact messages and 11/12 correct accepted messages, with no wrong-message acceptance and no negative acceptance in this bounded regression. This confirms that P6’s AAC conclusion was materially affected by the ADTS channel implementation. It does not establish general AAC robustness: all sources were reused, and the music sources were upsampled from 16 kHz.

Keep M4A as the Studio-generated AAC output and keep the known-input tail trim. Do not add a universal ADTS skip. Preserve external-file decoding as-is unless its own container metadata provides an explicit valid range.

For future algorithm-performance work, preserve the frozen confidence policy and focus on `environment_04`-like low-confidence exact candidates using a genuinely new, source-disjoint evaluation set. Do not lower the threshold based on this P8 set. Include native 44.1/48 kHz music and more negative sources before making broader robustness or false-accept claims.

## 7. Artifacts

- `experiments/v4_p8/RESULTS.json`: source hashes, model checkpoint hashes, one-embedding pairing hashes, per-condition detection records, FFprobe metadata, sample counts/ranges, codec and detection times, negative cases, and resource measurements.
- `tests/test_v4_p4_audio_processing.py`: AAC valid-range regression.
- `app/v4_audio_processing.py`: bounded M4A tail-padding handling and metadata return fields.

`V4_P6_ADVANCED_MODEL_COMPARISON_REPORT.md`, P6/P7 result files, SilentCipher weights, V3, GUI layout, Render, and online services were not modified. No audio, checkpoint, absolute machine paths, or credentials are included.
