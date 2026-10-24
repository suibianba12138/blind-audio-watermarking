# V3-P2-V Independent Validation

## Scope and status

This is the source-disjoint independent validation of the already frozen
8-bit and 12-bit Soft-Code candidates.  The B1 physical channel, REAL_TOP32
selector, embedding strength, codebooks, decoder, thresholds, and evaluation
protocol were not changed after the validation freeze.

`V3_P2_V_STATUS = COMPLETE_VALIDATION; 12BIT_NO_GO`

The validation supports retaining the 8-bit baseline.  It does not support
making 12-bit the default capacity.

## Frozen operating point

| Item | Frozen value |
|---|---|
| Base | `research/v3-p2@63d3166b1eeb2f0f7e99c8a9ad181934b824370e` |
| Manifest | `configs/v3_p2_v_independent_manifest.json` |
| Manifest SHA256 | `f5c0e6bd5ddf1e810358bcdfaa930e338203b2f66330540302186e6479679926` |
| Sources | 60: Speech 20, Music 20, Environment 20 |
| Messages | seeds 101 and 202, two messages per source |
| Audio protocol | 48 kHz, first 6 seconds, 32 physical positions |
| Strength | `1.60` |
| Selector | `REAL_TOP32`, watermark seed 7 |
| 8-bit threshold | `0.7855073980199624` |
| 12-bit threshold | `0.903827529676706` |
| MP3 | FFmpeg `libmp3lame`, 128 kbps |

Thresholds were inherited from the frozen P1/P2 records.  No V3-P2-V row was
used to refit them.

## Data independence

The manifest was selected before validation outcomes and excludes the audited
P0/R1, B1 Pilot, and V3-P1 manifests by path, file SHA256, source group, and
exact canonical first-six-second fingerprint.  The selected files have 60
unique paths, source groups, file hashes, and canonical crop hashes.

Exact path/hash/source-group/crop checks passed.  Near-duplicate or semantic
content equivalence is not established by these checks and is reported as a
limitation rather than treated as proven absent.  Raw MUSAN audio remains
outside the repository.

## Paired results

Counts below use the two messages per source as trial-level observations.  The
source-level metric requires both messages from a source to satisfy the stated
condition.

| Condition | Method | Raw exact | Correct accepted exact | Source raw exact | Source accepted exact | Logical BER | Physical BER | UNKNOWN |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| No attack | 8-bit | 120/120 | 120/120 | 60/60 | 60/60 | 0 | 0 | 0/120 |
| No attack | 12-bit | 120/120 | 120/120 | 60/60 | 60/60 | 0 | 0 | 0/120 |
| MP3 128k | 8-bit | 119/120 | 117/120 | 59/60 | 58/60 | 0.005208 | 0.063021 | 3/120 |
| MP3 128k | 12-bit | 116/120 | 97/120 | 57/60 | 45/60 | 0.009722 | 0.060677 | 23/120 |

`Correct accepted exact` means the frozen rejector accepted the detector output
and the decoded message exactly matched the predeclared message.  `Raw exact`
does not require acceptance.  Therefore the 12-bit gap is primarily a
rejection/score-margin loss under MP3, not an improvement in raw physical BER.

### MP3 results by category

Source-level correct accepted exact recovery, out of 20 sources per category:

| Category | 8-bit | 12-bit |
|---|---:|---:|
| Speech | 19/20 (95%) | 15/20 (75%) |
| Music | 20/20 (100%) | 18/20 (90%) |
| Environment | 19/20 (95%) | 12/20 (60%) |

The corresponding trial-level correct accepted exact counts are Speech 39/40,
Music 40/40, Environment 38/40 for 8-bit, and Speech 32/40, Music 37/40,
Environment 28/40 for 12-bit.

### Paired source comparison

For MP3 source-level correct accepted exact recovery, the paired table is:

| Outcome | Sources |
|---|---:|
| Both methods succeed | 45 |
| 8-bit only | 13 |
| 12-bit only | 0 |
| Neither | 2 |

The exact two-sided McNemar p-value is `0.000244140625`.  This is a paired
comparison on these 60 sources, not a claim of universal generalization.

## Fidelity

| Condition | Method | Mean SNR | Mean log-spectral distortion | Mean marked-to-MP3 SNR |
|---|---|---:|---:|---:|
| No attack | 8-bit | 54.9108 dB | 0.029855 dB | N/A |
| No attack | 12-bit | 54.9900 dB | 0.029921 dB | N/A |
| MP3 128k | 8-bit | 54.9108 dB | 0.029855 dB | 25.9587 dB |
| MP3 128k | 12-bit | 54.9900 dB | 0.029921 dB | 25.9578 dB |

The 12-bit candidate is numerically close in this fidelity budget: SNR differs
by `+0.0792 dB` and log-spectral distortion by `+0.000066 dB`.  This does not
establish a formal perceptual-quality result.

## Interpretation

The no-attack gate passes for both candidates.  Under real FFmpeg MP3 128 kbps,
8-bit has 97.5% trial-level correct accepted recovery and 96.67% source-level
two-message recovery.  12-bit has 80.83% and 75.00%, respectively.  The
12-bit source-level result is below the pre-registered 90% engineering target
and is 21.67 percentage points below 8-bit, exceeding the 5-point tolerance.

The 12-bit candidate is therefore not promoted.  No additional threshold
search, strength change, ECC, or capacity expansion was performed.

## Limitations and provenance

- Negative controls are matched clean and clean-MP3 versions of the 60
  validation sources; this is a useful paired control but not a separate pool
  of 60 unrelated negative recordings.
- Sixty negative sources are insufficient to claim population FPR below 1%.
  Wilson intervals are reported in the detection report.
- Exact fingerprint checks do not prove absence of near-duplicate or semantic
  content overlap.
- No formal human listening experiment was run.
- This report contains local validation results only; it does not import
  literature or historical P1/P2 numbers as new evidence.
