"""Freeze a small source-disjoint R1 real-audio manifest.

The script references an existing local MUSAN checkout but never copies audio
into the repository. It excludes every path listed by the audited Course V2
manifests and selects one file per higher-level FMA license group.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _historical_paths(manifests: tuple[Path, ...]) -> set[str]:
    paths: set[str] = set()
    for manifest in manifests:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for record in data.get("records", []):
            for key in ("relative_path", "path", "audio_path"):
                value = record.get(key)
                if value:
                    paths.add(str(value).replace("MUSAN:", ""))
    return paths


def _manifest_hashes(manifests: tuple[Path, ...]) -> dict[str, str]:
    return {str(path): _sha256(path) for path in manifests if path.is_file()}


def _fma_groups(dataset_root: Path, historical: set[str]) -> list[tuple[str, Path, str, str]]:
    license_path = dataset_root / "music/fma/LICENSE"
    groups: list[tuple[str, Path, str, str]] = []
    sections = license_path.read_text(encoding="utf-8", errors="replace").split(
        "=============================================================================="
    )
    for index, section in enumerate(sections):
        ids = re.findall(r"(?m)^music-fma-(\d{4})\s*$", section)
        if not ids:
            continue
        candidates = [
            dataset_root / f"music/fma/music-fma-{identifier}.wav"
            for identifier in ids
        ]
        candidates = [
            path
            for path in sorted(candidates)
            if path.is_file() and str(path.relative_to(dataset_root)) not in historical
        ]
        if not candidates:
            continue
        license_detail = next(
            (
                line.strip()
                for line in section.splitlines()
                if "licensed under" in line
                or line.strip().startswith("CC ")
                or "Public Domain" in line
            ),
            "SEE MUSAN MUSIC/FMA/LICENSE",
        )
        source_url = next(
            (line.strip() for line in section.splitlines() if line.strip().startswith("http")),
            "",
        )
        groups.append(
            (f"MUSAN:FMA_LICENSE_GROUP_{index:02d}", candidates[0], license_detail, source_url)
        )
    return groups


def _record(
    path: Path,
    *,
    category: str,
    split: str,
    source_group_id: str,
    license_detail: str,
    source_url: str,
    historical_paths: set[str],
    historical_manifests: tuple[Path, ...],
    dataset_root: Path,
) -> dict[str, object]:
    sample_rate, values = wavfile.read(path)
    array = np.asarray(values)
    if array.ndim == 1:
        channels = 1
        frame_count = int(array.shape[0])
    else:
        channels = int(array.shape[1])
        frame_count = int(array.shape[0])
    relative = str(path.relative_to(dataset_root))
    return {
        "record_id": f"r1-{category}-{split}-{len(historical_paths):04d}-{path.stem}",
        "category": category,
        "split": split,
        "relative_path": relative,
        "source_recording_id": f"MUSAN:{relative}",
        "source_group_id": source_group_id,
        "source_license": (
            "SOURCE_OR_SUBCORPUS_SPECIFIC; see source_license_detail; "
            "raw audio is not redistributed by this repository"
        ),
        "source_license_detail": license_detail,
        "source_url": source_url,
        "historical_use_status": "NOT_LISTED_IN_AUDITED_COURSE_V2_MANIFESTS",
        "historical_manifest_scope": [str(path) for path in historical_manifests],
        "sample_rate_hz": int(sample_rate),
        "duration_seconds": float(frame_count / int(sample_rate)),
        "r1_minimum_duration_seconds": 6.0,
        "frame_count": frame_count,
        "channels": channels,
        "dtype": str(array.dtype),
        "container_format": "WAV",
        "sha256": _sha256(path),
    }


def build_manifest(
    dataset_root: Path,
    historical_manifests: tuple[Path, ...],
    manifest_version: str = "V3_P0_R1_REAL_AUDIO_V1",
) -> dict[str, object]:
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"MUSAN root not found: {dataset_root}")
    historical = _historical_paths(historical_manifests)
    speech = [
        path
        for path in sorted((dataset_root / "speech/librivox").glob("*.wav"))
        if str(path.relative_to(dataset_root)) not in historical
    ][:20]
    environment = []
    for path in sorted((dataset_root / "noise/free-sound").glob("*.wav")):
        if str(path.relative_to(dataset_root)) in historical:
            continue
        sample_rate, values = wavfile.read(path)
        if len(values) / int(sample_rate) >= 6.0:
            environment.append(path)
        if len(environment) == 20:
            break
    music_groups = _fma_groups(dataset_root, historical)[:20]
    if len(speech) < 20 or len(environment) < 20 or len(music_groups) < 20:
        raise RuntimeError("insufficient source-disjoint files/groups for R1 manifest")

    records: list[dict[str, object]] = []
    for category, entries in (
        ("speech", [(f"MUSAN:LIBRIVOX:{path.stem}", path, "Public Domain", "https://librivox.org/") for path in speech]),
        ("environment", [(f"MUSAN:FREESOUND:{path.stem}", path, "Public Domain per MUSAN FreeSound LICENSE", "https://freesound.org/") for path in environment]),
    ):
        for index, (group, path, detail, url) in enumerate(entries):
            split = "dev" if index < 10 else "test"
            records.append(
                _record(
                    path,
                    category=category,
                    split=split,
                    source_group_id=group,
                    license_detail=detail,
                    source_url=url,
                    historical_paths=historical,
                    historical_manifests=historical_manifests,
                    dataset_root=dataset_root,
                )
            )
    for index, (group, path, detail, url) in enumerate(music_groups):
        split = "dev" if index < 10 else "test"
        records.append(
            _record(
                path,
                category="music",
                split=split,
                source_group_id=group,
                license_detail=detail,
                source_url=url,
                historical_paths=historical,
                historical_manifests=historical_manifests,
                dataset_root=dataset_root,
            )
        )
    return {
        "manifest_version": manifest_version,
        "status": "FROZEN",
        "dataset": "MUSAN",
        "dataset_id": "OpenSLR SLR17",
        "dataset_license": (
            "OpenSLR SLR17 listing is CC BY 4.0; source/subcorpus terms are "
            "retained in source_license_detail"
        ),
        "dataset_root": str(dataset_root),
        "selection_policy": {
            "per_category": {"dev": 10, "test": 10},
            "split_unit": "source recording or higher-level FMA license group",
            "exclude_historical_manifests": [str(path) for path in historical_manifests],
            "no_parameter_selection": True,
            "no_audio_copied_to_repository": True,
        },
        "historical_manifest_sha256": _manifest_hashes(historical_manifests),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--historical-manifest", type=Path, action="append", required=True)
    parser.add_argument("--manifest-version", default="V3_P0_R1_REAL_AUDIO_V1")
    args = parser.parse_args()
    manifest = build_manifest(
        args.dataset_root,
        tuple(args.historical_manifest),
        manifest_version=args.manifest_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "records": len(manifest["records"]), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
