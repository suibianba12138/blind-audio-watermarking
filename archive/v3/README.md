# V3 — classical blind FFT/QIM watermark (historical)

V3 was the earlier **blind** DSP implementation, combining FFT/QIM and Soft-Code to recover **8-bit messages** from six-second audio without supplying an unwatermarked original to the detector.

### Preserved code and demonstration

- [Read-only V3 code snapshot](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v3-legacy-20261113) (the former `main` head, commit `22073248`).
- [Original source modules](../../src/) and [V3 app](../../app/) remain in `main` for compatibility, rather than being moved or deleted.
- [Historical V3 project site assets](../../docs/v3/).
- [V3 results](../../docs/RESULTS.md), [method](../../docs/METHOD.md), [limits](../../docs/LIMITATIONS.md).
- [Legacy Render demo](https://blind-audio-watermarking-demo.onrender.com/) remains V3, not the course-final C2/C3 system.

Recorded frozen V3 MP3 six-second evaluation: **117/120 correct accepted**. This cannot be transferred to C2/C3, which uses a **reference-assisted** detector and different protocols.

The historical Render service is set to manual deployments. The archive branch preserves the last pre-course-release repository state.
