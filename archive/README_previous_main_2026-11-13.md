<div align="center">

# Robust Audio Watermarking Studio

### Embed · Transmit · Detect · Analyze

**Blind audio watermarking with a neural V4 Studio and a reproducible classical DSP baseline**

[**Project Showcase (V4)**](https://shengkaini.com/blind-audio-watermarking/) · [**V4 Source / Local Studio**](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep) · [**Live V3 Demo**](https://blind-audio-watermarking-demo.onrender.com/) · [**中文说明**](README_ZH.md)

![V4](https://img.shields.io/badge/V4-Local_Studio-127B86)
![V3](https://img.shields.io/badge/V3-DSP_Baseline-43576E)
![Python](https://img.shields.io/badge/Python-3.12%2B_for_V4-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/Project_Code-MIT-2B8C8A)

</div>

---

## Overview

This digital signal processing course project studies **blind audio watermarking**: embedding a message into audio and recovering it from the received file, without providing the detector with the original audio or the expected message.

The project has evolved from a classical **V2 identity-code system** through an **8-bit V3 FFT/QIM + Soft-Code implementation** to the **V4 Robust Audio Watermarking Studio**. V4 combines Sony Research's third-party pretrained SilentCipher model, real audio codec round trips, independent blind detection, and waveform/spectral analysis. V3 remains a distinct, reproducible DSP baseline.

**Repository status (2026-11-08):** The default `main` branch still hosts the historical V3/Legacy code and online demo. **V4 code is in the open [Draft PR #5](https://github.com/suibianba12138/blind-audio-watermarking/pull/5), branch [`upgrade/v4-github-prep`](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep), and has not been merged.** This README introduces the current project as a whole; it does **not** imply that a V4 installation can be started directly from `main`.

## Explore

| Resource | What it offers | Availability |
| --- | --- | --- |
| [V4 project showcase](https://shengkaini.com/blind-audio-watermarking/) | Reported 40-bit results, system workflow, version history | Static site; **no V4 online inference** |
| [V4 source + detailed README](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep) | Full local Gradio Studio and reproduction instructions | Draft branch; external model required |
| [Live classical DSP demo](https://blind-audio-watermarking-demo.onrender.com/) | Existing V3/Legacy hosted workflow | V3 **only**, not V4 |
| [V2/V3 method](docs/METHOD.md) · [results](docs/RESULTS.md) | Historical FFT/QIM parameters and course evidence | Maintained in `main` |
| [V4 reports](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep/docs/reports/v4) | Evaluation reports, limitations, and negative results | Draft branch |

## Three versions, distinct claims

| | Course V2 | V3 · Classical DSP | V4 · Studio |
| --- | --- | --- | --- |
| **Engine** | REAL_TOP32 spectral QIM | FFT/QIM + Soft-Code | Sony SilentCipher (pretrained) **and** the frozen V3 baseline |
| **Message** | Four preset identities, 32-bit redundant codewords representing **2 information bits** | 8-bit variable message (0–255) | 40-bit (5-byte) neural payload, or V3 8-bit mode |
| **Representative input** | 6 s / mono | 6 s / 48 kHz mono | Neural: 12 s / 44.1 kHz mono; V3: 6 s / 48 kHz |
| **Evidence** | MP3 identity: **46/48** | MP3 correct accepted: **117/120** | See V4 evidence below |
| **Role now** | Historical reference | Baseline + existing online demo | Main local experimental system |

V2 and V3 use different message spaces and evaluation protocols. Their percentages are **not** directly comparable to V4 recovery rates. The Sony model is **third-party work, not a model developed or trained by this project**.

## V4 Studio · four modules

1. **Watermark** — upload source audio, embed a 40-bit neural or 8-bit DSP watermark, and obtain prepared/marked WAV files.
2. **Channel Lab** — perform **real FFmpeg** MP3 128 kbps and AAC-LC/M4A 128 kbps round trips, or evaluate seeded noise/cropping.
3. **Blind Detection** — independently re-upload the received audio; return `IDENTIFIED`, `UNKNOWN`, or `DECODE_ERROR` without access to the embed-session answer.
4. **Signal Analysis** — compare aligned waveforms and STFT spectra, and report SNR/LSD only when alignment is credible.

The Studio is **local-first**, CPU-compatible, and not deployed on the existing Render V3 service. Its neural inference requires separately obtained official SilentCipher source and checkpoint files; **model weights are not stored or redistributed here**.

## Recorded results (bounded evidence)

| Evaluation | Reported outcome | Qualification |
| --- | --- | --- |
| V4 P9, 12 independent sources × 2 fixed messages | Clean **24/24**, MP3 128 kbps **24/24** correct accepted | Fixed evaluation; limited source diversity |
| V4 P9, AAC-LC/M4A 128 kbps | **24/24** exact raw decodes; **23/24** correct accepted | One correct decode rejected by provisional threshold |
| V4 P4, four selected demonstration clips × three channels | **12/12** correct file re-upload detections | Browser and human listening acceptance still pending |
| V4 local release smoke, 2026-11-07 | Clean / MP3 / AAC exact message recovered; **79/79 tests** | One licensed music excerpt; not a new generalization benchmark |
| Frozen V3, 6-second MP3 evaluation | **117/120** correct accepted | Separate classical DSP protocol |
| Frozen Course V2, MP3 identity evaluation | **46/48** identity accepted | Four-label classification, not arbitrary 32-bit recovery |

These are *recorded local evaluations*, not a guarantee for arbitrary content or attacks. Noise/crop support is **not** a claim of robustness to those transformations. The provisional neural detection threshold is not calibrated as a population-level false-positive guarantee. Negative experiments and protocol caveats are retained in the [V4 reports](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep/docs/reports/v4).

## Run the V4 Studio locally

**First switch to the V4 branch.** This is essential while Draft PR #5 remains unmerged.

    git clone https://github.com/suibianba12138/blind-audio-watermarking.git
    cd blind-audio-watermarking
    git switch upgrade/v4-github-prep

Use a dedicated **Python 3.12+** environment and install FFmpeg (including `ffprobe`, MP3 and AAC encoders). Install `requirements-v4.txt`, a compatible CPU PyTorch build, and obtain the **official** Sony SilentCipher source and 44.1 kHz checkpoint from [Sony's repository](https://github.com/sony/silentcipher). Configure the external directories, then launch:

    export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher
    export SILENTCIPHER_MODEL_DIR=/path/to/official/44_1_khz/73999_iteration
    export V3_SOURCE_ROOT="$PWD"
    export V4_STUDIO_PYTHON=python
    bash scripts/run_v4_studio.sh

Open **http://127.0.0.1:7862**. The Studio does not expose a public sharing URL. Full dependency, licensing, and reproduction details: [V4 README](https://github.com/suibianba12138/blind-audio-watermarking/blob/upgrade/v4-github-prep/README.md) and [V4 reproduction notes](https://github.com/suibianba12138/blind-audio-watermarking/blob/upgrade/v4-github-prep/docs/V4_REPRODUCTION.md). The tested runtime combination is engineering compatibility evidence, not an official upstream dependency guarantee.

### Run the current `main` branch (V3/Legacy)

**From `main` only**, with Python 3.10+ and FFmpeg:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[gui,dev]'
    python examples/generate_test_audio.py --output /tmp/watermark_test_signal.wav
    python scripts/demo.py --input /tmp/watermark_test_signal.wav --identity UESTC-003 --codec mp3
    python -m app.gui

This starts the **existing historical DSP interface**, **not** the V4 Studio.

## Verification, provenance, and limitations

- V4: 79 automated tests passed in the recorded 2026-11-07 smoke; a fresh model-based Clean/MP3/AAC file re-upload was also validated. **Real browser visual/click-through acceptance and human A/B listening remain pending.**
- The P9 evaluation used only 12 independent source clips; its finite counts do not establish broad robustness, perceptual transparency, or formal false-acceptance bounds.
- Public watermark labels are not cryptographic proof of ownership. Intentional attacks, forging, and broader cross-domain generalization have not been established.
- Original project code uses the [MIT License](LICENSE). Sony SilentCipher is explicitly attributed as third-party software. Its checkpoint's separate redistribution terms remain unclear, so weights are **not bundled**. Third-party evaluation audio is not redistributed.
- Source-level V2/V3 documents remain [Method](docs/METHOD.md), [Results](docs/RESULTS.md), and [Limitations](docs/LIMITATIONS.md).

---

<div align="center"><sub>Robust Audio Watermarking Studio · Digital Signal Processing · Clear evidence, clear version boundaries.</sub></div>
