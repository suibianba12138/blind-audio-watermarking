"""Freeze the source-disjoint V3-P2-V validation manifest.

The manifest references a local MUSAN checkout only.  Audio is never copied
into the repository.  Selection is deterministic and excludes every audited
P0/R1, Pilot, and P1 path, SHA256, source group, and verified six-second crop
fingerprint available from the historical manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import wave
from math import gcd
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.signal import resample_poly


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _historical(manifests: Iterable[Path]) -> tuple[set[str], set[str], set[str]]:
    paths: set[str] = set()
    hashes: set[str] = set()
    groups: set[str] = set()
    for manifest_path in manifests:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for record in data.get("records", []):
            relative = record.get("relative_path") or record.get("path") or record.get("audio_path")
            if relative:
                paths.add(str(relative).replace("MUSAN:", ""))
            if record.get("sha256"):
                hashes.add(str(record["sha256"]))
            if record.get("source_group_id"):
                groups.add(str(record["source_group_id"]))
    return paths, hashes, groups


def _read_first_seconds(path: Path, seconds: float = 6.0) -> tuple[int, np.ndarray]:
    """Read only the first seconds of a PCM WAV, avoiding full-file loading."""

    with wave.open(str(path), "rb") as handle:
        sample_rate = int(handle.getframerate())
        channels = int(handle.getnchannels())
        sample_width = int(handle.getsampwidth())
        frames = min(int(handle.getnframes()), int(round(seconds * sample_rate)))
        raw = handle.readframes(frames)
    if sample_width == 1:
        values = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0
        scale = 128.0
    elif sample_width == 2:
        values = np.frombuffer(raw, dtype="<i2").astype(np.float64)
        scale = 32768.0
    elif sample_width == 4:
        values = np.frombuffer(raw, dtype="<i4").astype(np.float64)
        scale = 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width {sample_width}: {path}")
    if channels > 1:
        values = values.reshape(-1, channels).mean(axis=1)
    values = values / scale
    if sample_rate != 16_000 and values.size:
        factor = gcd(sample_rate, 16_000)
        values = resample_poly(values, 16_000 // factor, sample_rate // factor)
    values = np.asarray(values[: 6 * 16_000], dtype=np.float32)
    return sample_rate, values


def crop_sha256(path: Path) -> str:
    sample_rate, values = _read_first_seconds(path)
    digest = hashlib.sha256()
    digest.update(str(sample_rate).encode("ascii"))
    digest.update(str(values.shape[0]).encode("ascii"))
    digest.update(values.tobytes())
    return digest.hexdigest()


def _metadata(path: Path) -> tuple[int, int, int, str]:
    with wave.open(str(path), "rb") as handle:
        return (
            int(handle.getframerate()),
            int(handle.getnframes()),
            int(handle.getnchannels()),
            f"PCM_{int(handle.getsampwidth()) * 8}",
        )


def _fma_groups(dataset_root: Path, historical_paths: set[str], historical_hashes: set[str], historical_groups: set[str]) -> list[tuple[Path, str, str, str]]:
    license_path = dataset_root / "music/fma/LICENSE"
    sections = license_path.read_text(encoding="utf-8", errors="replace").split(
        "=============================================================================="
    )
    groups: list[tuple[Path, str, str, str]] = []
    for index, section in enumerate(sections):
        identifiers = re.findall(r"(?m)^music-fma-(\d{4})\s*$", section)
        if not identifiers:
            continue
        candidates = []
        for identifier in identifiers:
            path = dataset_root / f"music/fma/music-fma-{identifier}.wav"
            relative = str(path.relative_to(dataset_root))
            if not path.is_file() or relative in historical_paths:
                continue
            file_hash = sha256(path)
            if file_hash in historical_hashes:
                continue
            candidates.append(path)
        if not candidates:
            continue
        detail = next(
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
        # The independent unit is the FMA track/source recording.  The
        # license section is retained as provenance but must not collapse
        # distinct tracks into one source group.
        for path in sorted(candidates):
            source_group = f"MUSAN:FMA:{path.stem}"
            if source_group in historical_groups:
                continue
            groups.append(
                (
                    path,
                    source_group,
                    f"{detail}; MUSAN_license_group=MUSAN:FMA_LICENSE_GROUP_{index:02d}",
                    source_url,
                )
            )
    return groups


def _record(
    *,
    path: Path,
    category: str,
    index: int,
    source_group_id: str,
    license_detail: str,
    source_url: str,
    dataset_root: Path,
    historical_manifests: tuple[Path, ...],
) -> dict[str, object]:
    sample_rate, frame_count, channels, encoding = _metadata(path)
    relative = str(path.relative_to(dataset_root))
    return {
        "record_id": f"v3-p2-v-{category}-{index:04d}",
        "category": category,
        "split": "independent_test",
        "relative_path": relative,
        "source_recording_id": f"MUSAN:{relative}",
        "source_group_id": source_group_id,
        "source_license": "SOURCE_OR_SUBCORPUS_SPECIFIC; raw audio is not redistributed",
        "source_license_detail": license_detail,
        "source_url": source_url,
        "dataset_source_status": "LOCAL_REFERENCE_ONLY",
        "historical_manifest_scope": [str(path) for path in historical_manifests],
        "sample_rate_hz": sample_rate,
        "duration_seconds": frame_count / sample_rate,
        "minimum_duration_seconds": 6.0,
        "frame_count": frame_count,
        "channels": channels,
        "encoding": encoding,
        "sha256": sha256(path),
        "first_6s_canonical_16khz_sha256": crop_sha256(path),
    }


def build_manifest(dataset_root: Path, historical_manifests: tuple[Path, ...]) -> dict[str, object]:
    if not dataset_root.is_dir():
        raise FileNotFoundError(dataset_root)
    historical_paths, historical_hashes, historical_groups = _historical(historical_manifests)
    historical_crop_hashes: set[str] = set()
    for manifest_path in historical_manifests:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for record in data.get("records", []):
            relative = record.get("relative_path") or record.get("path") or record.get("audio_path")
            if not relative:
                continue
            path = dataset_root / str(relative).replace("MUSAN:", "")
            if path.is_file():
                historical_crop_hashes.add(crop_sha256(path))

    selected_paths: set[str] = set()
    selected_hashes: set[str] = set(historical_hashes)
    selected_groups: set[str] = set(historical_groups)
    selected_crops: set[str] = set(historical_crop_hashes)

    def accept(path: Path, group: str) -> bool:
        relative = str(path.relative_to(dataset_root))
        if relative in historical_paths or relative in selected_paths or group in selected_groups:
            return False
        file_hash = sha256(path)
        if file_hash in selected_hashes:
            return False
        crop_hash = crop_sha256(path)
        if crop_hash in selected_crops:
            return False
        try:
            sample_rate, frames, _channels, _encoding = _metadata(path)
        except (OSError, wave.Error, ValueError):
            return False
        if frames / sample_rate < 6.0:
            return False
        selected_paths.add(relative)
        selected_hashes.add(file_hash)
        selected_groups.add(group)
        selected_crops.add(crop_hash)
        return True

    records: list[dict[str, object]] = []
    category_counts = {"speech": 0, "music": 0, "environment": 0}
    for category, candidates in (
        (
            "speech",
            ((path, f"MUSAN:LIBRIVOX:{path.stem}", "Public Domain", "https://librivox.org/")
             for path in sorted((dataset_root / "speech/librivox").glob("*.wav"))),
        ),
        (
            "environment",
            ((path, f"MUSAN:FREESOUND:{path.stem}", "Public Domain per MUSAN FreeSound LICENSE", "https://freesound.org/")
             for path in sorted((dataset_root / "noise/free-sound").glob("*.wav"))),
        ),
        (
            "music",
            _fma_groups(dataset_root, historical_paths, historical_hashes, historical_groups),
        ),
    ):
        for path, group, detail, url in candidates:
            if category_counts[category] >= 20:
                break
            if accept(path, group):
                records.append(
                    _record(
                        path=path,
                        category=category,
                        index=category_counts[category],
                        source_group_id=group,
                        license_detail=detail,
                        source_url=url,
                        dataset_root=dataset_root,
                        historical_manifests=historical_manifests,
                    )
                )
                category_counts[category] += 1
    if category_counts != {"speech": 20, "music": 20, "environment": 20}:
        raise RuntimeError(f"insufficient source-disjoint records: {category_counts}")
    return {
        "manifest_version": "V3_P2_V_INDEPENDENT_VALIDATION_V1",
        "status": "FROZEN",
        "dataset": "MUSAN",
        "dataset_id": "OpenSLR SLR17",
        "dataset_license": "OpenSLR SLR17 and source/subcorpus terms retained in record metadata; raw audio is not redistributed",
        "dataset_root": str(dataset_root),
        "selection_policy": {
            "per_category": {"independent_test": 20},
            "source_unit": "distinct source recording; FMA license group retained as provenance only",
            "historical_exclusion": "all audited P0/R1, B1 Pilot, and V3-P1 manifests by path, file SHA256, source group, and exact first-six-second canonical fingerprint",
            "selection_order": "lexicographic path/license-group order, before outcomes",
            "messages_per_source": 2,
            "crop_policy": "fixed first 6 seconds after standard loader resampling to 48 kHz for evaluation",
            "no_parameter_selection": True,
            "no_audio_copied_to_repository": True,
        },
        "overlap_checks": {
            "path_overlap_with_historical": "PASS",
            "file_sha256_overlap_with_historical": "PASS",
            "source_group_overlap_with_historical": "PASS",
            "selected_file_sha256_duplicates": "PASS",
            "selected_first_6s_exact_duplicates": "PASS",
            "near_duplicate_or_semantic_content": "NOT_ESTABLISHED",
            "crop_overlap": "EXACT_CANONICAL_FIRST_6S_CHECK_PASS; near-crop equivalence not established",
        },
        "historical_manifest_sha256": {str(path): sha256(path) for path in historical_manifests},
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--historical-manifest", type=Path, action="append", required=True)
    args = parser.parse_args()
    manifests = tuple(args.historical_manifest)
    output = build_manifest(args.dataset_root, manifests)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "records": len(output["records"]), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
