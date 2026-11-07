# V4-P7 AAC Failure Diagnosis Report

**Date:** 2026-11-05\
**Decision:** `V4_P7_DECISION = CHANNEL_PIPELINE_ISSUE`\
**Scope:** Frozen P6 sources and models; three-source SilentCipher channel diagnosis plus one AudioSeal container recheck. No model, weight, threshold, GUI, V3, or P0–P6 result was changed.

## Summary

P6’s `0/12` SilentCipher AAC result does not isolate AAC compression robustness: its test used AAC-LC in an ADTS stream, whose decoded PCM in this FFmpeg path retained one leading AAC frame of priming. On all three frozen P7 examples, decoded ADTS contained exactly 1,024 extra samples, and bounded reference cross-correlation placed the decoder waveform 1,024 samples (23.220 ms at 44.1 kHz) late. The P6-style “take the first 12 seconds” operation therefore fed priming samples and dropped the final 1,024 real samples.

The same marked audio encoded as AAC-LC in M4A carried a packet `skip_samples=1024` indication. FFmpeg applied it during decode: the returned waveform had no measured start offset and SilentCipher recovered the exact payload on all three examples. Applying the codec-frame compensation `discard first 1024 decoded samples, then pad/truncate to the original sample count` to the ADTS output also restored exact recovery on all three. Confidence after this fixed correction was 0.909, 0.925, and 0.996, all above the unchanged P1 provisional threshold `0.6805555373430252`.

This is strong evidence of a **channel-container priming/alignment defect in the P6-style ADTS decode path**, not evidence that AAC compression itself defeats SilentCipher. The small P7 sample does not establish general AAC robustness. AudioSeal’s one-source check also changed from an accepted wrong message under ADTS to exact recovery under M4A, consistent with the container-path finding; it is only a diagnostic recheck.

## Read-only P6 protocol audit

- P6 used FFmpeg 6.1.1, native AAC encoder, AAC-LC, nominal 128 kbps, mono, and the model’s required sample rate (44.1 kHz for SilentCipher; 16 kHz for AudioSeal).
- Its AAC path wrote a PCM16 WAV, encoded with `-c:a aac -b:a 128k -f adts`, then decoded with `-ac 1 -ar <model-rate> -c:a pcm_f32le -f wav`. The result was sliced to the original sample count and zero-padded if short.
- No extra resampling was requested when source and model sample rates matched. The input was quantized to PCM16 before encoding. No watermark was re-embedded per channel.
- ADTS has no container edit list carrying the leading AAC priming skip. The first packets reported PTS 0 and no skip-sample side data. FFprobe’s ADTS duration estimate was 12.43–12.96 s and did not match decoded PCM duration; this estimate is not a reliable sample-alignment instruction.
- M4A’s first packet had PTS `-1024` samples (`-0.023220 s`) and `Skip Samples` side data with `skip_samples=1024`. FFmpeg’s M4A decode yielded 529,408 samples versus the 529,200-sample input (208 tail samples extra), with no measurable leading shift. The P6-style 12-second slice retained the aligned audio.
- The first P7 attempt itself stopped before inference because the temporary diagnostic script looked for `.adts` while FFmpeg had written `.aac`. This was corrected and the full run completed; it was a script filename error, not a codec failure.

## Frozen inputs and method

The three inputs are the P6 manifest’s `music_03`, `speech_01`, and `environment_01` (one unique recording per class). Their P6 source SHA-256 values are retained in `experiments/v4_p7/RESULTS.json`; source IDs, fixed P6 crop starts, the P6 manifest hash, and the fixed SilentCipher message are recorded there. These are existing 16 kHz MUSAN recordings resampled to SilentCipher’s 44.1 kHz input; the music example is not native high-rate music. No new source was selected after seeing P7 outcomes.

For each source, one SilentCipher payload (`D3916B24E8`, 40 bit) was embedded once at the official default 47 dB. That same marked waveform was used for WAV, FLAC, MP3, AAC-ADTS, and AAC-M4A conditions. MP3 was `libmp3lame` CBR 128 kbps. Both AAC containers used FFmpeg native AAC-LC at nominal 128 kbps. SilentCipher’s P1 provisional threshold stayed fixed; no phase-shift search was enabled.

Waveform alignment diagnostics used normalized cross-correlation between the known marked reference and the decoded signal, bounded to ±0.5 seconds. This is an **oracle/reference-assisted diagnostic only**, not blind detection. The fixed 1,024-sample AAC-LC frame compensation was then evaluated separately; it was chosen from the observed fixed sample-count excess and AAC-LC frame timing, not from message recovery or a search over possible offsets. After the first paired run, its temporary PCM files had been automatically removed, so the fixed-compensation subtest regenerated one marked signal per source using the same frozen source, message, checkpoint, and default parameters. Within that subtest, the exact same regenerated marked signal fed the raw and fixed-compensation ADTS paths; no separate embedding was made for each codec. The raw subtest candidates/confidences matched the first paired run. This repeated subtest is reported separately and does not replace the original paired five-channel records.

## Paired signal and detection results

| Source | WAV decode | FLAC exact | MP3 exact | ADTS raw exact / confidence | M4A exact / confidence | ADTS fixed 1024 exact / confidence |
|---|---:|---:|---:|---|---|---|
| music_03 | 529,200 samples; exact | Yes | Yes | No; `D391AB54E8`, 0.548, rejected | Yes; `D3916B24E8`, 0.909 | Yes; `D3916B24E8`, 0.909 |
| speech_01 | 529,200 samples; exact | Yes | Yes | No; `816FA7E0D4`, 0.591, rejected | Yes; `D3916B24E8`, 0.925 | Yes; `D3916B24E8`, 0.925 |
| environment_01 | 529,200 samples; exact | Yes | Yes | No candidate / status false | Yes; `D3916B24E8`, 0.996 | Yes; `D3916B24E8`, 0.996 |

