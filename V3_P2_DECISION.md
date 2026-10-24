# V3-P2 Decision

## Decision fields

```makefile
V3_P2_STATUS = CONDITIONAL_GO_12BIT_ONLY
FROZEN_8BIT_BASELINE = PASS
CHANNEL_ERROR_MODEL = PARTIAL_NON_IID_DIAGNOSTIC
12BIT_CAPACITY_FEASIBILITY = PROMISING_CONDITIONAL
16BIT_CAPACITY_FEASIBILITY = NO_GO_FOR_NEXT_STEP
MP3_EXACT_RECOVERY = 8-bit 30/30 raw and 28/30 accepted (14/15 sources both accepted); 12-bit 30/30 raw and 27/30 accepted (13/15 sources both accepted); 16-bit 28/30 raw and 26/30 accepted (12/15 sources both accepted), P2 development pilot
NEGATIVE_REJECTION = 0/15 source-level clean FPR, 0/15 source-level MP3-clean FPR, 0/15 source-level wrong-key acceptance for each method in pilot role (30 paired rows per negative condition)
MATCHED_FIDELITY = PILOT_NUMERICAL_MATCH (mean SNR range 0.1323 dB; LSD range 0.00058 dB; formal perception NOT_ESTABLISHED)
RECOMMENDED_CAPACITY = 12-bit candidate only
INDEPENDENT_VALIDATION_READINESS = CONDITIONAL_12BIT_ONLY
```

## Reasoning

The frozen 8-bit reference decoded all 30 MP3 pilot messages exactly, with two
additional UNKNOWN outcomes after the unchanged P1 threshold. The 12-bit code
also decoded all 30 messages exactly and had zero logical BER, but its
calibration-derived rejector accepted 27/30 exact messages on the held-out
pilot. This is enough to justify a source-disjoint 12-bit validation protocol,
not enough to claim a practical improvement over 8-bit.

The 16-bit code decoded 28/30 messages, had logical BER 0.029167, and accepted
26/30 exact messages. It does not justify another round of capacity tuning.

All negative counts are finite development counts: 15 unique clean sources,
15 unique clean-MP3 sources, and 15 unique wrong-key source recordings per
method in the pilot role, represented by 30 paired message rows for each
condition. The observed zero rates must not be reported as a population FPR
below 1%. A future validation must freeze the 12-bit threshold and use new,
source-disjoint recordings.

## Explicit stop conditions and next boundary

- Stop the 16-bit capacity branch; no extra code search or threshold tuning was
  performed after the pilot.
- Do not modify the physical QIM channel or the frozen 8-bit baseline.
- If continuing, create a new independent source manifest and validate only the
  frozen 12-bit candidate, its frozen threshold `0.903827529676706`, and the
  same negative controls.
- Do not treat this P2 development pilot as V3-P1-style independent evidence.
