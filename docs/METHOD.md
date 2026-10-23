# Method

## Frozen signal path

The public export calls the existing fixed B1 transform-domain path. It uses
48 kHz mono audio, 2048-point rectangular non-overlapping frames, four frame
repetitions per payload bit, a 1000–10000 Hz candidate band, and the frozen
REAL_TOP32 selector. Embedding changes the selected A/B log-magnitude lattice
while preserving the phase. The public code does not introduce a new watermark
algorithm.

The arbitrary payload interface is:

```python
from audio_watermark.b1 import embed_watermark_b1, detect_watermark_b1
```

It accepts and returns a 32-bit payload through the same blind public selector.

## Identity mode

The four public identities are mapped to two source bits `(a, b)` and the fixed
codeword

```text
[a repeated 10, b repeated 11, (a XOR b) repeated 11]
```

Every codeword has length 32. The complete codebook is content-independent,
deterministic, and has minimum pairwise Hamming distance 21. This redundancy
does not turn the mode into a general 32-bit error-correcting message service:
only 2 bits carry identity information.

## Multiblock mode

The public duration choices are 6, 15, and 30 seconds. The implementation
actually embeds the selected identity in complete six-second blocks, yielding
1, 2, or 5 blocks respectively. Detection aggregates signed per-bit evidence
with equal weight and then performs the same identity-distance decision.

The formal frozen reliability evidence covers 6 seconds / 1 block. The longer
modes are retained for the demo path and are not silently promoted to formal
validation evidence.

## Rejection and blind boundary

The detector computes Hamming distances to the four legal codewords and returns
`UNKNOWN` when the minimum distance exceeds 8 or when the nearest decision is
tied. The threshold and strength are frozen public configuration, not selected
from this release smoke test. The detector process reads only the received
audio, public configuration, and public map.
