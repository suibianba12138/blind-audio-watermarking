# V4 Reproduction and Third-Party Model Notes

## Runtime configuration

The earlier full neural Studio acceptance used Python 3.12, CPU-only PyTorch 2.14.0, Gradio 4.44.1, FFmpeg 6.1.1, and Sony SilentCipher source commit `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10`. The 2026-11-07 release-preparation run used an isolated Python 3.13.5 environment with PyTorch 2.14.0+cpu, Gradio 6.31.0 and its resolved `gradio_client` 2.7.2 dependency. It passed 79 automated tests, launched the live Blocks app, and exercised upload/download plus real MP3/AAC and aligned analysis callbacks. One saved licensed native-44.1-kHz music excerpt was freshly embedded with a new 40-bit message; Clean, MP3 and AAC/M4A files were independently re-uploaded and correctly identified. An unwatermarked version returned `UNKNOWN`; malformed audio returned a safe `DECODE_ERROR`. This is a one-source release smoke, not a new performance estimate. Browser visual/click-through QA remains pending because the host's Snap/AppArmor setup prevents launching the installed browsers. The official repository requirements specify `torch<=2.0.0`; the tested Torch 2.14.0 runtime is empirical compatibility evidence, not an upstream-supported version combination. No GPU is required for the tested single-worker workflow; measured Studio peak RSS was about 1.56 GiB.

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

Create a dedicated Python environment compatible with Gradio 6.31.0 and the selected CPU PyTorch build, install `requirements-v4.txt`, install CPU PyTorch separately, and obtain SilentCipher source/weights from the official links above. `requirements-v4.txt` includes the audio, plotting, and SilentCipher runtime libraries used by the Studio. Gradio resolves its matching client and web stack; do not add legacy direct pins for those transitive dependencies. Check upstream dependency terms before installation; do not install into a robotics or V3 environment. Then, from the repository root:

```bash
export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher
export SILENTCIPHER_MODEL_DIR=/path/to/official/44_1_khz/73999_iteration
export V3_SOURCE_ROOT="$PWD"
export V4_STUDIO_PYTHON=python
bash scripts/run_v4_studio.sh
```

The studio should be available at `http://127.0.0.1:7862`. Do not bind to a public interface. The current requirements pin Gradio 6.31.0; local service, upload/file components, event registration, real MP3/AAC channel callbacks, Signal Analysis, and a fresh one-source neural Clean/MP3/AAC re-upload cycle were smoke-checked with that version. Browser-level visual QA and larger regression sampling remain separate. The Studio is for localhost use and has not received a separate network-exposure security review.

Run the selected unit suite with the command in the root README. End-to-end model tests additionally require the external source and checkpoints.
