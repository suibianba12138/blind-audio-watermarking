# Frozen Evidence Summary

All C2/C3 detectors use the corresponding unwatermarked original as a reference. These are reference-assisted, non-blind results. The rows below come from different protocols and must not be merged into one success rate.

## C2 Robust — 8 bits / 6 seconds

One-time Locked Test across 60 source recordings:

| Condition | Correctly accepted | Wrong message accepted | UNKNOWN | Negative false accepts |
|---|---:|---:|---:|---:|
| Clean readback | 60/60 | 0 | 0 | 0/180 |
| MP3 128 kbps | 59/60 | 1 | 0 | 0/120 |
| AAC-LC/M4A 128 kbps | 57/60 | 2 | 1 | 0/120 |

Combined negative decisions: 0/420. This zero observed count is not evidence that the population false-positive rate is zero. The locked float output study found rare samples above full scale; use the float master and do not claim a later PCM16 export policy inherits the Locked Test result.

## C2 Long-ID — one repeated 32-bit identity over 72 seconds

On 20 new mixed recordings, exact fused 32-bit identity recovery was 20/20 for Clean, MP3 and AAC. No false full ID was accepted among the 20 unwatermarked files in each channel. The 32-bit ID is sent as four byte messages every 24 seconds, repeated three times. Its independent information content is 32 bits, not 96 bits.

## C3-16 — 16 bits / 6 seconds

One-time independent evaluation over 120 source recordings (40 each from music, speech and environmental audio):

| Condition | Correctly accepted | Wrong message accepted | UNKNOWN | Negative false accepts |
|---|---:|---:|---:|---:|
| Clean readback | 120/120 | 0 | 0 | 0/360 |
| MP3 128 kbps | 120/120 | 0 | 0 | 0/360 |
| AAC-LC/M4A 128 kbps | 103/120 | 11 | 6 | 0/360 |

Combined negative decisions: 0/1,080. The AAC result is a capacity/robustness tradeoff and should not be represented as fully reliable.

## Selected single-track C3-16 showcase

The included *Where You Are Now* excerpt is a curated demonstration, not an independent performance estimate. It has 12 independently embedded 16-bit messages (192 bits over 72 seconds) and recovered all 12 blocks in Clean, full-file MP3 128 kbps and full-file AAC-LC/M4A 128 kbps. This selected result is shown separately from the 120-source evaluation above. The report records a 45 dB embedding SNR. Subjective inaudibility has not been established by a listening panel.

The same selected track also recovered the complete payload after MP3→AAC, −6 dB, +3 dB and 48→44.1→48 kHz processing. AAC→MP3 recovered 11/12 blocks; one wrong message was accepted, so the full 192-bit payload did not match.

## Separate Development robustness screen

An existing development-stage evaluation used 10 randomly mixed 72-second clips. These are mixed-source compositions, not 10 continuous songs, and are not Locked Test results.

| Condition | Full messages | Correct blocks | Wrong accepted | UNKNOWN | Negative false accepts |
|---|---:|---:|---:|---:|---:|
| Clean | 10/10 | 120/120 | 0 | 0 | 0/240 |
| MP3 128 kbps | 10/10 | 120/120 | 0 | 0 | 0/240 |
| AAC-LC/M4A 128 kbps | 2/10 | 104/120 | 8 | 8 | 1/240 |
| WAV→MP3→AAC | 6/10 | 111/120 | 8 | 1 | 1/240 |
| WAV→AAC→MP3 | 2/10 | 104/120 | 7 | 9 | 1/240 |
| −6 dB | 10/10 | 120/120 | 0 | 0 | 0/240 |
| +3 dB | 10/10 | 120/120 | 0 | 0 | 0/240 |
| 48→44.1→48 kHz | 10/10 | 120/120 | 0 | 0 | 0/240 |

The three codec-related negative false accepts correspond to the same unwatermarked block under three processing chains, not three independent source events. The included `media/robustness_evaluation/` chart and CSV are aggregate real results; no per-recording source IDs or full experiment matrix are included.

## Source identity and public packaging

- Frozen C2 source SHA-256: `330c3f9230523a76bf801d2b338072cbb00747225e3a9a44b3df95bf7bdb08ea`.
- Frozen C3 source SHA-256: `3b05b262921c84d4f595c1865978ba06587dac3b99f59ac5b195b71ea3495e3b`.
- The packaged C2/C3 modules preserve the DSP transforms and scoring code but require the caller to provide a key; their public hashes therefore differ from the frozen source hashes. Frozen keys are omitted. Frozen threshold values are retained.
- Smoke tests exercise the public-key package against included real music. They verify package operation, not the frozen locked/independent evaluation results.
