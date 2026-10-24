# V3-P2 Channel Error Analysis

## Scope and provenance

This is a development-only diagnostic for the frozen B1-QIM channel. It uses
the 30 `split=dev` source recordings from the frozen V3-P1 manifest, with two
fixed messages (`seed_101` and `seed_202`) per source. For each message the
existing B1 embedder is followed by a real FFmpeg `libmp3lame` 128 kbps
round-trip. The first five sources in each category are labelled calibration
and the last five pilot; this role split is recorded but no codebook or
threshold is fitted from the P1 formal test split.

The detector receives only the received audio and the frozen public selector.
The expected physical word is used only after detection to score the CSV.
Raw per-bit rows are in
`experiments/v3_p2/V3_P2_CHANNEL_DIAGNOSTICS.csv`; the machine-readable
summary is `experiments/v3_p2/V3_P2_CHANNEL_ANALYSIS.json`.

## Confirmed development observations

| Quantity | Result |
|---|---:|
| Source recordings | 30 |
| Paired messages | 60 |
| Physical observations after MP3 | 1,920 |
| Marked, no-attack physical BER | 0.0000 |
| MP3 128 kbps physical BER | 0.0546875 (105/1,920) |
| Mean MP3 physical errors per 32-bit word | 1.75 |
| Error-count variance | 3.4875 |
| IID binomial variance at observed BER | 1.6543 |
| Observed/IID dispersion ratio | 2.1081 |

Category BER was 0.0500 for Speech, 0.0500 for Music, and 0.0640625 for
Environment. These are development diagnostics, not independent validation
estimates.

## Position dependence

The highest observed MP3 BER positions were physical bit 1 (0.1833), bits 2
and 7 (0.1333 and 0.1167), bit 20 (0.1167), and bits 19, 24, and 31 (0.0833
each). Positions 6 and 29 had zero errors in this finite development sample.
The complete 32-position table, including counts, mean absolute statistic, and
MP3 drift, is in the JSON/CSV artifacts rather than being summarized as a
universal carrier ranking.

The physical error-count distribution over the 60 paired words was:

```text
errors: 0  1  2  3  4  5  6  7
trials: 19 14 13  4  2  5  1  2
```

This distribution is more dispersed than an IID binomial model with the same
mean. The mean off-diagonal error correlation was 0.03683 and the mean
adjacent-position correlation was -0.00934. The largest contiguous error run
was 2 positions, with mean run length 1.05 among observed runs. The evidence
therefore supports position/content heterogeneity and over-dispersion, but it
does not establish a simple burst-error process.

## Soft reliability and host interaction

The correlation between absolute MP3 statistic magnitude and the binary
physical-error indicator was -0.3492 in this sample: lower absolute signed
margin tended to be less reliable. This is diagnostic evidence, not a
calibrated probability model. The mean signed expected-direction host
statistic before embedding was -0.01650, while the corresponding marked
alignment was 1.60000; the no-attack BER was consequently zero. The overall
mean MP3-minus-marked statistic drift was 0.01029, but the per-position drift
table shows substantial signed heterogeneity.

## Interpretation and limits

`CHANNEL_ERROR_MODEL = PARTIAL_NON_IID_DIAGNOSTIC`: the finite development
data show position-dependent and over-dispersed errors. A short-code design is
therefore evaluated by paired decoding results rather than by assuming an IID
channel. The P1 formal test rows were not used to select a new encoder or
threshold. No general codec-robustness, population BER, or independent-test
claim follows from this artifact.
