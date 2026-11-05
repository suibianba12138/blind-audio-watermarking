# V4-P10 — Blind Detection Calibration & File Decoding Consistency Report

**Decision:** `V4_P10_DECISION = INCONCLUSIVE`\
**Operational policy:** retain the P1-frozen `0.6805555373430252` threshold and the current Studio backend.\
**Calibration label:** `PRESENCE_CALIBRATION = PROVISIONAL`

## 1. Scope and evidence boundaries

This stage audited the file-read/preprocessing path, replayed a bounded native-rate-versus-Studio M4A path comparison, reviewed P1–P9 decoder/presence evidence, and checked the meaning of P9 `DECODE_ERROR` records. No SilentCipher code, model weights, P0–P9 reports/results, V3 algorithm, GUI, or Render service was changed.

The P9 positive/negative audio files had been removed after that stage. The P9 result artifact preserves the external M4A hash and scores, but not the M4A itself or the original PCM. A new-source calibration set was not locally available. A direct source download attempt could not reach the configured local network proxy, so no new source was acquired. Consequently, the independent threshold validation required by P10 was **not run**. Historical records below are development/diagnostic evidence only.

Evidence labels used here:

- **SOURCE REVIEWED:** code/result artifact inspected.
- **RUNTIME PATH CHECK:** same locally generated M4A passed through two independent file-decoding paths.
- **NOT VALIDATED:** independent threshold holdout, exact P9 M4A A/B replay, broad file-decoder generalization.

## 2. Studio file-decoding path

### Source review

`app/v4_audio_processing.py::load_audio_file()` reads WAV at its stored rate. For every non-WAV file it invokes FFmpeg with `-ar 48000`, regardless of the file's native rate. The Studio's `blind_detect_callback()` then calls `prepare_audio(... target_sample_rate=44100, duration_seconds=12)` for SilentCipher. `prepare_audio()` uses `scipy.signal.resample_poly` when the input rate is not already 44.1 kHz. SilentCipher's adapter receives 44.1 kHz and therefore performs no additional model-side rate conversion.

For a 44.1 kHz compressed input this means:

`44.1 kHz container → FFmpeg decode/resample to 48 kHz → scipy resample to 44.1 kHz`

This is a redundant intermediate rate conversion. For native 48 kHz inputs the Studio path performs only the required 48→44.1 kHz conversion. WAV input at 44.1 kHz bypasses both conversions. P9's saved external-file record confirms its 44.1 kHz M4A was decoded by the Studio reader at 48 kHz and prepared to 44.1 kHz; that one-file check was `IDENTIFIED` at confidence `0.706349`.

### Paired runtime path check

The exact P9 M4A (SHA-256 recorded in P9 as `bba73cef66169dd8355a002ed8957fb92ea4658d3e677373835351f58ee77815`) was not retained, so it could not be replayed. To isolate the path behavior, the same newly created AAC-LC/M4A file was decoded two ways:

- **A — native-rate route:** FFmpeg decoded the 44.1 kHz M4A without `-ar`; fixed backend preparation then fit it to 12 seconds. No sample-rate conversion was needed.
- **B — current Studio route:** `load_audio_file()` decoded to 48 kHz, then `prepare_audio()` converted 48→44.1 kHz and fit 12 seconds.

Both detectors received only their respective decoded/prepared samples and the frozen detector. The expected message and the source waveform were not passed to detection. Ground truth was used only after inference to score the positive row.

