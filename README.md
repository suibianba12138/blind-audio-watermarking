<div align="center">

# Blind Audio Watermarking

### Embed. Compress. Detect.

**Codec-Aware Blind Audio Watermarking with Error-Correcting Identity Codes**

A digital signal processing course project that embeds a limited identity into audio and recovers it **without the original recording**, including real MP3 compression.

[**🌐 Project Site (source)**](docs/index.html) · [**🎛️ Run Demo**](#-quick-start) · [**📐 Method**](docs/METHOD.md) · [**📊 Results**](docs/RESULTS.md)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2B8C8A)
![MP3](https://img.shields.io/badge/Recorded_MP3_Identity-46%2F48-188A69)
![Demo](https://img.shields.io/badge/Hosted_Backend-Not_Live-D97706)

</div>

---

## 🎧 Demo — Embed → Compress → Detect

Upload a short audio file, choose one of **four preset identities**, embed a redundant 32-bit codeword, apply real FFmpeg **MP3 128 kbps** compression and run a separate **blind detector**. The result is an identity or **UNKNOWN**.

| 01 · Embed | 02 · Compress | 03 · Detect |
| :---: | :---: | :---: |
| REAL_TOP32 spectral QIM | FFmpeg MP3 128 kbps | Independent blind decoding |
| Four-label identity codebook | Actual audio processing | Identity or UNKNOWN |

The interactive Python demo runs locally using Gradio. The [responsive project website](docs/index.html) offers an informational showcase and a **browser-local waveform/player preview** only. It **does not** pretend to embed or detect watermarks before a hosted Python service is deployed.

## ✨ Highlights

- **Blind detector:** no clean audio, expected identity, original payload, filename label or answer cache is supplied.
- **Codec-aware carrier selection:** frozen REAL_TOP32 frequency map.
- **Identity encoding:** four preset identities mapped to 32-bit codewords, minimum pairwise Hamming distance **21**, rejection threshold **8**.
- **Real MP3 processing:** encode and decode through FFmpeg.
- **Baseline API:** arbitrary 32-bit payload embedding/detection remains accessible, but is far less reliable after MP3.
- **Multi-block processing:** 6 / 15 / 30 s implementations; formal validation refers to **6 s / one block** only.

## 🧩 How It Works

**Audio → spectral QIM / REAL_TOP32 → MP3 → blind bit decoding → codebook match or UNKNOWN**

The identity codebook carries only **2 bits of information** (four possible labels) in each 32-bit redundant codeword. **95.83% identity accuracy does not mean that arbitrary 32-bit payloads are recovered at 95.83%.** The frozen operating point is strength **1.28**, threshold **8**, seed **7**. See [Method](docs/METHOD.md).

## 📊 Evaluation — Frozen Course V2

These values are recorded from the earlier Course V2 validation at source commit **7b0dca6b94f74d98304b1cb4a64209201fb2675a**. They were **not re-measured** using the clean public export.

| Measurement | Recorded result |
|---|---:|
| Identity, no attack | **48/48 (100%)** |
| Identity, MP3 128 kbps | **46/48 (95.83%)** |
| Arbitrary 32-bit full packet, MP3 | **5/48 (10.42%)** |
| Wrong identity on positive MP3 recordings | **0/48** |
| Unmarked-source false positives | **1/60** |
| MP3-negative false positives | **0/60** |

All 48 positive source tests were **6 s / 1 block**. Two environment audio cases returned UNKNOWN after MP3. The frozen peak audit found no additional clipping, but **formal perceptual/listening validation is not established**. These finite-sample results do not guarantee equivalent results for arbitrary uploads.

[**Read full results and provenance →**](docs/RESULTS.md)

## 🚀 Quick Start

**Prerequisites:** Python 3.10+ and FFmpeg installed and on PATH.

~~~bash
git clone https://github.com/suibianba12138/blind-audio-watermarking.git
cd blind-audio-watermarking

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[gui,dev]'

python examples/generate_test_audio.py --output /tmp/watermark_test_signal.wav
python scripts/demo.py --input /tmp/watermark_test_signal.wav --identity UESTC-003 --codec mp3
python -m app.gui
~~~

The GUI binds to **127.0.0.1** without public sharing. CLI outputs include the prepared source, marked WAV, compressed MP3, decoded WAV and blind detector JSON. For checks: run **python -m pytest -q** after installing the development extra.

## 📂 Repository Layout

~~~text
src/audio_watermark/   QIM and blind detection
app/                   Local Gradio GUI, FFmpeg, independent detector
configs/               Frozen carrier map and parameters
scripts/               CLI embedding and detection
tests/                 Standalone contract checks
examples/              Generated synthetic audio example
docs/                  Architecture, results, limits and site
~~~

## 🌐 Website & Deployment

The site source is at [docs/index.html](docs/index.html) with styles and scripts in **docs/assets/**. It follows the information hierarchy of [RecallVision-Course](https://github.com/suibianba12138/RecallVision-Course), adapted to DSP audio. GitHub Pages can host the site after deployment is configured; it cannot run the Python processing service. The hosted backend will be integrated only when actually deployed and validated.

## ⚠️ Scope & Limitations

This is a teaching prototype, **not cryptographic ownership authentication**. Public identities can be imitated, intentional forgery/removal resistance is untested, and broad codec generalization has not been established. Longer modes have smoke tests but no formal success-rate evidence. The project redistributes **no MUSAN raw audio**; its frozen research data used [MUSAN / OpenSLR SLR17](https://www.openslr.org/17/) with proper upstream attribution. See [Limitations](docs/LIMITATIONS.md).

## 📜 License

Original project code: **[MIT License](LICENSE)** · © 2026 suibianba12138. Third-party code, FFmpeg builds and datasets retain their own terms.

---

<div align="center"><sub>Blind Audio Watermarking · Digital Signal Processing · Reproducible research software with explicit limits.</sub></div>
