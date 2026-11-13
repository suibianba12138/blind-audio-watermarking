# Audio Watermarking — DSP Course Project

A digital audio watermarking system built for a **Digital Signal Processing course project**. The current implementation focuses on **reference-assisted multiband watermarking**: embedding information in music with limited distortion, then recovering it after ordinary audio processing.

**Current course release:** [C2/C3 source, examples, audio and evidence](course_release/) · [中文说明](README_ZH.md) · [Version archive](archive/README.md)

> **Detection contract:** the receiver uses the corresponding **unwatermarked original audio** and the selected key. This is **non-blind, reference-assisted detection**. The receiver is **not** given the expected message. It is a classroom prototype for information retention and controlled distribution tracking, not a security or copyright-proof service.

## What the system does

```text
Original audio + message + key
           |
 Frame-wise FFT / keyed chip allocation / multiband energy modulation
           |
     Watermarked audio
           |
    MP3 / AAC / volume / resampling
           |
 Received audio + original reference + key
           |
 Alignment / reference spectral difference / chip aggregation / presence check
           |
    Recovered message or UNKNOWN
```

Two operating modes share this signal-processing approach but prioritize different needs:

| Mode | Six-second payload | How 72 seconds is used | Independent information |
| --- | --- | --- | --- |
| **Robust ID — C2** | 8 bits | Four bytes of a 32-bit ID repeated over three 24 s cycles | **32 bits**, repeated for redundancy |
| **High capacity — C3-16** | 16 bits | Twelve different 16-bit blocks | **192 bits** |

The C2 repeated-ID layout occupies twelve eight-bit blocks (96 transmitted bits), **not 96 independent identity bits**. Both modes use an original-audio reference for detection.

## Demonstration: one continuous recording

The included curated example uses 72 seconds of **Where You Are Now** by Benjamin Orth (featuring Wolf Fly), distributed under **CC BY 3.0**. The original recording, actual watermarked WAV, full-file MP3 and AAC encodes, plots and sample-level data are in [the selected showcase](course_release/media/selected_c3_16_showcase/). See [attribution and modifications](course_release/THIRD_PARTY_NOTICES.md).

- **C3-16:** twelve independent 16-bit blocks, **192 bits** over 72 seconds.
- **Selected recording:** Clean WAV, MP3 128 kbps and AAC-LC 128 kbps each recovered **12/12 blocks** and the complete message.
- **Audio quality:** embedding SNR 45 dB for this prepared example; no formal subjective listening study.
- **Further processing on this selected recording:** MP3→AAC, −6 dB, +3 dB and 48→44.1→48 kHz also recovered the complete message.

This is **one deliberately selected demonstration**, not a measured success rate over arbitrary music.

## Evaluation: different sources, different conclusions

| Protocol | Clean | MP3 128 kbps | AAC-LC 128 kbps |
| --- | ---: | ---: | ---: |
| C2, 60-source locked evaluation | 60/60 | 59/60 | 57/60 |
| C3-16, 120-source independent evaluation | 120/120 | 120/120 | 103/120 |
| C3-16, selected 72 s music (blocks) | 12/12 | 12/12 | 12/12 |

Counts denote **correctly accepted messages/blocks** in the stated protocol. In C3-16's independent AAC evaluation, **11/120 incorrect messages were accepted** and 6/120 returned UNKNOWN. In a separate 10-file development set of mixed 72-second recordings, complete C3-16 message recovery was **2/10 for AAC** and **6/10 for MP3→AAC**. These limitations matter: the curated music example does not establish universal AAC robustness.

The C2 repeated 32-bit ID was correctly fused in **20/20** mixed 72-second recordings under each of Clean, MP3 and AAC, using its own evaluation protocol. Do not compare that directly with the 192-bit full-message criterion.

For threshold, negative-case and dataset details, see [Evidence Summary](course_release/EVIDENCE_SUMMARY.md).

## Run the current course release locally

Requirements: **Python ≥ 3.10**, NumPy, SciPy; install **FFmpeg** separately for MP3/AAC.

```bash
git clone https://github.com/suibianba12138/blind-audio-watermarking.git
cd blind-audio-watermarking/course_release
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
```

Example: embed a sixteen-bit message in the first six seconds of the included reference audio, save it and detect from the saved file:

```bash
python examples/embed_detect_6s.py \
  --mode c3-16 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message A7C3 \
  --key course-demo-public-v1 \
  --output /tmp/course-watermarked.wav
```

The 72-second scripts and real FFmpeg transcode helpers are documented in [course_release/README.md](course_release/README.md). **The public demonstration key is different from the frozen evaluation key**: rerunning a published showcase file with the demo key is not a valid reproduction of its historical detection record.

## Project layout

| Path | Role |
| --- | --- |
| [`course_release/`](course_release/) | **Current** C2/C3 implementation, executable examples, tests, evidence, selected audio |
| [`archive/`](archive/) | Historical version guide and preserved README snapshots |
| [`src/`](src/), [`app/`](app/) | **Legacy V3** implementation and online-demo code; kept for compatibility |
| [`docs/`](docs/) | Historical V2/V3 documents and existing V4-oriented static site |
| [`upgrade/v4-github-prep`](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113) | Archived V4 neural studio; separate third-party-model approach |

## Historical versions and websites

The project explored several approaches before selecting the course-final C2/C3 system. Prior work remains available, but **does not share the same detection contract or evaluation protocol**:

- [**V2** — fixed-label identity watermark](archive/v2/README.md): four labels; historical 32-bit redundant codewords carry **2 information bits**.
- [**V3** — blind FFT/QIM + Soft-Code](archive/v3/README.md): 8-bit payload; [read-only snapshot branch](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v3-legacy-20261113).
- [**V4** — neural blind watermark Studio](archive/v4/README.md): 40-bit Sony SilentCipher-based work (pretrained third-party model); [archived code snapshot](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113), [historical Draft PR #5](https://github.com/suibianba12138/blind-audio-watermarking/pull/5).

**Website/deployment status:** [shengkaini.com/blind-audio-watermarking](https://shengkaini.com/blind-audio-watermarking/) still displays the **historical V4** site, and [the Render demo](https://blind-audio-watermarking-demo.onrender.com/) remains **V3**. Neither is the new C2/C3 online calculator. Their redesign/deployment is a separate step; this GitHub release does not silently update them.

## Attribution and limitations

Original course code: [MIT License](LICENSE); release package also includes [license](course_release/LICENSE), [third-party notices](course_release/THIRD_PARTY_NOTICES.md) and [source provenance](course_release/SOURCE_PROVENANCE.json). The sample music is **CC BY 3.0**, not MIT. Frozen experimental keys, third-party neural weights and private experimental workspaces are not published.

The design assumes a matching original reference and an aligned, substantially intact recording. It does not establish arbitrary-crop detection, intentional watermark attack resistance, large-scale source identification or cryptographic proof of origin.

*DSP course project · 2026 · Reference-assisted multiband audio watermarking*
