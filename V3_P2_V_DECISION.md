# V3-P2-V Decision

## Final fields

```makefile
V3_P2_V_STATUS = COMPLETE_VALIDATION; 12BIT_NO_GO
INDEPENDENT_SOURCE_COUNT = 60 (Speech 20, Music 20, Environment 20)
8BIT_EXACT_ACCEPTED = 117/120 trials; 58/60 sources on MP3 128k
12BIT_EXACT_ACCEPTED = 97/120 trials; 45/60 sources on MP3 128k
PAIRED_CAPACITY_TRADEOFF = 12-bit is -21.67 percentage points versus 8-bit at source level; 8-bit-only 13, 12-bit-only 0, McNemar p=0.000244
NEGATIVE_REJECTION = 8-bit clean 0/60, clean-MP3 1/60; 12-bit clean 0/60, clean-MP3 0/60; zero rates do not prove FPR <1%
WRONG_MESSAGE_ACCEPTANCE = 0/120 MP3 trials for both methods
MATCHED_FIDELITY = 12-bit minus 8-bit: +0.0792 dB SNR, +0.000066 dB LSD; formal perceptual gate not established
RECOMMENDED_DEFAULT_CAPACITY = 8-bit Soft-Code
V3_RELEASE_READINESS = NO-GO for 12-bit default; retain frozen 8-bit baseline
```

## Decision rationale

The validation protocol passed its execution and provenance gates.  Both
methods achieved 120/120 clean exact recovery.  On real FFmpeg MP3 128 kbps,
the frozen 8-bit candidate achieved 117/120 correct accepted trials and 58/60
source-level two-message successes.  The frozen 12-bit candidate achieved
97/120 and 45/60.  The 12-bit source-level result is below the 90% target and
falls 21.67 percentage points below 8-bit, not within the allowed 5-point
degradation.

The fidelity budget is comparable, so the result is not explained by a large
measured embedding-distortion difference.  Wrong-message acceptance and
wrong-key acceptance were zero in this finite run, but the negative sample is
not large enough to support a population FPR claim below 1%; 8-bit also has one
clean-MP3 false positive.

## Stop decision

Stop the V3-P2 capacity expansion at 12-bit.  Keep the 8-bit Soft-Code as the
default frozen candidate.  Do not tune the validation threshold, increase
strength, add ECC, or continue to 16-bit on the basis of this result.
