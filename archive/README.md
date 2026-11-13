# Historical versions / 历史版本

The **current course project is C2/C3**. Start at the [main README](../README.md), [中文主页](../README_ZH.md) or [course_release](../course_release/).

Older implementations remain available for reproducibility. **Archiving is documentation and immutable branch snapshots, not deletion of old code.** The existing V3 Render service and V4 work-in-progress remain untouched.

| Version | Approach | Original-message requirement | Main payload | Archival location |
| --- | --- | --- | --- | --- |
| Course V2 | Fixed-label spectral QIM | Blind | 4 labels = 2 bits of identity | [v2 notes](v2/README.md), [historical files](../docs/v2/) |
| V3 | FFT/QIM + Soft-Code | Blind | 8 bits / 6 s | [v3 notes](v3/README.md), [snapshot branch](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v3-legacy-20261113) |
| V4 | Sony SilentCipher-based neural Studio | Blind | 40 bits / 12 s | [v4 notes](v4/README.md), [snapshot branch](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113) |
| **Current C2/C3** | Multiband reference-assisted DSP | **Reference required** | 32-bit repeated ID / 192-bit independent long message | [course_release](../course_release/) |

> The historical V2 “32-bit codeword” was a redundant encoding of **one of four fixed labels (2 information bits)**; it is **not** the current C2 Long-ID carrying a genuine repeated 32-bit identity.

Preserved README snapshots from before the course-final release:
- [Old English README](README_previous_main_2026-11-13.md)
- [Old Chinese README](README_ZH_previous_main_2026-11-13.md)

Current remote deployments still display older versions until the separately planned website work is completed:
- [Personal project page](https://shengkaini.com/blind-audio-watermarking/) — historical V4 site.
- [Existing Render service](https://blind-audio-watermarking-demo.onrender.com/) — V3 legacy GUI.

Do not silently substitute a recorded V4 blind result for a C2/C3 reference-assisted result.
