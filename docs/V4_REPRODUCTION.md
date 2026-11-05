# V4 Reproduction and Third-Party Model Notes

## Runtime configuration

The validated local Studio used Python 3.12, CPU-only PyTorch 2.14.0, Gradio 4.44.1, FFmpeg 6.1.1, and Sony SilentCipher 1.0.4 source. The official repository requirements specify `torch<=2.0.0`; the tested runtime is therefore empirical compatibility evidence, not an upstream-supported version combination. No GPU is required for the tested single-worker workflow. Approximate peak process memory was 1.5–1.7 GiB in prior local runs; startup and inference time vary with CPU and filesystem cache.

The official source and model archive remain outside this repository. Before starting, provide:

- `SILENTCIPHER_SOURCE_ROOT`: a local checkout of `https://github.com/sony/silentcipher` (P0 source commit `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10`).
- `SILENTCIPHER_MODEL_DIR`: the official 44.1 kHz `73999_iteration` directory containing `hparams.yaml` and checkpoint state files.
- `V3_SOURCE_ROOT`: the repository root with the frozen V3 public API. For an integrated checkout, this is the repository root; a separate frozen V3 checkout can also be used.

The app binds to `127.0.0.1`, uses no model-download fallback, and does not enable Gradio sharing. Generated audio/cache files are local-only and ignored by Git.

## Model and weight provenance

- Official repository: [sony/silentcipher](https://github.com/sony/silentcipher)
- Code license: the official repository includes an MIT license.
- Official release: [release / Models.tar.gz](https://github.com/sony/silentcipher/releases/tag/release), a 64,389,731-byte archive in the audited release metadata.
- Audited release/source: repository commit `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10`; the P0 record has the local archive and checkpoint SHA-256 values.
- **Weight licensing:** the repository license covers source code, but the audited release did not provide a separate clear weight license or an upstream asset digest. This project does not redistribute the archive or checkpoint files. Users should review the source and release terms before use or redistribution.

The adapter uses the official 44.1 kHz model interface and frozen 40-bit message format. It does not change the checkpoint or model parameters. Presence is decided separately from the official decode status; the current SilentCipher score threshold remains provisional.

## Channels and evidence

The Studio Channel Lab uses FFmpeg for actual MP3 128 kbps and AAC-LC/M4A 128 kbps encode/decode operations. For Studio-generated M4A, the decoder uses container timing metadata and trims only known trailing frame padding. It does not unconditionally discard 1,024 samples from externally uploaded AAC/ADTS files. Channel support is not a robustness guarantee.

Historical reports and machine-readable records are archived under [`reports/v4`](reports/v4) and [`../experiments`](../experiments). The original local experiment workspace retains raw data; this public preparation includes text records only and excludes audio assets, model weights, and local environment directories. Reports were scrubbed of machine-specific absolute paths before inclusion.

Selected evidence, with the protocol boundaries preserved:

- P9: 12 independent sources, two messages per source. Correct accepted recovery: clean 24/24; MP3 24/24; AAC/M4A exact raw decode 24/24 and correct accepted 23/24. One correct AAC message fell below the frozen threshold. No wrong accepted message was observed in this set.
- P4 selected demo clips: 4 sources × clean/MP3/AAC yielded 12/12 accepted. It was still marked PARTIAL because browser validation and human listening review were incomplete.
- Earlier P1/P3/P7 results include failures and the original ADTS priming issue. They are not replaced by P8/P9 and should be read with their individual protocols.

These samples support bounded engineering conclusions only. They do not establish a formal false-acceptance rate, broad generalization, or SOTA performance.

## Reproduction steps

Create a dedicated Python 3.12 environment, install the Studio dependencies in `requirements-v4.txt`, install a CPU PyTorch build, and obtain SilentCipher source/weights from the official links above. Check the upstream dependency requirements before installation; do not install into a robotics or V3 environment. Then, from the repository root:

```bash
export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher
export SILENTCIPHER_MODEL_DIR=/path/to/official/44_1_khz/73999_iteration
export V3_SOURCE_ROOT="$PWD"
export V4_STUDIO_PYTHON=python
bash scripts/run_v4_studio.sh
```

The studio should be available at `http://127.0.0.1:7862`. For this archived local stack, do not bind to a public interface. Gradio 4.44.1 was the version used in P4 runtime checks; the app has not been security-upgraded and revalidated for public exposure.

Run the selected unit suite with the command in the root README. End-to-end model tests additionally require the external source and checkpoints.
