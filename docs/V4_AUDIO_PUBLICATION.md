# Publishing verified V4 audio to the GitHub Pages listening panel

The public listening panel is already integrated in `docs/index.html`, but its playback controls stay inactive until **actual, hash-matched P4 exports** are committed. The frozen audio files are not in GitHub and cannot be recreated faithfully from the published reports alone.

## Eligible media

Only the two P4 **FMA CC0** music recordings are selected for this website: `music_01` (Sax & Piano) and `music_02` (Free To Use). Each track needs four files: original prepared WAV, SilentCipher watermarked WAV, the actually tested MP3, and the actually tested AAC/M4A. Eight files in total. The music excerpts are 12 s each; they are not synthetic placeholders.

The exact filenames, byte counts and SHA256 digests are frozen in `scripts/publish_v4_audio.py` and cross-validated against the original V4 file `experiments/v4_end_to_end_acceptance/results.json`. The published manifest is `docs/assets/v4-audio/manifest.json`.

**Do not** regenerate approximate watermarked audio, use a different checkpoint, or substitute newly encoded MP3/AAC: this would invalidate the recorded detector scores.

## Local procedure

Use your Ubuntu checkout with the saved P4 audio and results JSON (for example, the preserved V4 workspace). In a **separate clean checkout or Git worktree of the latest website `main`**, run:

```bash
python scripts/publish_v4_audio.py \
  --source-root /home/nsk/blind-audio-watermarking-v4/experiments/v4_end_to_end_acceptance
```

This first run is an audit and **does not copy or commit media**. It must show all eight files as SHA256 matches. If a filename is stored in another subdirectory, the script searches within this fixed experiment folder recursively. Missing, duplicated, mis-sized, or SHA-mismatched files block publishing.

After verifying that the sample attribution remains CC0 at the original FMA track pages, run:

```bash
python scripts/publish_v4_audio.py \
  --source-root /home/nsk/blind-audio-watermarking-v4/experiments/v4_end_to_end_acceptance \
  --publish
```

The script copies the eight files and marks both music tracks `SHA256_VERIFIED` and `published: true` in the JSON manifest. Preview the diff and stage **only the printed exact file paths**. Since `.gitignore` ignores all WAV/MP3/M4A files globally, use `git add -f` on those eight exact files (never `git add -f .`). Also stage the updated manifest. Commit on the website's `main` branch, push, and inspect its GitHub Pages deployment.

## Acceptance

1. Verify the actual Pages media URLs return audio, not HTML/404. Verify all eight deployed file SHA256 values match the frozen record when downloaded.
2. Try both 12 s CC0 tracks; play original and marked WAV, switch A/B with playback-position retention, and listen to MP3 and AAC versions. M4A browser support varies; download is a fallback.
3. Confirm the listening card scores are **recorded detector scores**, not the browser performing fresh inference.
4. Try mobile layouts, playback controls, no overlapping audio, and inspect any console errors. Record human A/B observations; do not claim perceptual invisibility solely from high SNR.
5. Ensure V3 Render is untouched, V4 PR #5 is still a draft, and no model weights or unrelated media were committed.

When the manifest is still `published:false`, the site displays an explicit **unavailable** message and does not point audio controls to fake files. This intentional fail-closed state is not a completed publication.
