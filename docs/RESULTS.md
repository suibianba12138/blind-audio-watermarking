# Results and provenance

## Frozen Course V2 validation record

The following numbers are transcribed from the frozen Course V2 final report at
source commit `7b0dca6b94f74d98304b1cb4a64209201fb2675a`. They are provenance
records, not a claim that this clean export re-ran the original data matrix:

The underlying calibration/validation protocol used external MUSAN / OpenSLR
SLR17 source recordings. Only aggregate statistics are included here; no raw
MUSAN audio, archive, or per-recording manifest is redistributed. OpenSLR lists
SLR17 as CC BY 4.0 and should be cited as the data source.

| Measurement | Frozen result | Scope |
|---|---:|---|
| No-attack identity | 48/48 (100%) | 48 independent positive sources |
| MP3 128 kbps identity | 46/48 (95.83%) | same positive-source protocol |
| MP3 complete arbitrary 32-bit recovery | 5/48 (10.42%) | not equivalent to identity recovery |
| False identification | 0/48 | positive-source identity decisions |
| Identity negative FPR | 1/60 (1.67%) | no-watermark negative set |
| MP3 negative FPR | 0/60 | no-watermark negative set |

The two MP3 `UNKNOWN` positive cases were environment recordings with distances
9 and 11. The identity false positive was a negative example at the exact
distance threshold 8. These cases are retained as limitations rather than
hidden by a post hoc threshold change.

All 48 formal positives used 6 seconds / 1 block. The 15/30-second paths were
available for course demonstration but were not part of that formal positive
matrix.

## Clean-export smoke evidence

The release test suite checks codebook geometry, deterministic embedding,
arbitrary 32-bit round-trip, map/selector hashes, blind CLI arguments, and the
absence of personal absolute paths in public Python files. A generated signal
is used so no external recording is needed. The test output belongs to this
export and must be reported separately from the frozen validation table.

## Audio quality status

The frozen objective peak audit found no new clipping introduced by the
watermark path, but eight of 48 positive source recordings already exceeded a
unit peak before embedding. A formal listening/perceptual gate was not
established. This release therefore does not claim imperceptibility.