| Input | A native decode | B Studio decode | A result | B result | A/B waveform difference SNR | A/B LSD | Detect time A / B |
|---|---|---|---|---|---:|---:|---:|
| Watermarked M4A, SHA-256 `eef6841cc7e7dab119c523f2b0d11b9936937b8f3ce194ea4f3f1852a01d1996` | 44.1 kHz, 529,408 decoded samples, fit to 529,200; 0 rate conversions | Container 44.1 kHz; FFmpeg output 48 kHz; fit/resample to 44.1 kHz / 529,200 | `IDENTIFIED`, `7B91D4E260`, 0.928571 | `IDENTIFIED`, same candidate and confidence | 63.262 dB | 1.416 dB | 7.90 / 7.63 s |
| Unwatermarked M4A, SHA-256 `7808a698e6e3574d197e24ee2a1167337299ea60a9b6e354b08610c967e96447` | 44.1 kHz, 529,408 decoded samples, fit to 529,200; 0 rate conversions | Container 44.1 kHz; FFmpeg output 48 kHz; fit/resample to 44.1 kHz / 529,200 | `UNKNOWN`, candidate `26AA68AAA6`, 0.424603 | `UNKNOWN`, same candidate, 0.420635 | 63.281 dB | 1.424 dB | 7.60 / 7.21 s |

The 208 excess decoded samples were the AAC frame tail beyond the fixed 12-second model input. Both paths fit to the backend's fixed 12-second input without using a reference waveform, original source length, expected message, or embed-session metadata. No leading samples were discarded.

The paths produce measurable waveform/spectral differences, but on this one positive and one negative neither candidate nor presence state changed. The positive was accepted by both; the negative remained below threshold and was rejected by both. Detection-time differences are one-run observations and are not a throughput comparison. The diagnostic input came from an existing official example asset and was not an independent source-disjoint performance sample.

**Conclusion:** unnecessary intermediate resampling exists, but this paired check did not show an acceptance-state impact. Because the exact P9 file was unavailable and the check was small, a general no-impact claim is not justified. Per the P10 stop rule, the generic Studio path was left unchanged; do not interpret this as proof that double resampling is harmless for every input.

## 3. Historical score and threshold review

The frozen threshold is `0.6805555373430252`, selected in P1 as the midpoint between P1 development-positive minimum confidence `0.944444` and development-negative maximum candidate confidence `0.416667`. Confidence is frame-consistency, not a calibrated probability.

| Historical phase | Positive rows / raw exact | Frozen-threshold correct accepts | Negative candidate confidence maximum | Frozen-threshold negative accepts |
|---|---:|---:|---:|---:|
| P1 SilentCipher subset | 48 / 46 | 46 | 0.416667 | 0/24 |
| P3 | 48 / 44 | 44 | 0.392857 | 0/24 |
| P6 SilentCipher | 36 / 24 | 24 | 0.396825 | 0/24 |
| P8 | 36 / 24 | 23 | 0.448413 | 0/36 |
| P9 | 72 / 72 | 71 | 0.416667 (clean); 0.408730 (MP3); 0.400794 (M4A) | 0/72 |

Rows and channels are repeated measures. P6 and P8 overlap by design; their counts must not be summed as independent trials. The historical negatives also reuse sources across channels/stages and cannot support a formal false-accept rate. P2/P5/P7 diagnostic evidence is discussed in their frozen reports; it was not treated as an additional independent validation set.

Two thresholds were compared as limited historical diagnostics, without fitting any model:

- **0.65 candidate:** across the above historical records it would add one correct acceptance, P9 `music_commons_01` M2 at `0.674603`; it still rejects P8 `environment_04` at `0.638889`. No historical negative or wrong-message candidate in these parsed records crosses 0.65. This is not independent validation and is not installed.
- **0.60 comparator:** it would admit the two low-confidence exact examples, but also accepts wrong candidates observed on `speech_02` MP3 at `0.646825` and `environment_03` AAC-ADTS at `0.623016`. The latter appears in P6/P8 as a repeated evaluation of the same source/condition. The historical negative rows still show no acceptance at 0.60, but the wrong-message cases demonstrate a distinct risk that a negative-only comparison would miss.

Thus the freeze threshold is conservative for two exact low-confidence messages, but the available data do not support a safe replacement. A lower threshold of 0.60 is rejected as a candidate because it turns observed wrong payloads into accepted detections. The 0.65 candidate would need a genuinely new, frozen source-level validation set before any integration decision.

