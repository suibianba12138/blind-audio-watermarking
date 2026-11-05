# V4 Adaptive Watermarking Report

**Decision: `ADAPTIVE_WATERMARKING_DECISION = INCONCLUSIVE`**

## Scope and decision summary

This bounded experiment evaluated a sender-side adaptive embedding prototype around the official frozen Sony SilentCipher 44.1 kHz / 40-bit model. It tried only `message_sdr = 47, 45, 43 dB`, in that order. The frozen presence threshold (`0.6805555373430252`, still provisional) and official hard decoder were unchanged. No model weights, V3 code, Studio backend, GUI, or deployment service were modified.

The default 47 dB candidate passed all three channels on all 12 new message trials from six source-disjoint recordings. The adaptive method therefore stopped at 47 dB on every new trial and tied the fixed baseline. On historical development cases it rescued one speech message at 43 dB, but it did not rescue the historical music case, and another speech case could not be selected because its LSD exceeded the predeclared quality limit. The new-source evidence does not demonstrate a generalization gain. Keep the existing fixed 47 dB Studio behavior; this prototype is not integrated.

## Frozen protocol and data

The protocol is recorded in [`configs/v4_adaptive_source_protocol.json`](../../../configs/v4_adaptive_source_protocol.json), with SHA256 `a9e912cb72cc6f2e1ccbe67a4695f74f55c2b752abcc962f9a2da0b26ec6c52c`. Its source list includes source hashes, licenses, source sample rates, crop offsets and fixed messages. New data comprised six distinct licensed MUSAN recordings: two music, two speech and two environment recordings, each carrying two fixed 40-bit messages. The two messages from a recording are repeated measurements, not independent sources. Historical development records were the P1 `music_03` case and P3 `speech_02` with two messages.

The new music recordings were natively 16 kHz and resampled once to the model rate; no new native 44.1/48 kHz music was available locally. Thus this experiment does not validate performance on new native high-rate music. All audio presented to the model was mono, 44.1 kHz and 12 seconds. Each positive trial used one embedded audio for Clean WAV, FFmpeg MP3 CBR 128 kbps, and AAC-LC 128 kbps in M4A. AAC used the P8 metadata-aware path, including removal only of known trailing padding. For each of six new source recordings, unwatermarked Clean, MP3 and M4A negatives were also independently detected.

The fixed quality gates were SNR ≥ 40 dB, LSD ≤ 5 dB and no new clipping. These are engineering screening bounds, not perceptual guarantees. SNR/LSD compared aligned, same-length original and exported PCM16 watermark audio. The exact evaluation output is [`experiments/v4_adaptive/RESULTS.json`](../../../experiments/v4_adaptive/RESULTS.json); it contains no source audio or local absolute paths.

## Method and isolation

The isolated implementation is [`app/adaptive_watermarking.py`](../../../experiments/v4_adaptive/prototype/adaptive_watermarking.py). It embeds a candidate, sends each channel output to the ordinary blind detector, and only then performs sender-side exact-message comparison. The detector interface receives only received samples, sample rate, frozen model and PresencePolicy; it has no expected message, reference audio, embedding session or candidate-selection history. A candidate qualifies only if all three channel outputs are `IDENTIFIED` with an exact message match and the quality gates pass. If 47 dB qualifies, lower strengths are not run. Otherwise the two predeclared alternatives are tested, and the best quality-qualified candidate is selected. If none qualifies, the method returns no selected watermarked output.

`app/v4_audio_processing.process_channel()` supplied the real MP3/M4A paths; the official model was loaded once, CPU inference was limited to four threads, and the evaluator used temporary directories. The independent tests for the adaptive helper passed 6/6 using Python `unittest`.

## Results

### New source-disjoint evaluation

Every one of the 12 trials selected 47 dB on its first attempt. Per recording, both fixed messages passed Clean, MP3 and AAC/M4A with the frozen presence policy:

| Source | Type | Fixed 47 dB and adaptive selection |
|---|---|---|
| `music_adapt_01` | Music | 2/2 messages passed all three channels |
| `music_adapt_02` | Music | 2/2 passed |
| `speech_adapt_01` | Speech | 2/2 passed |
| `speech_adapt_02` | Speech | 2/2 passed |
| `environment_adapt_01` | Environment | 2/2 passed |
| `environment_adapt_02` | Environment | 2/2 passed |

By channel, fixed and adaptive both achieved 12/12 correct accepted messages for Clean, MP3 and AAC/M4A. That is 6/6 recordings with both messages passing in each channel. Because no new trial needed fallback, this result shows the selector did not harm the baseline on this small set; it does not show that adaptivity improved it.

