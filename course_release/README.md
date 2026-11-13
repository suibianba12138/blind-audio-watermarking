# DSP Audio Watermarking Course Release

This folder packages the frozen reference-assisted C2 and C3 DSP modes, small command-line examples, tests, a selected licensed C3-16 music case, and a concise evidence summary. It does not include training data, model checkpoints, Python environments, or the full experiment workspace.

## Modes

| Mode | Payload | Long-audio use | Detector information |
|---|---:|---|---|
| C2 Robust | 8 bits / 6 s | Robust per-block messages | Requires the corresponding unwatermarked reference |
| C2 Long-ID | One 32-bit identity | Same four ID bytes repeated three times across 72 s | Repeated identity, not 96 independent bits |
| C3-16 High-Capacity | 16 bits / 6 s | Twelve independent blocks carry 192 bits over 72 s | Requires the corresponding unwatermarked reference |

C2 and C3 are **reference-assisted, non-blind** methods. A decoder estimates the message without receiving the target message, then an independent presence threshold decides `IDENTIFIED` or `UNKNOWN`. This package is a course demonstration, not a cryptographic authentication system.

## Install and smoke test

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
```

The public demo key in `configs/demo.example.json` is intentionally different from the frozen evaluation keys. The packaged source requires an explicit key, so no frozen key is distributed. Smoke tests use the included licensed music excerpt and do not reproduce the locked-test scores.

## Six-second embed and readback detection

```bash
python examples/embed_detect_6s.py \
  --mode c2-8 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message A7 \
  --key course-demo-public-v1 \
  --output /tmp/c2-marked.wav

python examples/embed_detect_6s.py \
  --mode c3-16 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message A7C3 \
  --key course-demo-public-v1 \
  --output /tmp/c3-marked.wav
```

The example writes float32 WAV, closes it, reads it back, and then detects against the original reference. The expected message is used only to score the recovered result after detection.

## 72-second payload layouts

The payload layout helpers are available in `examples/payload_layout.py`:

- C2 Long-ID splits a 32-bit identity into four byte messages and repeats those four bytes three times across twelve six-second blocks.
- C3-192 splits a 192-bit value into twelve independent 16-bit block messages.

`examples/embed_detect_72s.py` embeds and verifies a float32 readback from a 72-second, 48 kHz WAV. It reports block-level decisions and a fused payload. It does not run a codec or claim that the demo key reproduces frozen results.

```bash
python examples/embed_detect_72s.py \
  --mode c2-long-id \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message 12345678 \
  --key course-demo-public-v1 \
  --output /tmp/c2-long-id.wav

python examples/embed_detect_72s.py \
  --mode c3-192 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message D42DEE6FA235F3C07531FD862283452DCB56FF6A8F621E41 \
  --key course-demo-public-v1 \
  --output /tmp/c3-192.wav
```

## Real FFmpeg encoding

`examples/transcode_ffmpeg.py` invokes FFmpeg to encode WAV to MP3 at 128 kbps or AAC-LC/M4A at 128 kbps. It can also decode the encoded file back to float32 WAV:

```bash
python examples/transcode_ffmpeg.py marked.wav marked.mp3 --codec mp3 --decode-to marked_mp3_decoded.wav
python examples/transcode_ffmpeg.py marked.wav marked.m4a --codec aac --decode-to marked_aac_decoded.wav
```

FFmpeg must be installed separately. The script uses real FFmpeg encoding and decoding; it does not simulate codec effects.

## Results and limits

Read `EVIDENCE_SUMMARY.md` for the frozen C2 Locked Test, repeated 32-bit Long-ID, C3-16 independent evaluation, and the separate selected single-track showcase. The single-track 12/12 result is a selected demonstration and is not a population reliability claim. C3-16 AAC errors in the independent evaluation are retained.

## Selected music

The `media/selected_c3_16_showcase/` folder contains one licensed 72-second C3-16 case: Original/WAV, Watermarked/WAV, whole-file MP3, whole-file AAC/M4A, the 192-bit message, actual detection figures, and figure source CSVs. See `THIRD_PARTY_NOTICES.md` for attribution and license.
