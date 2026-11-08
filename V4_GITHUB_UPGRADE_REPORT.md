# V4 GitHub Repository Upgrade — Local Preparation Report

**Audit date:** 2026-11-06 (UTC/GitHub state checked live)\
**Remote writes:** none. No push, release, or remote ref update was performed.\
**Local preparation:** `upgrade/v4-github-prep`, based on the fetched current `origin/main` at `1641cebc327a0e9efbf5ee1d1baec0baeb706555`.

**V4 content commit:** `6ff723c9c0bc5b1f40aad2ca8507c8f8e77f59a7` (local only).

## 1. Existing repository and version history

Remote URL: `https://github.com/suibianba12138/blind-audio-watermarking.git`. The repository is public; the live GitHub API identifies `main` as the default branch. A fresh fetch was performed into the V4 checkout's remote-tracking refs before preparing the local branch.

The current remote `main` is **not** the initial V3-only snapshot. It points to merge commit `1641cebc` (“Merge V3 8-bit Soft-Code with Legacy and updated safe Gradio runtime”). It descends from the initial release `a89b493` and includes hosted-demo/site work and V3 integration. The live branch heads observed were:

| Remote branch | Head | Meaning observed |
|---|---|---|
| `main` | `1641cebc` | Current default; V3/hosted integration tree |
| `feat/v3-8bit-integration` | `7fe6782` | Frozen original V3 8-bit integration snapshot |
| `feat/v3-safe-hosted-integration` | `35df70e` | Safe hosted V3 integration work |
| `feat/hosted-audio-demo` | `51ec62e` | Hosted demo work |
| `feat/render-live-website-integration` | `93c8696` | Render/site integration |
| `feat/website-readme-v1` | `5bf977a` | Website/readme work |
| `feat/audio-studio-visual-redesign` | `a0bae20` | Audio Studio visual work |

The V2 public snapshot is the initial-release commit `a89b4935ec056a6709cc17379e333a9b1f7c387e`; its committed README identifies the Course V2 baseline. The frozen V3 source commit is `7fe678234e8af1d0be34a0a3e56297c7182945ff`. It remains available on the existing remote `feat/v3-8bit-integration` branch. A local-only `legacy/v3` branch was also created at that exact commit for clear local access; it has not been pushed.

The live repository reported no tags and no Releases. No retrospective V2/V3 tag was invented. Version preservation therefore relies on the existing V3 remote branch and immutable commit history; V2 remains addressable by its verified commit.

## 2. Local/remote history relationship and integration strategy

The V4 research checkout is not an unrelated Git repository: its ancestry and the remote repository share the `a89b493` base. However, its `research/v4-p0` line diverged from current `main` at that point. A test merge against current `main` produced conflicts in README and several V3/hosted files. The V4 research line also contains committed P0 environment evidence with machine-specific paths. Merging that line wholesale would add unnecessary conflicts and carry those paths into public history.

The prepared branch is consequently a **curated content migration on top of the latest remote `main`**, not a history rewrite and not an unrelated-history merge. It leaves the original `research/v4-p0`, V3, V2, and main histories intact. Only reviewed V4 source, sanitized text records, documentation, and selected tests are added. This retains the public V2/V3 ancestry while avoiding upload of unreviewed local P0 commits.

Proposed eventual integration is a PR from `upgrade/v4-github-prep` to `main`. At the time of preparation, the branch starts directly from the current `main`, so the content change is a normal fast-forwardable continuation if no remote commits intervene. No PR or push is created in this round.

## 3. Prepared V4 layout

The integration candidate keeps the existing V2/V3 tree and adds the V4 Studio in place:

- `app/silentcipher_adapter.py`, `app/v4_audio_processing.py`, `app/v4_backends.py`, `app/v4_studio_gui.py`, and `app/v4_tempfiles.py` — current P4 backend, DSP/channel and GUI runtime.
- `scripts/run_v4_studio.sh` — local launcher. External source/model paths remain environment configuration, not repository constants.
- `requirements-v4.txt` — isolated local Studio dependency set, separate from the existing V3/hosted requirements.
- `docs/V4_REPRODUCTION.md` — model provenance, environment, setup, and evidence boundaries.
- `docs/reports/v4/` — P0–P11, adaptive, and end-to-end reports, plus the P0 notes.
- `experiments/v4_*/` — text-only result records/manifests and separately labeled experimental prototypes. Adaptive and P5 decoder prototypes are outside the production `app/` path and are not activated by the Studio.
- `tests/` — adapter and P4 integration tests selected for the published runtime.

P2's former standalone GUI, diagnostic helper, and tests are archived below `experiments/v4_p2/prototype/`; they are not presented as a second production entry point. The original V4 research workspace and its unmodified experiment files remain intact.

## 4. README and evidence claims

Both `README.md` and `README_ZH.md` now lead with **Robust Audio Watermarking Studio** and describe the dual-backend architecture, four Studio tabs, local setup, external model requirements, version history, and limitations. SilentCipher is explicitly attributed to Sony; the project does not claim to have authored that model.

The public summary reports the bounded P9 figures with their protocol and limitations: 12 sources × two messages, clean and MP3 correct accepted 24/24, AAC/M4A raw exact 24/24 and correct accepted 23/24, with one correct low-score message rejected. It also identifies the P4 4-source demo result as a selected demonstration and retains its `PARTIAL` status due to incomplete browser/audio-listening acceptance. These are not described as SOTA, formal FAR, or generalization guarantees.

