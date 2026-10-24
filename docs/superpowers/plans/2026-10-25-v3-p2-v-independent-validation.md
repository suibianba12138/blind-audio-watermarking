# V3-P2-V Independent Validation Plan

## Scope

Validate the already frozen 8-bit and 12-bit capacity candidates on a new,
source-disjoint MUSAN manifest. Do not change the B1 physical channel, either
capacity code, thresholds, selector, strength, or any historical result.

## Gates

1. Confirm `63d3166b1eeb2f0f7e99c8a9ad181934b824370e` and create only
   `research/v3-p2-validation`.
2. Freeze a manifest with 20 speech, 20 music, and 20 environment source
   recordings after excluding all audited P0/R1/Pilot/P1/P2 records by path,
   SHA256, and source-group identity. Do not copy raw audio into Git.
3. Freeze an evaluation record containing the 8-bit threshold, 12-bit P2
   threshold, strength, selector/map, message seeds, MP3 command, detector
   contract, and source/config hashes before running the validation.
4. Run paired clean and FFmpeg `libmp3lame` 128 kbps trials for both methods,
   with two fixed messages per source and expected payloads used only by the
   post-detection scorer.
5. Run matched clean/MP3 negative controls and wrong-key controls using the
   frozen rejector; never fit a threshold on validation rows.
6. Aggregate trial and source-level results, category results, paired
   differences, Wilson intervals, and explicit sample-size limitations.
7. Write the four V3-P2-V reports and CSV, run regression and frozen-core
   checks, then commit locally without pushing or merging.

## Artifacts

- `configs/v3_p2_v_independent_manifest.json`
- `experiments/v3_p2_v/CONFIG_FREEZE.json`
- `experiments/v3_p2_v/` raw JSON/CSV summaries (metadata only; no audio)
- `V3_P2_V_INDEPENDENT_VALIDATION.md`
- `V3_P2_V_PAIRED_RESULTS.csv`
- `V3_P2_V_DETECTION_REPORT.md`
- `V3_P2_V_DECISION.md`

## Stop rules

- Stop capacity expansion if 12-bit does not meet the pre-registered target
  or has a material rejection/fidelity regression; retain 8-bit as default.
- Do not claim FPR below 1% from a small negative set; report Wilson bounds.
- Any data, detector-contract, or frozen-source violation invalidates the
  formal validation and is reported as blocked rather than repaired by tuning.
