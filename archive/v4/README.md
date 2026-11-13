# V4 — neural blind watermarking Studio (historical)

V4 explored a different approach: **Sony Research's third-party pretrained SilentCipher** neural watermark, integrated into a local audio watermarking Studio. This was a **blind** detector, unlike the current reference-assisted C2/C3 DSP system.

### Preserved development snapshot

- [Frozen-at-archive code branch](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113), starting from commit `68830f41`.
- [Original V4 preparation branch](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep).
- [Historical Draft PR #5](https://github.com/suibianba12138/blind-audio-watermarking/pull/5), which was not merged into the course-final `main`.
- [Legacy English README snapshot](../README_previous_main_2026-11-13.md) and [Chinese snapshot](../README_ZH_previous_main_2026-11-13.md).
- [Existing personal project site](https://shengkaini.com/blind-audio-watermarking/) currently still shows V4 content; it is not a C2/C3 live engine.

The V4 local model stage used **40-bit / 12-second** payloads. Historic small-sample P9 results included 24/24 correct accepted in Clean and MP3, and 23/24 in AAC; such results are for a different model, detector and dataset.

**Attribution:** SilentCipher is third-party pretrained work, not a model designed or trained by this course team. Model weights and upstream code are not redistributed in the C2/C3 course package. Refer to Sony's official project for licensing and model availability.

For the project presented in the final DSP course: [C2/C3 release](../../course_release/).
