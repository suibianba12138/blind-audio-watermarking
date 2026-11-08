# V4-P11 Fast Blind Temporal Synchronization Feasibility Report

**Decision: `V4_P11_DECISION = NOT_PROMISING`**\
Scope: feasibility of low-cost synchronization from one official SilentCipher decoder forward, not a claim that all synchronization methods are impossible.

## 1. Scope and frozen settings

- Official Sony SilentCipher 44.1 kHz checkpoint `73999_iteration`; checkpoint and official source were not modified.
- `message_sdr=47 dB`, official hard decoder, and frozen presence threshold `0.6805555373430252`.
- Fixed 40-bit message `[18, 52, 86, 120, 154]` for the three positive excerpts. Detection did not receive that message; it was used only after detection to score exact recovery.
- Three positive excerpts: P1 `music_03`, P1 `speech_03`, P1 `environment_01`. The prepared excerpt SHA256 values are in `experiments/v4_p11/SYNC_PROBE.json`. Music `music_03` originated from a native 44.1 kHz CC0 FMA recording. The speech and environment source manifests identify the recordings as 16 kHz before preparation/resampling to 44.1 kHz; they are not native high-rate validation.
- Three unwatermarked clean controls used distinct prior P1/P3 music, speech, and environment recording excerpts. They are source-distinct from one another; this is a small diagnostic set, not an independent false-accept-rate study.
- Each positive was embedded once. All four edited conditions were generated from that same marked waveform. Each excerpt was 12 s / 529,200 samples at 44.1 kHz after edits.

## 2. Official decoder and time scales

The official 44.1 kHz configuration uses `N_FFT=4096`, `HOP_LENGTH=2048`, and `message_len=21`. The hop is 46.44 ms; the 4096-point analysis window spans 92.88 ms. The STFT implementation pads the signal at the right to a window-length multiple and uses `torch.stft` defaults, including centered framing. There are 21 repeated 2-bit message symbols per message period: 20 payload symbols followed by a zero terminator. The official decoder takes hard argmax symbols for each time frame, truncates to complete 21-frame blocks, votes per slot, and estimates confidence as the fraction of frame predictions matching each slot's modal value. It locates the first modal zero as the terminator, rotates the sequence, subtracts one from payload symbols, then packs them into five bytes.

These are different failure mechanisms:

- **Sample offset:** moving the waveform by a fraction of a hop changes the samples under each STFT window.
- **STFT-grid offset:** the same signal can be analyzed with a different window/frame origin. The official phase search tries to find such an origin.
- **21-frame symbol phase:** grouping frame predictions from a different starting frame rotates their position within the repeated 21-symbol pattern. This can be examined after one forward pass, but only if the frame predictions still contain the message.
- **Content loss:** cropping removes watermark-bearing frames. Padding with silence does not restore them. A 9 s crop padded to 12 s has less marked content than the original.

The requested 0.25 s prepend case is **not a pure offset**: after prepending, truncating to 12 s drops the last 0.25 s of marked content. Removing 0.5 s and padding drops the first 0.5 s and adds silence. The 9 s condition takes source seconds 1–10, dropping 1 s at the start and 2 s at the end, then adds 3 s of silence. No tested condition isolates a time shift while retaining all original samples.

The official `phase_shift_decoding` searches waveform offsets from 0 to 2047 samples in steps of 10 (about 205 STFT/frame origins). For each offset it recomputes the STFT and message decoder, then chooses the offset with the highest modal consistency; that score is not message correctness or a calibrated presence score. P1's 0.5 s crop search used 90.152 s and still returned no message before the hard budget expired.

## 3. Minimal perturbation results

Raw confidence is the official decoder's frame-to-modal consistency. “Accepted” applies the frozen threshold and requires a usable five-byte candidate; official `status=True` alone is not an acceptance. Terminator positions are zero-based slots in the official modal 21-symbol sequence.

| Source / condition | Official output | Confidence | Terminator | Exact | Correct accepted | Wrong accepted |
|---|---|---:|---:|---:|---:|---:|
| music_03 clean | correct message | 0.8690 | 20 | yes | yes | no |
| music_03 prepend 0.25 s, truncate to 12 s | wrong candidate | 0.4563 | 11 | no | no | no |
| music_03 remove 0.5 s, pad 0.5 s | no message; modal terminator absent | — | — | no | no | no |
| music_03 9 s segment, pad 3 s | no message; modal terminator absent | — | — | no | no | no |
| speech_03 clean | correct message | 0.9921 | 20 | yes | yes | no |
| speech_03 prepend 0.25 s, truncate to 12 s | correct message | 0.7063 | 4 | yes | yes | no |
| speech_03 remove 0.5 s, pad 0.5 s | correct message | 0.9008 | 9 | yes | yes | no |
| speech_03 9 s segment, pad 3 s | no message; modal terminator absent | — | — | no | no | no |
| environment_01 clean | correct message | 0.8651 | 20 | yes | yes | no |
| environment_01 prepend 0.25 s, truncate to 12 s | no valid payload after terminator | 0.337 (modal consistency) | 5 | no | no | no |
| environment_01 remove 0.5 s, pad 0.5 s | invalid byte candidate | 0.3929 | 9 | no | no | no |
| environment_01 9 s segment, pad 3 s | no message; modal terminator absent | — | — | no | no | no |

