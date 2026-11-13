# Course V2 — four-identity watermark (historical)

This is an **older DSP course exercise**, retained for the project record. Its four identity labels were mapped to 32-bit redundant codewords; the payload represented **only two independent identity bits**. This is not the current C2 Long-ID mode.

### Original implementation and evidence

- [Historical V2 notes and assets](../../docs/v2/)
- [Legacy method document](../../docs/METHOD.md)
- [Legacy results](../../docs/RESULTS.md)
- [Legacy limitations](../../docs/LIMITATIONS.md)
- [V3-era repository snapshot containing V2 documents](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v3-legacy-20261113)

Recorded historical V2 demonstration: 48/48 correct labels without processing, 46/48 after MP3 128 kbps; these are four-label decisions, **not arbitrary 32-bit message recovery**.

The final C2/C3 method uses a different detector, payload and evaluation protocol. See [course release](../../course_release/).