“Exact” means the 40-bit payload matched; accepted results additionally satisfy the unchanged status, valid-payload, and provisional confidence policy. No wrong payload was accepted. The fixed-compensation output is a corrected channel-path diagnostic, not the unmodified blind-detector result.

| Source | ADTS decoded samples | ADTS reference lag | M4A decoded samples | M4A reference lag | M4A aligned SNR vs marked | M4A LSD* |
|---|---:|---:|---:|---:|---:|---:|
| music_03 | 530,432 | +1,024 (23.220 ms) | 529,408 | 0 | 32.13 dB | 27.93 dB |
| speech_01 | 530,432 | +1,024 (23.220 ms) | 529,408 | 0 | 31.90 dB | 34.57 dB |
| environment_01 | 530,432 | +1,024 (23.220 ms) | 529,408 | 0 | 34.58 dB | 26.16 dB |

Positive lag means decoded audio starts later relative to the marked reference. ADTS aligned SNR after the fixed 1,024-sample correction was 32.13, 31.90, and 34.58 dB, respectively. The unaligned SNR was about -2.8 to -3.6 dB because it compared the priming-shifted signal sample-by-sample; it must not be interpreted as codec quality. The marked environment signal peaked slightly above full scale before the PCM16 write; decoded AAC also had peaks above 1. This is a level/codec overshoot observation, not a demonstrated decoder clipping event.

`*LSD` is the script’s regularized STFT log-magnitude distance (`n_fft=4096`, hop 2048, Hann, global reference-derived floor). This floor makes the reported value sensitive to low-energy bins and PCM quantization, especially for lossless FLAC; it is retained as a consistent diagnostic and not treated as a perceptual quality score. The detailed STFT inputs, probe fields, timing, peaks, RMS, clipping flags, and per-condition detections are in the JSON evidence file.

## Frame prediction and message reconstruction

The independent diagnostic adapter recorded the official per-frame argmax symbol sequence and parser result for raw ADTS and fixed-compensated ADTS. In every case, raw ADTS failed the frozen terminator/payload reconstruction or produced a different payload. After the fixed 1,024-sample crop, each sequence reconstructed `D3916B24E8` with the terminator at symbol index 20 (zero-based), which is the expected end position. Full symbol sequences and decode records are preserved in `experiments/v4_p7/ADTS_FIXED_DIAGNOSTIC.json`.

The M4A outputs matched the fixed-compensated ADTS outcome exactly on these three samples. WAV, FLAC, and MP3 were exact on all three, consistent with P6’s positive clean/MP3 behavior. This comparison argues against a model-forward numeric error: the same frozen model and marked signal recover once the ADTS priming samples are removed.

### Limited AudioSeal recheck

For frozen `music_03`, AudioSeal used its P6 message `A55A`, 16 kHz input, and unchanged official detector. ADTS produced candidate `C512`, presence score 0.962 (accepted, wrong payload); M4A produced `A55A`, score 1.000 (accepted, exact). One recording is not a performance estimate, but the parallel container result supports an ADTS path issue rather than SilentCipher-specific decoder behavior.

## Resource and execution observations

- SilentCipher official model load: 0.040 s; process peak RSS: 1,612,740 KiB; CPU threads: 4.
- Embedding time for the three sources: 3.33–3.45 s each.
- SilentCipher detection time: approximately 5.68–6.15 s per decode; the fixed-compensation diagnostic includes another full decode and raw-score extraction.
- AudioSeal limited detector calls: 0.165–0.271 s; model loading and embedding are outside those per-call times.
- FFmpeg: 6.1.1; no GPU, training, model changes, or additional data were used.

These are local engineering timings, not throughput guarantees.

## Decision and engineering implication

`V4_P7_DECISION = CHANNEL_PIPELINE_ISSUE`

A reproducible ADTS priming/alignment discrepancy was identified, and correcting the fixed delay restored valid messages on all three selected SilentCipher sources. M4A’s packet skip metadata already enabled the FFmpeg decoder to handle the same delay. This diagnosis does **not** prove broad AAC robustness or establish general error rates; the P7 set is only three frozen P6 sources and all source music is 16 kHz before resampling.

The audio-channel utility should either preserve AAC priming metadata through a container that supports it (as M4A did here) or apply a codec/container-aware deterministic trim before blind detection. Do not silently apply a reference-derived cross-correlation lag in the product detector: it requires the original marked audio. If ADTS must remain supported, encode/decode metadata and the fixed skip rule should be explicit and separately regression-checked. No such code change was made in P7.

**Answer:** The P6 ADTS failures are primarily attributable to a reproducible channel timing/priming issue. On this bounded check, there is no remaining AAC-induced SilentCipher message failure after fixed alignment; broader codec robustness remains unverified.

## Evidence and reproducibility

- `experiments/v4_p7/RESULTS.json`: per-source and per-channel ffprobe metadata, PCM stats, alignment, SNR/LSD, and raw/fixed-oracle detections.
- `experiments/v4_p7/ADTS_FIXED_DIAGNOSTIC.json`: fixed-rule compensation and official frame-symbol/parser records.
- `experiments/v4_p7/AUDIOSEAL_CONTAINER_RECHECK.json`: one-source AudioSeal ADTS/M4A comparison.

P0–P6 artifacts, V3, P4 Studio, checkpoints, and online services remain unchanged. No audio, model weights, absolute local paths, or credentials are included.