Per condition, clean exact and accepted recovery was 3/3; prepend-plus-tail-truncation was 1/3; remove-and-pad was 1/3; and 9 s segment-plus-padding was 0/3. There were no accepted wrong messages. The environment crop produced an invalid candidate with negative byte values after the official parser's symbol subtraction; it is not a valid decoded message and would be rejected by the adapter's message validation.

The three unwatermarked controls produced no accepted result (0/3). One returned a random five-byte candidate with `status=True` and confidence 0.3730; the other two failed terminator/message parsing. This confirms why official status alone is not a presence decision. The small negative set cannot establish a false-accept rate.

### P1 crop evidence

P1's retained `CROP_CHECK.json` records `speech_03` with the first 0.5 s removed and an 11.5 s input: ordinary decode recovered the correct bytes at confidence 0.670996, just below the frozen threshold, so it was rejected as `UNKNOWN`. The phase-shift call exhausted its 90 s budget without a message. P1's 9 s segment from t=1 s failed ordinary decoding. P11's remove-and-pad waveform is not exactly the P1 11.5 s protocol, so these are related evidence, not a byte-identical regression.

## 4. One-forward synchronization diagnostics

A forward hook captured the official message decoder's raw frame scores during the same ordinary `decode_wav()` call. The experiment saved the full per-frame argmax sequence and five class scores in `experiments/v4_p11/SYNC_PROBE.json`.

A bounded diagnostic tested frame offsets 0 through 20 only. For each offset it discarded leading frame predictions, grouped complete 21-frame blocks, and used modal consistency to rank legal hard candidates (ties choose the smaller offset). This is a post-processing shift of the **frame grouping only**; it does not correct sample-level or STFT-grid misalignment. A separate soft diagnostic averaged raw class scores within aligned 21-frame blocks and required a zero terminator. It was not treated as a presence detector because its score has no calibration.

- The hard frame-boundary procedure preserved the three clean messages and the two speech edit successes, but did not add a correct accepted recovery over ordinary decoding.
- It did not recover any of the failed music or environment edits or any 9 s segment.
- No unwatermarked control crossed the frozen confidence threshold or became accepted.
- Soft aggregation occasionally produced a byte-shaped candidate for a failed 9 s segment, but these candidates were incorrect. This is not recovery and demonstrates the multiple-candidate false-alarm concern.
- The 21-candidate CPU post-processing sweep took 0.708 ms mean (0.73 ms median, 1.102 ms max over 75 replays of the saved outputs). This is negligible next to the ordinary neural forward pass, but it did not improve detection.

## 5. Resource use and reproducibility

With the model already loaded, 15 ordinary decode calls (12 positive conditions and 3 negatives) took 5.834–5.996 s each, mean 5.880 s, on CPU with four PyTorch threads. Process peak RSS was 1,447,940 KiB (about 1.38 GiB). P11 did not separately time a cold model load. The official dense phase-shift result above is from the frozen P1 record, not a rerun.

The full frame predictions, per-frame class scores, source excerpt hashes, candidate lists, confidence values, and CPU timings are saved in `experiments/v4_p11/SYNC_PROBE.json`. The probe did not write into P0–P10 records or alter application code.

## 6. Feasibility judgment

1. **Main reason for crop failure:** mixed. A small offset/crop can change model frame predictions and terminator position even when most marked content remains; longer cropping and padding also remove a substantial part of the repeated watermark evidence. The 9 s failures show insufficient usable frame evidence in these examples. Three sources are too few to assign a universal primary cause.
2. **Alignment versus information loss:** both are plausible in the tested edits. The experiment did not isolate a pure sample shift. The 9 s case clearly includes lost watermarked content; no frame-only regrouping recovered it. The clean-to-edited degradations in music and environment cannot be attributed solely to missing the terminator position because the underlying per-frame predictions also became inconsistent.
3. **Are single-forward symbols enough for fast synchronization?** They are enough to cheaply test a bounded frame-group phase, but not enough here to recover failed messages. A high-consistency periodic pattern existed in clean audio; under failing edits, the needed symbol/terminator evidence was often absent or corrupted.
4. **Concrete algorithm worth implementing?** No implementation is justified yet. A fixed 21-way frame-boundary diagnostic is concrete and extremely cheap, but had no incremental accepted recovery. The soft-score candidate path generated unvalidated wrong candidates and needs a new calibrated policy before it could be safely used.
5. **CPU cost:** single-forward post-processing is negligible (~0.7 ms), but ordinary detection itself is about 5.9 s per 12 s clip and peak memory was about 1.38 GiB. The official dense waveform search is costly: P1 spent 90 s and did not finish. A low-cost candidate can meet the runtime goal but currently fails the utility and safety gates.
6. **Should synchronization be the next V4 algorithm improvement?** Not on this evidence. Preserve the official decoder and presence policy. Do not integrate the exploratory candidate search. If synchronization is revisited later, first collect source-disjoint cases with a true sample-shift-only condition that preserves all watermarked samples, and compare ordinary decoding against a predeclared bounded search while keeping negative controls.

This is a small engineering feasibility probe, not a benchmark, false-accept-rate estimate, or claim about all source types and edits.