### Historical development cases

| Source/message | Fixed 47 dB | Adaptive result | Interpretation |
|---|---|---|---|
| P1 `music_03`, `123456789A` | Clean accepted; MP3 UNKNOWN; AAC decoded a wrong candidate and was UNKNOWN | Tried 47/45/43; no candidate passed all channels | Even 43 dB recovered MP3 but AAC had no valid candidate. Remains unresolved. |
| P3 `speech_02`, `D3916B24E8` | Clean UNKNOWN; MP3 wrong candidate UNKNOWN; AAC exact candidate below threshold UNKNOWN | At 43 dB all channels decoded and were identified, but LSD was 5.238 dB, above the frozen 5 dB gate | No selected output; stronger embedding failed the quality gate. |
| P3 `speech_02`, `2C6E94DB17` | All three channels UNKNOWN | Selected 43 dB; all three were exact and IDENTIFIED | One historical message recovered, at a measurable quality cost. |

Across all 15 positive message trials (12 new plus 3 historical), fixed 47 dB produced Clean 13/15 correct accepted, MP3 12/15, and AAC/M4A 12/15 correct accepted (13/15 raw exact on AAC, with one exact candidate below threshold). The adaptive output was selected for 13/15: the 12 new cases plus the one historical speech message. Those 13 selected outputs passed 39/39 channel checks. Counting both unselected historical cases as failures, adaptive reached 13/15 per channel versus fixed 47 dB’s 13/15 Clean, 12/15 MP3 and 12/15 AAC correct acceptance. Its apparent +1/15 strict all-channel gain is entirely one historical message, not an independent-source gain.

No wrong-message candidate was accepted in the positive trials. Negative acceptance was 0/18: all six distinct unwatermarked sources returned UNKNOWN in Clean, MP3 and AAC/M4A. Six negative detections produced legal candidate scores below the frozen threshold (range 0.3611–0.3849); other negative cases had no candidate. This small negative set is not a formal false-acceptance estimate.

## Audio quality and compute

Candidate-level quality was consistent with the expected trade-off. For the 15 attempted 47 dB embeddings, mean SNR was 48.974 dB (range 48.489–50.426), mean LSD 2.476 dB (range 0.591–4.417), with mean embedding time 3.370 s. The three historical 45 dB embeddings averaged 47.935 dB SNR and 3.352 dB LSD; the three 43 dB embeddings averaged 46.054 dB SNR and 3.699 dB LSD. No tested candidate introduced clipping. One 43 dB historical speech candidate exceeded the LSD gate at 5.238 dB. These small, selected candidate counts are descriptive; lower `message_sdr` visibly reduced SNR and can worsen spectral distortion.

The first candidate, including embedding, channel work and three detector calls, took roughly 21–24 seconds on this CPU. A case requiring all three strengths took roughly 63 seconds. The complete bounded run took 567.70 seconds; model load was 0.037 seconds after the runtime environment was initialized. Peak process RSS was 1,593,140 KiB (about 1.52 GiB), with four CPU threads. The 12 new cases incurred no fallback cost because 47 dB passed immediately.

## Risks and limitations

- Only six new independent recordings were available; all music was 16 kHz before one resampling step, so native high-rate music remains untested.
- Adaptive improvement is supported by one historical message only; that is development evidence, not a generalization result.
- The old music failure remains unresolved even at 43 dB, and one speech rescue was rejected by the audio-quality gate.
- The provisional presence threshold was deliberately frozen. Results do not calibrate or validate a population-level false alarm rate.
- SNR/LSD are not listening tests; no claim of inaudibility is made.
- Search costs grow with the number of attempted levels, up to about three times the default candidate cost.
- The prototype is a send-side verifier. Its success does not permit the blind detector to use the sender’s known message or session state.

## Recommendation

`ADAPTIVE_WATERMARKING_DECISION = INCONCLUSIVE`

Adaptive embedding can repair one historical speech message without changing the blind detector, but it did not improve any of the new source-disjoint trials because the 47 dB baseline already passed all of them. It did not solve the historical music/AAC failure, and more aggressive embedding can violate the LSD quality floor. Keep 47 dB as the formal default and retain this prototype as an isolated offline experiment only. Do not replace the Studio embedding path based on these data. A larger, truly independent set with native 44.1/48 kHz music would be needed to test whether per-audio fallback improves reliability beyond the baseline.