## 4. Independent calibration status

No new threshold was selected from P1–P9 and then evaluated on those same records as if they were a holdout. No new independent positive or negative recording set was acquired in this run. The required source-independent validation therefore has no measured P10 metrics:

| Metric | P10 independent result |
|---|---|
| Raw exact recovery | Not run |
| Correct accepted recovery | Not run |
| False rejection | Not run |
| Wrong-message acceptance | Not run |
| Unwatermarked false acceptance | Not run |
| `UNKNOWN` vs `DECODE_ERROR` | Audited from P9 records/code; no new source run |
| CPU detection time | Measured only in the paired file-path diagnostic above |

The P9 single external M4A check remains useful evidence that the normal upload boundary can work without original audio, but it is not a new independent test and does not establish broad external-file reliability.

## 5. P9 `DECODE_ERROR` classification

P9 has five negative condition records marked `DECODE_ERROR` with wrapper category `INVALID_DECODER_RESULT` and no `exception_type`. These were not recorded as upload/read/preprocessing exceptions. The adapter's normalizer can set this category when the official output cannot be converted into the expected five-byte candidate structure. P9 did not persist the raw `decode_wav()` return object or the exact validation sub-error, and the source files are gone; consequently the specific five cases cannot now be distinguished between malformed candidate output and upstream parse failure.

The official SilentCipher `decode_wav()` wraps per-channel inference and terminator/message parsing in a bare exception handler. It returns `status=False`, empty `messages`, and `"Could not find message"` for both ordinary no-terminator cases and any exception in that block. The adapter already classifies a normal empty-message result as `UNKNOWN` with `NO_MESSAGE`. The five `INVALID_DECODER_RESULT` rows are a separate output-normalization failure category; the saved evidence is insufficient to relabel them as expected no-message outcomes. They remain `DECODE_ERROR` until raw-result capture and reproduction can establish otherwise. Actual file I/O and preprocessing failures must continue to remain `DECODE_ERROR`.

No adapter change was made. That avoids concealing malformed decoder results or conflating them with valid `UNKNOWN` results based on incomplete P9 logs.

## 6. Answers and decision

1. **Does Studio perform unnecessary resampling?** Yes, for non-WAV 44.1 kHz files: FFmpeg converts to 48 kHz, then Studio converts back to 44.1 kHz. The P9 external M4A record confirms this path.
2. **Did it affect detection in the paired check?** It changed waveform/spectral values, but not the positive/negative presence outcome; the positive candidate/confidence were identical and negative candidate confidence changed by about 0.004. Exact P9 M4A replay and broader conclusions remain unavailable.
3. **Is the current threshold too conservative?** It does reject two known exact messages below threshold. However, the historical candidate at 0.60 would accept observed wrong messages. The evidence does not establish that a lower policy is safer overall.
4. **Does a new strategy have source-independent performance benefit?** Not established; the network/data availability gate prevented independent holdout acquisition. Historical comparisons are development evidence only.
5. **Which failures are decoding vs presence?** P8/P9 low-confidence exact messages are presence false rejections, not message decoding failures. P9 five `INVALID_DECODER_RESULT` cases are wrapper output-validation errors with missing raw decoder objects; they are not proven file-read errors or ordinary no-message results. Empty official messages already map to `UNKNOWN`.
6. **Should the detector change now?** No. Keep the P1 threshold and adapter behavior; keep 0.65 as an unintegrated candidate for a later independent test. Do not deploy 0.60.

`V4_P10_DECISION = INCONCLUSIVE`

The provisional baseline is retained operationally. The unresolved bottleneck is presence-score calibration and incomplete raw diagnostics for malformed decoder outputs, rather than a demonstrated file-decoder failure. The redundant 44.1→48→44.1 conversion is a code-path inefficiency; this check did not prove it changes the detection decision, so it was not patched in this stage.
