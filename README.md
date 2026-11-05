# Robust Audio Watermarking Studio

A local-first course project for blind audio watermarking with two distinct backends: Sony's third-party pretrained SilentCipher model and the repository's frozen V3 DSP baseline. The V4 Studio combines audio processing, real codec round trips, blind detection, and signal analysis in one Gradio Blocks application.

> SilentCipher is an external model by Sony Research. It is not an original model created by this project. Its official code is MIT licensed; the published checkpoint archive does not include a clear standalone weight license notice. The weights are therefore not bundled or redistributed here.

## What V4 provides

- **Watermark:** SilentCipher, 40-bit (five bytes), mono 44.1 kHz / 12 s; or frozen V3, 8-bit, mono 48 kHz / 6 s.
- **Channel Lab:** actual FFmpeg MP3 128 kbps and AAC-LC/M4A 128 kbps round trips, seeded additive noise, and fixed crop. A transform being available does not mean the watermark is robust to it.
- **Blind Detection:** a separate received-file upload and backend-specific presence policy. SilentCipher's current threshold remains provisional; the decoder never receives the expected message or embed session.
- **Signal Analysis:** aligned waveforms, STFT magnitude and difference plots, SNR, LSD, and audio metadata. Metrics are withheld when alignment is not credible.
- CPU-first execution, model singleton, bounded single-worker queue, local-only binding, upload and duration limits, and expiring temporary artifacts.

## Evidence snapshot

The results below are bounded engineering checks, not an SOTA claim or a population-level guarantee.

- P9 tested 12 independent sources with two fixed messages per source. Correct accepted recovery was 24/24 for clean WAV and 24/24 for MP3 128 kbps. AAC/M4A produced 24/24 exact raw decodes and 23/24 correct accepted detections; one fully correct message was rejected by the frozen provisional threshold. No accepted wrong messages were observed in those trials. The source-level sample is small and is not a formal false-acceptance estimate.
- P4's four selected demo clips (two music, one speech, one environment) each passed clean, MP3, and AAC/M4A blind re-upload checks (12/12). The acceptance remains **PARTIAL** because browser-level validation and human A/B listening were not complete in that acceptance run.
- Earlier P1/P3 failures, the AAC ADTS priming diagnosis, and the corrected M4A protocol remain in the archived reports. The reports retain negative evidence and protocol differences.

See [`docs/reports/v4/`](docs/reports/v4/) and [`experiments/`](experiments/) for reports and sanitized text records. Audio samples, generated outputs, checkpoints, and model archives are excluded.

## Local setup

Use a dedicated Python 3.12 environment. Do not install these packages into the V3/robotics environment. The integration was exercised with CPU-only PyTorch 2.14.0, Gradio 4.44.1, FFmpeg 6.1.1, and Sony's SilentCipher 1.0.4 source. The tested combination differs from SilentCipher's published `torch<=2.0.0` requirement, so treat it as an empirically working local combination rather than an upstream-supported matrix.

1. Install FFmpeg with `ffprobe` and `libmp3lame` / AAC support.
2. Create and activate a dedicated Python 3.12 virtual environment.
3. Install the Studio packages listed in [`requirements-v4.txt`](requirements-v4.txt), then install a compatible CPU PyTorch build in that environment.
4. Obtain the official SilentCipher source and 44.1 kHz checkpoint from the [Sony repository](https://github.com/sony/silentcipher) and its [official release](https://github.com/sony/silentcipher/releases/tag/release). Review the upstream terms before downloading or using the checkpoint. Do not place model files in this repository.
5. Configure the external paths and launch locally:

```bash
export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher
export SILENTCIPHER_MODEL_DIR=/path/to/official/44_1_khz/73999_iteration
export V3_SOURCE_ROOT="$PWD"
export V4_STUDIO_PYTHON=python
bash scripts/run_v4_studio.sh
```

Open `http://127.0.0.1:7862`. The app does not enable Gradio sharing. Keep it on localhost; the pinned Gradio 4.44.1 runtime is the version used for local verification and has not been security-upgraded/revalidated for public exposure. Review current upstream advisories before any network-facing deployment.

Detailed provenance, model files, CPU notes, and reproduction caveats are in [`docs/V4_REPRODUCTION.md`](docs/V4_REPRODUCTION.md).

## Tests

Install the development test dependency from `requirements-v4-dev.txt`, then run the suite below.

```bash
python -m pytest tests/test_silentcipher_adapter.py tests/test_v4_p4_audio_processing.py tests/test_v4_p4_backends.py tests/test_v4_pcm16_peak_safety.py
```

These are local code tests. Full model-runtime checks additionally require external SilentCipher source and weights.

## Historical versions

- **Course V2 release snapshot:** [`a89b493`](https://github.com/suibianba12138/blind-audio-watermarking/tree/a89b4935ec056a6709cc17379e333a9b1f7c387e), preserved in repository history.
- **Frozen V3 8-bit integration:** [`feat/v3-8bit-integration`](https://github.com/suibianba12138/blind-audio-watermarking/tree/feat/v3-8bit-integration) at `7fe678234e8af1d0be34a0a3e56297c7182945ff`.
- The current repository `main` already contains the V3 integration and hosted-site history. V4 is prepared as a fast-forwardable continuation of that current history; no history is rewritten.

## License and attribution

This repository's project code is MIT licensed. Sony SilentCipher code is third-party MIT-licensed code; its checkpoint archive is not included, and the archive's separate redistribution terms were not established during this audit. Third-party audio was used only in local tests; this repository does not redistribute audio. Experiment reports identify sources and licenses where known. Dependencies and FFmpeg retain their own licenses.
