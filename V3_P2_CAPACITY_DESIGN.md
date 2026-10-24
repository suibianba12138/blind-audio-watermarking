# V3-P2 Capacity Expansion Design

## Purpose and boundaries

This document records a finite development-only capacity pilot. It does not
modify the frozen B1-QIM embedder, the P1 8-bit Soft-Code decoder, Course V2,
or any P1 result. The pilot uses only the frozen P1 `split=dev` sources. Each
content category is split deterministically into five calibration sources and
five held-out development pilot sources. The P1 formal `split=test` sources
are not used for codebook or threshold selection.

The physical channel remains 32 B1 positions with strength `1.60`, selector
`REAL_TOP32`, watermark seed `7`, 48 kHz/6 s processing, and real FFmpeg
`libmp3lame` 128 kbps. The blind detector receives only received audio and
public/keyed configuration. Expected payloads are scoring-only values.

## Candidate design

The candidates are deterministic Boolean evaluation codes over all 32 five-bit
position labels:

- `soft8_frozen`: the existing 256-word `[32, 8, 8]` code, used as the frozen
  reference; its threshold remains `0.7855073980199624`.
- `degree2_12`: constant term, five linear terms, and six pairwise quadratic
  terms; 4,096 codewords, 12 variable message bits, minimum Hamming distance 8.
- `degree2_16`: constant term, five linear terms, and all ten pairwise
  quadratic terms; 65,536 codewords, 16 variable message bits, minimum
  Hamming distance 8.

The 12/16-bit codebooks are generated directly from the formula and are not
optimized against the P1 formal test set. No BCH implementation, ECC stack, or
new physical embedding algorithm was introduced. Decoding is normalized signed
correlation over the finite codebook with deterministic lowest-index tie
breaking. Presence thresholding is separate from message decoding.

## Development pilot protocol

For every pilot source, two fixed message seeds (`101`, `202`) are encoded for
each capacity. The same source, message, QIM strength, selector, and FFmpeg
parameters are paired across methods. Conditions are marked/no-attack,
MP3-128k, clean no-watermark, clean-MP3 no-watermark, and wrong-key MP3.

For 12/16-bit methods, thresholds were calibrated only from calibration-role
positive and negative presence scores:

| Method | Threshold | Calibration positive detection | Calibration FPR |
|---|---:|---:|---:|
| soft8_frozen | 0.7855073980 (P1 frozen) | not refit | not refit |
| degree2_12 | 0.9038275297 | 56/60 | 0/60 |
| degree2_16 | 0.9278809958 | 55/60 | 0/60 |

These thresholds were not changed after viewing the held-out pilot results.

## Held-out development pilot results

The pilot role contains 15 source recordings and two messages per source, so
the positive MP3 denominator is 30 message trials per method. Source recordings
remain the primary unit; the two messages are paired observations.

| Method | Capacity | MP3 physical BER | MP3 logical BER | Raw exact (trial/source) | Accepted exact (trial/source both) | UNKNOWN | Clean FPR (source) | MP3 FPR (source) | Wrong-key accept (source) | Mean SNR (dB) | Mean LSD (dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| soft8_frozen | 8 | 0.045833 | 0.000000 | 30/30; 15/15 | 28/30; 14/15 | 2/30 | 0/15 | 0/15 | 0/15 | 56.1193 | 0.030236 |
| degree2_12 | 12 | 0.046875 | 0.000000 | 30/30; 15/15 | 27/30; 13/15 | 3/30 | 0/15 | 0/15 | 0/15 | 56.1656 | 0.030205 |
| degree2_16 | 16 | 0.050000 | 0.029167 | 28/30; 14/15 | 26/30; 12/15 | 4/30 | 0/15 | 0/15 | 0/15 | 56.0334 | 0.029654 |

All marked/no-attack positive trials had zero physical and logical BER and
100% accepted exact recovery in this pilot. Wrong-message acceptance was 0/30
for each method under MP3. The complete raw rows are in
`V3_P2_CAPACITY_PILOT.csv`; calibration and pilot role labels are retained in
each row.

## Fidelity and interpretation

The mean SNR range across the three methods was 0.1323 dB and the mean LSD
range was 0.00058 dB. This is a numerical matched-fidelity check within this
pilot, not a formal perceptual study. No introduced clipping was observed in
the 30 MP3 positive pilot rows for any method. The existing perceptual gate
remains `NOT_ESTABLISHED`.

The 12-bit candidate preserves zero logical BER in the finite pilot while
adding four message bits, but its accepted exact rate is one trial and one
source-level two-message outcome below the frozen 8-bit reference. That
supports a bounded independent-validation design, not a claim of improvement.
The 16-bit candidate has lower raw exact recovery, nonzero logical BER, and
more UNKNOWN decisions than the reference; it is not carried forward.

## Evidence status

`V3_P2_STATUS = DEVELOPMENT_PILOT_COMPLETE`.

This artifact establishes only a conditional 12-bit feasibility signal. It does
not establish independent generalization, population FPR, codec robustness
beyond MP3-128k, arbitrary 32-bit recovery, or perceptual transparency.
