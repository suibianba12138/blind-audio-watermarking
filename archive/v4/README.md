# V4 — neural blind watermarking Studio (historical)

V4 explored a different approach: **Sony Research's third-party pretrained SilentCipher** neural watermark, integrated into a local audio watermarking Studio. This was a **blind** detector, unlike the current reference-assisted C2/C3 DSP system.

### Preserved development snapshot

- [Historical code snapshot](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113), at commit `68830f41`.
- [Original V4 working branch](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep) and [historical Draft PR #5](https://github.com/suibianba12138/blind-audio-watermarking/pull/5).
- [Historical English README](../README_previous_main_2026-11-13.md) and [Chinese README](../README_ZH_previous_main_2026-11-13.md).
- The previous V4 project landing page is preserved in the personal homepage repository's [archive branch](https://github.com/suibianba12138/suibianba12138.github.io/tree/archive/audio-watermark-v4-20261113). The **live project website now features C2/C3**.

V4 experiments used **40-bit payload / 12-second inputs**. Recorded P9 results over a limited source set were 24/24 correctly accepted for Clean, 24/24 for MP3, and 23/24 for AAC; these cannot be merged with the C2/C3 evaluation protocol.

SilentCipher is a **third-party pretrained model**, not a model developed or trained by this course team. Its weights are not bundled in the C2/C3 release.

For the final course DSP system, see [C2/C3](../../course_release/).
