# V3-P2-V Detection and Rejection Report

## Frozen rejector

The detector used the frozen thresholds without validation-set calibration:

| Method | Threshold | Detector inputs |
|---|---:|---|
| 8-bit Soft-Code | 0.7855073980199624 | received audio, public config, pre-shared selector |
| 12-bit Soft-Code | 0.903827529676706 | received audio, public config, pre-shared selector |

Expected payload, clean audio, ground truth, and filename labels were used only
after blind detection for scoring.  The result CSV records
`detector_expected_payload_used=False` for every row.

## Negative and wrong-key controls

Source-level rates use 60 validation sources.  Wrong-key controls have two
message trials per source, so their trial denominator is 120.

| Method | Clean FPR | Clean-MP3 FPR | Wrong-key MP3 acceptance |
|---|---:|---:|---:|
| 8-bit | 0/60 (0%) | 1/60 (1.667%) | 0/120 (0%); 0/60 sources |
| 12-bit | 0/60 (0%) | 0/60 (0%) | 0/120 (0%); 0/60 sources |

The two-sided 95% Wilson source-level interval for 0/60 is `[0%, 6.017%]`.
For the 8-bit clean-MP3 result 1/60, it is `[0.295%, 8.855%]`.  These finite
sample results do not establish FPR below 1%.

The single 8-bit clean-MP3 false positive was:

| Source | Category | Score | Threshold | Decoded payload |
|---|---|---:|---:|---|
| `v3-p2-v-speech-0016` | Speech | 0.7939169694 | 0.7855073980 | `00001111` |

No expected message was supplied to this negative detector call.

## Positive acceptance and UNKNOWN

For MP3 128 kbps:

| Method | Accepted trials | UNKNOWN trials | Accepted exact | Wrong-message accepted |
|---|---:|---:|---:|---:|
| 8-bit | 117/120 | 3/120 | 117/120 | 0/120 |
| 12-bit | 97/120 | 23/120 | 97/120 | 0/120 |

The 8-bit rejected rows were one wrong raw decode and two correct raw decodes
below the frozen presence threshold.  The 12-bit rejected rows included 19
correct raw decodes below threshold and 4 wrong raw decodes; none of the wrong
decodes was accepted.

The 12-bit rejected/failed source distribution was Speech 5/20 sources,
Music 2/20, and Environment 8/20.  This category pattern is consistent with
the source-level results in the validation report; it was not used to adjust
the detector.

## Decision

The rejector did not accept wrong messages or wrong-key inputs in this finite
run.  However, the 12-bit threshold produces too many UNKNOWN outcomes under
MP3 to meet the pre-registered capacity target.  The 8-bit clean-MP3 false
positive is retained as a real limitation rather than hidden.
