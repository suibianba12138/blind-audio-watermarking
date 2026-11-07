# V4 GitHub Pre-Release Final Readiness

**Final status: `V4_GITHUB_RELEASE_READINESS = CONDITIONAL`**

**Review date:** 2026-11-07

**Remote writes:** none. No push, PR, merge, tag, or Release was created.

## 1. Gradio security and version selection

The official Gradio release page identified **6.31.0** as the latest release on the review date ([official releases](https://github.com/gradio-app/gradio/releases)). Gradio maintainers state that security fixes ship in the latest release and are not backported ([official security policy](https://github.com/gradio-app/gradio/security/policy)). The selected version is above the fixed versions listed in the reviewed advisories for blocked-path ACL bypass, Windows/Python 3.13 absolute path traversal, and `gr.load()` proxy SSRF ([ACL advisory](https://github.com/gradio-app/gradio/security/advisories/GHSA-j2jg-fq62-7c3h), [Windows path advisory](https://github.com/gradio-app/gradio/security/advisories/GHSA-39mp-8hj3-5c49), [SSRF advisory](https://github.com/gradio-app/gradio/security/advisories/GHSA-jmh7-g254-2cq9)).

The V4 dependency file now pins `gradio==6.31.0` and lets Gradio resolve its matching client and web stack. Stale direct pins for `gradio_client`, FastAPI, Starlette, Pydantic, and related packages were removed. Direct runtime packages used by V4 were retained or added, including librosa, PyYAML, pydub, Plotly, SciPy, and SoundFile. PyTorch remains an external CPU model-runtime install rather than a bundled dependency.

The new isolated runtime resolved Gradio 6.31.0 with `gradio_client 2.7.2`, FastAPI 0.162.0, Starlette 1.10.0, and Pydantic 2.14.3. `pip check` reported no broken requirements. No global, V3, Render, or robotics environment was changed.

Gradio 6 warned that the Studio theme argument had moved from `Blocks(...)` to `launch(...)`. A regression test was added; it failed before the change and passed after moving the theme option. No broader GUI redesign was made.

## 2. Runtime and model provenance

The upgrade acceptance environment was an isolated Python 3.13.5 venv under `/tmp`, CPU-only PyTorch 2.14.0, NumPy 2.5.4, SciPy 1.18.1, librosa 0.10.2.post1, SoundFile 0.13.1, Plotly 6.9.0, Gradio 6.31.0, and FFmpeg/FFprobe 6.1.1. `torch.cuda.is_available()` returned false.

The model source was the frozen official Sony commit `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10`. The official model archive was downloaded only to `/tmp` for this local verification; its SHA-256 matched the P0 frozen value `cd2beaa9824102c4bae5fe9de7b737cda2682b109ab5f2375a72f3303172af78`, and all three 44.1 kHz checkpoint hashes matched P0. Source and checkpoint files were not copied into the candidate worktree or committed. Their independent redistribution license remains unconfirmed, so they remain excluded from publication.

## 3. Automated and live Studio verification

The full candidate test suite passed: **79 passed in 12.20 seconds**. This includes the public/V3 suite and V4 adapter, audio processing, backend, PCM16 safety, and Gradio compatibility coverage. `git diff --check` passed.

The actual Studio launched with the repository script on loopback. Its home page returned **HTTP 200**. The live Gradio 6.31.0 configuration exposed 51 components and five named event endpoints: `backend_info`, `embed`, `channel`, `detect`, and `analyze`. `gr.File` uploads/downloads, `gr.Audio`, event callbacks, bounded queue configuration, the 16 MiB upload limit, and localhost-only launch were exercised. The app continues to use a private temporary root; it and job directories were mode 0700. The root was empty after clean shutdown, confirming exit cleanup for this run.

The test source was the existing licensed `music_01` 12-second prepared excerpt (native source 44.1 kHz, CC0 per its frozen P4 manifest). Prepared input SHA-256: `1ab6de691310639176f88dd70c9b763411169d5543c32b92484979c7c9f7a974`. A new message `C4317E90A5` was fixed for this smoke.

| Operation | Result |
|---|---|
| Fresh 40-bit embed | Completed; 4.28 s CPU, model init 0.05 s, exported-pair SNR 48.48 dB, shared peak gain 1.000000 |
| Downloaded Clean WAV, independently re-uploaded | `IDENTIFIED`, exact `C4317E90A5`, score 1.000000; detector 5.84 s |
| Same embed output → FFmpeg MP3 128 kbps → downloaded file re-upload | MP3 created in 0.16 s; `IDENTIFIED`, exact message, score 1.000000; detector 5.89 s |
| Same embed output → FFmpeg AAC-LC/M4A 128 kbps → downloaded file re-upload | M4A created in 0.21 s; `IDENTIFIED`, exact message, score 0.992063; detector 6.28 s |
| Unwatermarked original music, separate detection upload | `UNKNOWN`; candidate `F0534B2033`, score 0.369048, below frozen 0.680556 threshold |
| Invalid 40-bit text | Safely rejected with the five-byte/hex format message before model inference |
| Malformed WAV upload | `DECODE_ERROR`, safe “unable to read audio information” response; no traceback or local path returned |
| Signal Analysis | Three plots returned; aligned SNR 48.47 dB, LSD 3.537 dB, lag 0.0000 s, 12.00 s compared |

The detector requests received only the uploaded received file and backend selection. The message was used only by the embed endpoint; it was not passed to detection. These are one-source release smoke results, not a new robustness estimate or false-acceptance claim.

Output SHA-256: watermarked WAV `e10fe5242b3ec371a8bf7d91dd43476f3b8c44998c5548c5951f040d93afd421`; MP3 `df9a460fa462c11d0fb358edaf5a2f811bb94343c70cd9c637c96710635144ac`; AAC/M4A `875fcc14a03101e5a44c64641e9dbfb3aae72b4e34c524397667466ba31b90d3`.

During the live server run, `/usr/bin/time -v` measured **1,635,300 KiB peak RSS** (about 1.56 GiB). The server ran 1:44 wall time including startup, embed, four detections, channel round trips, analysis, uploads, and downloads. CPU detection times above are the callback-reported model times; this wall time is not a per-request benchmark.

## 4. Browser check and manual checklist

Browser-level visual and click-through QA was **not completed**. The installed Chromium Snap launcher refused to start because the host Snap confinement service rejected its setup; Firefox Snap could not create its runtime directory because the required runtime path is read-only. Per the bounded scope, no browser stack was installed or repaired. The live HTTP/API callback checks above are not represented as browser interaction.

Manual browser acceptance checklist for the next available desktop/browser session:

1. Open the local URL and confirm the four tabs and upload controls render without console errors.
2. In Watermark, upload a licensed music file, embed a 40-bit message, play both returned audio files, and download the watermarked WAV.
3. In Channel Lab, upload that downloaded WAV, create MP3 and AAC/M4A, play and download each result.
4. In Blind Detection, separately upload the downloaded Clean, MP3, and AAC/M4A files and confirm each state/message; upload the original and confirm `UNKNOWN`.
5. In Signal Analysis, upload reference and watermarked files and view waveform, STFT, and spectral-difference plots and aligned metrics.
6. Try malformed audio and an invalid message and confirm the sanitized errors remain visible.

## 5. Public-file and Git audit

- The current remote `main` was fetched read-only and remains `1641cebc327a0e9efbf5ee1d1baec0baeb706555`.
- The candidate branch remains rooted in that history. The prepared branch has the prior two local commits and this finalizer adds only V4 README/reproduction/dependency/UI compatibility/test/report updates.
- No V2/V3 source, frozen V3 algorithm/configuration, P0–P11 results, SilentCipher weights, Render service files, or online services were changed by this task.
- The candidate contains no WAV/MP3/M4A/FLAC audio, checkpoint/weight files, or archive files. No added file exceeds 10 MiB. The text changes were scanned for machine-specific `/home/nsk` and `/mnt` paths; none were found. No credentials were added. Temporary runtime audio/model files were kept outside Git under `/tmp`.
- Path-handling review confirmed callback inputs pass through `_safe_path` size/existence checks, output names are constrained by `ArtifactStore.checked_path`, the Studio upload/output cache stays under the mode-0700 run root, and Gradio returns only explicit callback outputs. This was a bounded local review, not an adversarial path-traversal penetration test; keep the Studio bound to localhost.
- V2 remains reachable at verified commit `a89b4935ec056a6709cc17379e333a9b1f7c387e`. V3 remains reachable at `feat/v3-8bit-integration` commit `7fe678234e8af1d0be34a0a3e56297c7182945ff`; local alias `legacy/v3` points to the same commit. No tags or Releases were created.

### Planned publication path

- Push candidate: `upgrade/v4-github-prep` only after human review.
- Planned PR: `upgrade/v4-github-prep` → `main`.
- Expected `main` effect: update the project README to lead with V4, add reviewed V4 code/docs/tests and current V4 requirements, while retaining all pre-existing V2/V3 commits and files in normal Git history. No force push or history replacement is part of this plan.
- This round made no remote changes. No PR or Release exists yet.

## 6. Decision

`V4_GITHUB_RELEASE_READINESS = CONDITIONAL`

The Gradio upgrade, full automated suite, live local service, real SilentCipher embed and blind Clean/MP3/AAC checks, negative case, malformed-input handling, file lifecycle, and Signal Analysis smoke all passed. The remaining condition is browser visual/click-through QA, which could not run because the installed browser launchers were unusable in this host session. Checkpoint weight redistribution terms also remain unconfirmed; the candidate excludes the weights and documents them as user-supplied external runtime files. The local candidate is prepared for review, but no remote operation was performed.