The SilentCipher source repository includes an MIT license, but the audited `Models.tar.gz` release asset did not supply a separate explicit weight license or a digest in GitHub release metadata. The 64,389,731-byte official archive and checkpoint files are not included. The README asks users to review upstream terms. No Sony source tree is vendored.

## 5. Public-upload safety audit

The curated candidate was checked before staging:

- No audio (`wav/mp3/m4a/flac/ogg`) or model-weight (`ckpt/pt/pth/safetensors`) file is present in the added V4 candidate.
- The original end-to-end WAVs, codec files, A/B listening files, model archive, and checkpoints were left in their original local locations and not copied.
- `experiments/v4_p0/ENVIRONMENT_AUDIT.json` was excluded from the public candidate because it contains host/runtime inventory. Existing experiment records remain in the original workspace.
- Added text files were scanned for credential-like tokens and machine-specific `/home`, `/mnt`, or user workspace paths; no hits remained in the curated additions. Generic `/tmp/...` command examples already present in the inherited remote V3 documentation/workflow are not machine-specific paths and were not altered.
- `.gitignore` now explicitly excludes local `.env`, model/checkpoint folders, weight extensions, and V4 input/output/listening directories. Existing media ignore rules remain.
- Public text records contain protocol metadata, source identifiers/hashes, license/source references, model/checkpoint hashes, and aggregate/per-trial measurements. They contain no audio payload. Reports were path-scrubbed for this candidate; originals in the separate research checkout were not edited.
- The curated added V4 files total about 3.1 MB; the complete prepared worktree is about 4.1 MB. The largest added experiment record is a text JSON sync diagnostic. No large dataset or model binary is included.
- The separate public-release checkout's pre-existing modified files, untracked approval document, and `.aws` directory were not read, staged, or changed during this preparation.

### Dependency/security caveat

The runtime-tested V4 UI pins Gradio 4.44.1. This is acceptable only for the existing loopback-only local workflow. GitHub's official advisory records a blocked-path ACL issue affecting Gradio versions below 5.6.0, and the maintainers state they support security fixes in the latest release rather than backporting them. The V4 app has not been upgraded and revalidated on a patched current Gradio version. Thus **public network deployment is not ready**; before such use, upgrade the UI stack and rerun the functional and file-isolation checks. Sources: [Gradio GHSA-j2jg-fq62-7c3h](https://github.com/gradio-app/gradio/security/advisories/GHSA-j2jg-fq62-7c3h) and [Gradio security policy](https://github.com/gradio-app/gradio/security).

## 6. Validation performed

### Tests

The prepared integration branch ran the selected adapter/audio/backend/PCM-safety suite under the existing isolated Python 3.12 runtime: **19 passed**. That environment did not contain pytest and package installation was blocked by network policy, so the installed pure-Python pytest runner from the local Python 3.13 environment was exposed through a temporary `/tmp` symlink-only tools directory, with plugin autoload disabled. Runtime dependencies (NumPy, SciPy, SoundFile, Gradio, Torch) remained the Python 3.12 environment's packages. No V3/robotics environment was changed.

### Studio startup

The prepared launcher started the actual Gradio Blocks app on `127.0.0.1` using the already-present official source/checkpoint paths. A local HTTP request returned status 200 and the Studio title; the process was then terminated cleanly. The app loads the model lazily, so this verifies startup/import/page health, not a fresh inference run. P4/P9/E2E reports retain the earlier actual embed, codec, independent re-upload, and blind-detection runtime evidence. No new browser visual check was claimed.

### Git and content checks

- The integration worktree began at the fetched `origin/main` head `1641cebc`; no force operation or remote write occurred.
- No tracked V3 algorithm/configuration or Render deployment file was modified by the prepared V4 changes.
- V2/V3 historical files remain present in the tree; source-level P4 V3 calls remain through the narrow existing API.
- The exact staged file list and commit identity are recorded in the local Git state. The original V4 experiment workspace was not cleaned or rewritten.

## 7. Planned refs and expected effect on GitHub

| Ref | Local state | Future action |
|---|---|---|
| `upgrade/v4-github-prep` | Local integration branch based on `1641cebc` | Push only after review; open PR to `main` |
| `legacy/v3` | Local alias at `7fe6782`; remote equivalent already exists as `feat/v3-8bit-integration` | No new public alias is required; push only if a clearer compatibility ref is later requested |
| V2 snapshot | Verified commit `a89b493` | No new tag required |
| Releases/tags | None observed | No release/tag created in this round |

Expected `main` effect after a future reviewed merge: add V4 files, V4 README/reproduction docs, and selected sanitized V4 records while retaining existing V2/V3/hosted history and files. No current main file was deleted by this candidate. The public integration should wait on a Gradio security upgrade/revalidation decision; this report is local preparation, not publication approval.

## 8. Summary

Local preparation is complete on a branch rooted in the live remote history. The branch preserves the current public repository lineage, a local exact V3 reference exists, and V4 files have been organized with audio/weight/path exclusions. The core local test suite and Studio startup check passed. Public upload remains deferred as requested; a Gradio update and validation is the main release blocker, with checkpoint weight licensing still unresolved for redistribution (the weights are excluded).
