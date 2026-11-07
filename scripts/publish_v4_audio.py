#!/usr/bin/env python3
"""Publish *actual* frozen V4 P4 experiment audio into the GitHub Pages tree.

Does not run SilentCipher, synthesize audio or modify the experiments.
Uses stdlib only. By default it audits without copying. --publish copies
only when all 8 exact local files match their recorded SHA256 checksums.

Example:
  python scripts/publish_v4_audio.py --source-root /path/to/V4/experiments/v4_end_to_end_acceptance
  python scripts/publish_v4_audio.py --source-root /path/to/V4/experiments/v4_end_to_end_acceptance --publish
  git add -f docs/assets/v4-audio/*.wav docs/assets/v4-audio/*.mp3 docs/assets/v4-audio/*.m4a
  git add docs/assets/v4-audio/manifest.json
  git commit -m "feat(pages): publish verified P4 V4 audio samples"
  git push origin main

Audio files are globally gitignored; a reviewed explicit force-add is required.
Check permissions/attribution before public push. These two FMA samples were
recorded as CC0 in the frozen source manifest, not as model training data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs" / "assets" / "v4-audio"
MANIFEST = DEST / "manifest.json"
EXPECTED = {
    "music_01": {
        "original": ("music_01_original_prepared.wav", "1ab6de691310639176f88dd70c9b763411169d5543c32b92484979c7c9f7a974"),
        "watermarked": ("music_01_watermarked.wav", "85289a63aa3dcdb257b6f9a6df5e8f9179ebeb94814b48327a5a617debbc08f0"),
        "mp3": ("music_01_mp3_128k.mp3", "30ed55cdc13e30f887dfa1e11e197c6e53c42c1b8ce458d5de9a9f6daf08ce2b"),
        "aac": ("music_01_aac_lc_m4a_128k.m4a", "18fd87b6f8400facd260484a00794582baee9d2f650203e2698855e0c860cd35"),
    },
    "music_02": {
        "original": ("music_02_original_prepared.wav", "12a31ec46ad8cab8ce80c1743efc75619a63874f44a2708d531b3fab4114ccc3"),
        "watermarked": ("music_02_watermarked.wav", "98fe7c41dfccc29166bdbcf771962f3758db93fc183d22e3a589a7c2fead917a"),
        "mp3": ("music_02_mp3_128k.mp3", "9af756799508b227405cc747550b1a78b4b588ff0b5980e3c86feeca483f4f5c"),
        "aac": ("music_02_aac_lc_m4a_128k.m4a", "30a89c1163c475086f4620936a3a182db51cfa9f257e87868bd7df1c4134189f"),
    },
}


def sha256(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True,
                        help="Directory containing actual P4 exports, including possible subdirectories.")
    parser.add_argument("--publish", action="store_true",
                        help="Copy verified audio into docs/ and set published=true in its manifest.")
    parser.add_argument("--evidence", type=Path, default=None,
                        help="Frozen results.json path; defaults to <source-root>/results.json.")
    args = parser.parse_args()
    source_root = args.source_root.expanduser().resolve()
    evidence_file = (args.evidence or source_root / "results.json").expanduser().resolve()
    if not source_root.is_dir():
        print(f"NOT FOUND: {source_root}", file=sys.stderr)
        return 2

    # Manifest and result records are only used as an additional contract;
    # if the branch is missing those records, do not trust hand-entered names alone.
    if not evidence_file.is_file():
        print(f"Missing frozen evidence: {evidence_file}", file=sys.stderr)
        print("Point --evidence to the preserved V4 P4 results.json.", file=sys.stderr)
        return 2
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    assert evidence["message_hex"] == "A4D97E216B", "Unexpected frozen message"
    evidence_cases = {case["source_id"]: case for case in evidence["cases"]}

    verified = {}
    failures = []
    for track, parts in EXPECTED.items():
        case = evidence_cases[track]
        expected_from_results = {
            "original": case["embedding"]["original_prepared"],
            "watermarked": case["embedding"]["watermarked_wav"],
            "mp3": case["channels"]["mp3_128k"]["encoded_output"],
            "aac": case["channels"]["aac_lc_m4a_128k"]["encoded_output"],
        }
        for role, (filename, digest) in parts.items():
            record = expected_from_results[role]
            if record["file"] != filename or record["sha256"] != digest:
                failures.append(f"Frozen evidence mismatch: {track}/{role}")
                continue
            # Search only in the fixed P4 export directory, never arbitrary user paths.
            candidates = [p for p in source_root.rglob(filename) if p.is_file()]
            if len(candidates) != 1:
                failures.append(f"Expected exactly one local file {filename}, found {len(candidates)}")
                continue
            src = candidates[0]
            if src.stat().st_size != record["bytes"]:
                failures.append(f"{filename}: size {src.stat().st_size} != {record['bytes']}")
                continue
            actual = sha256(src)
            if actual != digest:
                failures.append(f"{filename}: SHA256 {actual} != {digest}")
                continue
            verified[(track, role)] = (src, filename, digest, src.stat().st_size)
            print(f"PASS {track:8s} {role:11s} {filename} SHA256={digest[:16]}…")

    if failures:
        print("\nBLOCKED: The following files are missing or inconsistent:", file=sys.stderr)
        for failure in failures:
            print(" - " + failure, file=sys.stderr)
        print("No publication performed.", file=sys.stderr)
        return 1
    if len(verified) != 8:
        print("BLOCKED: Incomplete eight-file contract", file=sys.stderr)
        return 1
    if not args.publish:
        print("\nAUDIT PASS; no files copied. Repeat with --publish to prepare public assets.")
        return 0

    old_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert old_manifest["version"] == 1
    assert old_manifest["protocol"] == "P4_END_TO_END_FROZEN"
    DEST.mkdir(parents=True, exist_ok=True)
    for (track, role), (src, filename, digest, size) in verified.items():
        dst = DEST / filename
        shutil.copyfile(src, dst)
        if sha256(dst) != digest:
            dst.unlink(missing_ok=True)
            raise RuntimeError(f"Copied asset failed checksum: {dst}")
        print(f"COPIED {dst.relative_to(ROOT)} ({size} bytes)")
    for track in EXPECTED:
        item = old_manifest["tracks"][track]
        item["published"] = True
        item["validation"] = "SHA256_VERIFIED"
        for role in EXPECTED[track]:
            _, filename, digest, size = verified[(track, role)]
            item[role] = {"file": filename, "sha256": digest, "bytes": size}
    data = json.dumps(old_manifest, indent=2, ensure_ascii=False) + "\n"
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(MANIFEST)
    print("\nPUBLISH PREPARED. Carefully review public media licensing and git diff.")
    print("Audio extensions are ignored by .gitignore; explicitly stage only these eight exact files:")
    for track in EXPECTED:
        for role in EXPECTED[track]:
            print(f"git add -f docs/assets/v4-audio/{EXPECTED[track][role][0]}")
    print("git add docs/assets/v4-audio/manifest.json")
    print("Do not run a broad force-add or upload unrelated audio/checkpoint files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
