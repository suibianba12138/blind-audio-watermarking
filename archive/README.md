# Historical versions / 历史版本归档

The **current course final is C2/C3 reference-assisted watermarking**. Start at the [project homepage](../README.md), [中文 README](../README_ZH.md), [interactive website](https://shengkaini.com/blind-audio-watermarking/) or [course release](../course_release/).

Previous work is kept as **documentation and immutable Git branch snapshots**, without deleting legacy source files or changing the existing Render V3 service.

| Version | Method | Need original for detection? | Payload | Archive |
| --- | --- | --- | --- | --- |
| **Course V2** | Four-label identity / spectral QIM | No | Four IDs → 2 independent bits | [V2 notes](v2/README.md) |
| **V3** | FFT/QIM + Soft-Code | No (blind) | 8 bit / 6 s | [V3 notes](v3/README.md) · [snapshot](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v3-legacy-20261113) |
| **V4** | Third-party Sony SilentCipher neural Studio | No (blind) | 40 bit / 12 s | [V4 notes](v4/README.md) · [snapshot](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113) |
| **Current C2/C3** | Reference-assisted multiband DSP | **Yes** | 32-bit repeated ID / 192-bit independent | [course_release](../course_release/) |

Historical V2 32-bit redundant codewords represent one of four identities (**2 independent bits**). They must not be confused with the current **C2 32-bit repeated-ID** mode.

Preserved old README snapshots:
- [English](README_previous_main_2026-11-13.md)
- [中文](README_ZH_previous_main_2026-11-13.md)

**Websites:** The [current public project page](https://shengkaini.com/blind-audio-watermarking/) presents C2/C3 with actual media and recorded results. It is a **static interactive showcase**, not an embedding/detection backend. The [existing Render service](https://blind-audio-watermarking-demo.onrender.com/) is still **historical V3**.
