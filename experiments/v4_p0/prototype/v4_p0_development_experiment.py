"""Run the bounded V4-P0 development comparison on local MUSAN references.

The script never copies source audio into the repository. It uses only the
V3-P1 development split, records source metadata, and writes aggregate rows
and diagnostics. These results are development evidence, not independent
validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.b1 import embed_watermark_b1  # noqa: E402
from audio_watermark.b1_soft import decode_b1_soft_detection, detect_watermark_b1_soft  # noqa: E402
from audio_watermark.b2_capacity import decode_soft_capacity, encode_capacity_payload  # noqa: E402
from audio_watermark.metrics import bit_error_rate, signal_snr  # noqa: E402
from audio_watermark.v4_tf import V4TFConfig, detect_v4_tf, embed_v4_tf  # noqa: E402


SAMPLE_RATE = 48_000
BLOCK_SECONDS = 6
MESSAGE_SEEDS = (11, 29)
V4_STRENGTHS = (0.04, 0.08)
V3_STRENGTH = 1.60
V3_THRESHOLD = 0.7855073980199624
MANIFEST = ROOT / "configs" / "v3_p1_independent_manifest.json"
DEFAULT_DATASET_ROOT = Path(os.environ.get("V4_DATASET_ROOT", "datasets/MUSAN"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_float(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.integer):
        info = np.iinfo(array.dtype)
        array = array.astype(np.float64) / float(max(abs(info.min), info.max))
    else:
        array = array.astype(np.float64)
    if array.ndim == 2:
        array = np.mean(array, axis=1)
    return np.asarray(array, dtype=np.float64)


def load_source(record: dict[str, object], dataset_root: Path) -> np.ndarray:
    path = dataset_root / str(record["relative_path"])
    source_rate, values = wavfile.read(path)
    samples = _to_float(values)
    if int(source_rate) != SAMPLE_RATE:
        divisor = math.gcd(int(source_rate), SAMPLE_RATE)
        samples = resample_poly(
            samples, SAMPLE_RATE // divisor, int(source_rate) // divisor
        ).astype(np.float64)
    target = SAMPLE_RATE * BLOCK_SECONDS
    if samples.size >= target:
        return samples[:target]
    return np.pad(samples, (0, target - samples.size))


def _message(seed: int, bits: int) -> tuple[int, ...]:
    return tuple(int(value) for value in np.random.default_rng(seed).integers(0, 2, size=bits))


def _repeat4(payload: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(value) for value in payload for _ in range(4))


def _unrepeat4(payload: Sequence[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in payload)
    return tuple(int(sum(values[index : index + 4]) >= 2) for index in range(0, 32, 4))


def _fit_length(values: np.ndarray, length: int) -> np.ndarray:
    if values.size >= length:
        return np.asarray(values[:length], dtype=np.float64)
    return np.pad(np.asarray(values, dtype=np.float64), (0, length - values.size))


def _write_wav(path: Path, samples: np.ndarray) -> None:
    wavfile.write(path, SAMPLE_RATE, np.asarray(samples, dtype=np.float32))


def _mp3_roundtrip(samples: np.ndarray) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is unavailable")
    with tempfile.TemporaryDirectory(prefix="v4_p0_mp3_") as directory:
        root = Path(directory)
        marked = root / "marked.wav"
        encoded = root / "marked.mp3"
        decoded = root / "decoded.wav"
        _write_wav(marked, samples)
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(marked),
             "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "libmp3lame", "-b:a", "128k", str(encoded)],
            check=True, shell=False, capture_output=True, text=True, timeout=120,
        )
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(encoded),
             "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_f32le", str(decoded)],
            check=True, shell=False, capture_output=True, text=True, timeout=120,
        )
        _, values = wavfile.read(decoded)
        return _fit_length(_to_float(values), samples.size)


def _clipping(clean: np.ndarray, marked: np.ndarray) -> tuple[int, float]:
    clean_peak = float(np.max(np.abs(clean)))
    marked_peak = float(np.max(np.abs(marked)))
    return int(marked_peak > 1.0 and clean_peak <= 1.0), marked_peak


def _spectral_rms(clean: np.ndarray, marked: np.ndarray) -> float:
    n_fft = 2048
    clean_frames = np.array([clean[index : index + n_fft] for index in range(0, clean.size - n_fft + 1, n_fft)])
    marked_frames = np.array([marked[index : index + n_fft] for index in range(0, marked.size - n_fft + 1, n_fft)])
    if clean_frames.size == 0:
        return float("nan")
    clean_log = np.log(np.maximum(np.abs(np.fft.rfft(clean_frames, axis=1)), np.finfo(float).tiny))
    marked_log = np.log(np.maximum(np.abs(np.fft.rfft(marked_frames, axis=1)), np.finfo(float).tiny))
    delta_db = 20.0 / math.log(10.0) * (marked_log - clean_log)
    return float(np.sqrt(np.mean(delta_db * delta_db)))


def _base_row(record: dict[str, object], method: str, bits: int, strength: float | str, seed: int, condition: str) -> dict[str, object]:
    return {
        "record_id": record["record_id"],
        "source_group_id": record["source_group_id"],
        "category": record["category"],
        "split": record["split"],
        "method": method,
        "effective_payload_bits": bits,
        "strength": strength,
        "message_seed": seed,
        "condition": condition,
        "source_sha256": record["sha256"],
        "detector_expected_payload_used": False,
    }


def _evaluate_v3(clean: np.ndarray, record: dict[str, object], payload: tuple[int, ...], selector: object, config: object) -> list[dict[str, object]]:
    expected_physical = tuple(int(value) for value in encode_capacity_payload(payload, 8))
    marked = embed_watermark_b1(clean, expected_physical, config, selector)
    received = _mp3_roundtrip(marked)
    rows: list[dict[str, object]] = []
    for condition, audio in (("clean", marked), ("mp3_128k", received)):
        started = time.perf_counter()
        soft = detect_watermark_b1_soft(audio, config, selector)
        decoded_evidence = decode_soft_capacity(soft.physical_statistics, 8)
        decoded = decoded_evidence.message_bits
        elapsed = time.perf_counter() - started
        presence = float(decoded_evidence.presence_score)
        row = _base_row(record, "v3_b1_soft8", 8, V3_STRENGTH, 0, condition)
        row.update({
            "expected_payload": "".join(map(str, payload)),
            "decoded_payload": "".join(map(str, decoded)),
            "logical_ber": bit_error_rate(payload, decoded),
            "physical_ber": bit_error_rate(expected_physical, soft.hard_physical_bits),
            "exact_message_recovery": int(decoded == payload),
            "presence_score": presence,
            "presence_threshold": V3_THRESHOLD,
            "detected": int(presence >= V3_THRESHOLD),
            "correct_accepted_recovery": int(presence >= V3_THRESHOLD and decoded == payload),
            "wrong_message_acceptance": int(presence >= V3_THRESHOLD and decoded != payload),
            "snr_db": signal_snr(clean, marked),
            "spectral_distortion_rms_db": _spectral_rms(clean, marked),
            "mp3_fidelity_snr_db": signal_snr(marked, received) if condition == "mp3_128k" else "NOT_APPLICABLE",
            "introduced_clipping": _clipping(clean, marked)[0],
            "detect_seconds": elapsed,
        })
        rows.append(row)
    return rows


def _evaluate_v4(clean: np.ndarray, record: dict[str, object], payload: tuple[int, ...], strength: float, bits: int) -> list[dict[str, object]]:
    config = V4TFConfig(payload_bits=bits, strength=strength)
    started = time.perf_counter()
    marked = embed_v4_tf(clean, payload, config)
    embed_seconds = time.perf_counter() - started
    received = _mp3_roundtrip(marked)
    rows: list[dict[str, object]] = []
    for condition, audio in (("clean", marked), ("mp3_128k", received)):
        started = time.perf_counter()
        evidence = detect_v4_tf(audio, config)
        elapsed = time.perf_counter() - started
        row = _base_row(record, f"v4_tf_{bits}bit", bits, strength, 0, condition)
        row.update({
            "expected_payload": "".join(map(str, payload)),
            "decoded_payload": "".join(map(str, evidence.recovered_payload)),
            "logical_ber": bit_error_rate(payload, evidence.recovered_payload),
            "physical_ber": "NOT_APPLICABLE",
            "exact_message_recovery": int(evidence.recovered_payload == payload),
            "presence_score": evidence.presence_score,
            "presence_threshold": config.presence_threshold,
            "detected": int(evidence.detected),
            "correct_accepted_recovery": int(evidence.detected and evidence.recovered_payload == payload),
            "wrong_message_acceptance": int(evidence.detected and evidence.recovered_payload != payload),
            "snr_db": signal_snr(clean, marked),
            "spectral_distortion_rms_db": _spectral_rms(clean, marked),
            "mp3_fidelity_snr_db": signal_snr(marked, received) if condition == "mp3_128k" else "NOT_APPLICABLE",
            "introduced_clipping": _clipping(clean, marked)[0],
            "embed_seconds": embed_seconds,
            "detect_seconds": elapsed,
            "used_frames": evidence.used_frames,
            "reject_reason": evidence.reject_reason or "",
        })
        rows.append(row)
    return rows


def _negative_v3(clean: np.ndarray, clean_mp3: np.ndarray, record: dict[str, object], selector: object, config: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for condition, audio in (("clean_negative", clean), ("mp3_clean_negative", clean_mp3)):
        started = time.perf_counter()
        soft = detect_watermark_b1_soft(audio, config, selector)
        decoded_evidence = decode_soft_capacity(soft.physical_statistics, 8)
        elapsed = time.perf_counter() - started
        presence = float(decoded_evidence.presence_score)
        row = _base_row(record, "v3_b1_soft8", 8, V3_STRENGTH, -1, condition)
        row.update({
            "expected_payload": "NOT_APPLICABLE",
            "decoded_payload": "".join(map(str, decoded_evidence.message_bits)),
            "logical_ber": "NOT_APPLICABLE",
            "physical_ber": "NOT_APPLICABLE",
            "exact_message_recovery": "NOT_APPLICABLE",
            "presence_score": presence,
            "presence_threshold": V3_THRESHOLD,
            "detected": int(presence >= V3_THRESHOLD),
            "correct_accepted_recovery": "NOT_APPLICABLE",
            "wrong_message_acceptance": "NOT_APPLICABLE",
            "false_positive": int(presence >= V3_THRESHOLD),
            "snr_db": "NOT_APPLICABLE",
            "spectral_distortion_rms_db": "NOT_APPLICABLE",
            "mp3_fidelity_snr_db": "NOT_APPLICABLE",
            "introduced_clipping": "NOT_APPLICABLE",
            "detect_seconds": elapsed,
        })
        rows.append(row)
    return rows


def _negative_v4(clean: np.ndarray, clean_mp3: np.ndarray, record: dict[str, object], strength: float, bits: int) -> list[dict[str, object]]:
    config = V4TFConfig(payload_bits=bits, strength=strength)
    rows: list[dict[str, object]] = []
    for condition, audio in (("clean_negative", clean), ("mp3_clean_negative", clean_mp3)):
        started = time.perf_counter()
        evidence = detect_v4_tf(audio, config)
        elapsed = time.perf_counter() - started
        row = _base_row(record, f"v4_tf_{bits}bit", bits, strength, -1, condition)
        row.update({
            "expected_payload": "NOT_APPLICABLE",
            "decoded_payload": "".join(map(str, evidence.recovered_payload)),
            "logical_ber": "NOT_APPLICABLE",
            "physical_ber": "NOT_APPLICABLE",
            "exact_message_recovery": "NOT_APPLICABLE",
            "presence_score": evidence.presence_score,
            "presence_threshold": config.presence_threshold,
            "detected": int(evidence.detected),
            "correct_accepted_recovery": "NOT_APPLICABLE",
            "wrong_message_acceptance": "NOT_APPLICABLE",
            "false_positive": int(evidence.detected),
            "snr_db": "NOT_APPLICABLE",
            "spectral_distortion_rms_db": "NOT_APPLICABLE",
            "mp3_fidelity_snr_db": "NOT_APPLICABLE",
            "introduced_clipping": "NOT_APPLICABLE",
            "detect_seconds": elapsed,
            "used_frames": evidence.used_frames,
            "reject_reason": evidence.reject_reason or "",
        })
        rows.append(row)
    return rows


def run(output_dir: Path, *, manifest_path: Path = MANIFEST, dataset_root: Path = DEFAULT_DATASET_ROOT) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [record for record in manifest["records"] if record["split"] == "dev"]
    selected = sorted(selected, key=lambda record: (str(record["category"]), str(record["record_id"])))
    selected = [
        record
        for category in ("environment", "music", "speech")
        for record in [
            candidate for candidate in selected if candidate["category"] == category
        ][:3]
    ]
    # The expression above is intentionally category-balanced and keeps three
    # source recordings per category. It is development evidence only.
    if len(selected) != 9:
        raise RuntimeError("V4-P0 requires nine available development records")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for record in selected:
        path = dataset_root / str(record["relative_path"])
        if not path.exists():
            raise FileNotFoundError(path)
        manifest_rows.append({
            "record_id": record["record_id"],
            "category": record["category"],
            "source_group_id": record["source_group_id"],
            "relative_path": record["relative_path"],
            "source_sha256_manifest": record["sha256"],
            "source_sha256_local": _sha256(path),
            "source_license_detail": record["source_license_detail"],
            "historical_use_status": record["historical_use_status"],
            "role": "v4_p0_development_only",
        })
    (output_dir / "DEV_MANIFEST.json").write_text(json.dumps({"status": "FROZEN_DEVELOPMENT_ONLY", "records": manifest_rows}, indent=2, sort_keys=True), encoding="utf-8")

    v3_config = replace(build_embedding_config(), strength=V3_STRENGTH)
    selector = load_public_selector()
    rows: list[dict[str, object]] = []
    for record in selected:
        clean = load_source(record, dataset_root)
        clean_mp3 = _mp3_roundtrip(clean)
        rows.extend(_negative_v3(clean, clean_mp3, record, selector, v3_config))
        for bits in (8, 16):
            for strength in V4_STRENGTHS:
                rows.extend(_negative_v4(clean, clean_mp3, record, strength, bits))
        for seed in MESSAGE_SEEDS:
            payload = _message(seed, 8)
            for row in _evaluate_v3(clean, record, payload, selector, v3_config):
                row["message_seed"] = seed
                rows.append(row)
            for bits in (8, 16):
                for strength in V4_STRENGTHS:
                    for row in _evaluate_v4(clean, record, _message(seed, bits), strength, bits):
                        row["message_seed"] = seed
                        rows.append(row)
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with (output_dir / "V4_P0_CANDIDATE_RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    baseline_rows = [row for row in rows if str(row["method"]).startswith("v3_")]
    with (output_dir / "BASELINE_RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(baseline_rows)
    return {"status": "DEVELOPMENT_ONLY", "records": len(selected), "rows": len(rows), "messages": list(MESSAGE_SEEDS), "strengths": list(V4_STRENGTHS), "output": str(output_dir / "V4_P0_CANDIDATE_RESULTS.csv")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, manifest_path=args.manifest, dataset_root=args.dataset_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
