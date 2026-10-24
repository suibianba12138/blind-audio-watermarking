"""Measure the frozen B1/QIM channel without changing its implementation.

This is a diagnostic-only P0 script.  The three deterministic signals are
synthetic probes, not licensed music, speech, or environmental recordings.
The script therefore reports channel behavior and does not claim a dataset
evaluation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.public_config import build_embedding_config, load_public_selector  # noqa: E402
from audio_watermark.course_v2 import identity_codeword  # noqa: E402
from audio_watermark.detect import _detection_statistic  # noqa: E402
from audio_watermark.framing import frame_audio  # noqa: E402
from audio_watermark.carrier import carrier_sides  # noqa: E402
from audio_watermark.b1 import embed_watermark_b1, detect_watermark_b1  # noqa: E402
from audio_watermark.metrics import signal_snr  # noqa: E402
from audio_watermark.transform import real_fft  # noqa: E402


FIXTURE_NAMES = ("speech_like", "music_like", "environment_like")
BANDS_HZ = ((1000.0, 3000.0), (3000.0, 6000.0), (6000.0, 10000.0))


def _normalize(values: np.ndarray, peak: float = 0.30) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    scale = float(np.max(np.abs(values)))
    return values * (peak / scale) if scale > 0.0 else values


def make_fixture(name: str, *, seconds: float = 6.0, sample_rate: int = 48_000) -> np.ndarray:
    """Return a deterministic synthetic probe labelled by broad signal type."""

    if name not in FIXTURE_NAMES:
        raise ValueError(f"unknown fixture: {name}")
    count = int(round(seconds * sample_rate))
    time = np.arange(count, dtype=np.float64) / sample_rate
    rng = np.random.default_rng(20261024 + FIXTURE_NAMES.index(name))
    if name == "speech_like":
        syllable = 0.58 + 0.42 * (0.5 + 0.5 * np.sin(2.0 * np.pi * 2.1 * time))
        carrier = (
            0.75 * np.sin(2.0 * np.pi * 180.0 * time)
            + 0.32 * np.sin(2.0 * np.pi * 360.0 * time)
            + 0.18 * np.sin(2.0 * np.pi * 720.0 * time)
        )
        values = syllable * carrier + 0.012 * rng.standard_normal(count)
    elif name == "music_like":
        notes = (220.0, 277.18, 329.63, 440.0, 554.37, 659.25)
        values = sum(
            (0.20 / (1.0 + index / 3.0))
            * np.sin(2.0 * np.pi * frequency * time + index * 0.37)
            for index, frequency in enumerate(notes)
        )
        values *= 0.75 + 0.25 * np.sin(2.0 * np.pi * 0.5 * time) ** 2
        values += 0.025 * np.sin(2.0 * np.pi * 1760.0 * time)
    else:
        noise = rng.standard_normal(count)
        burst = (np.sin(2.0 * np.pi * 0.7 * time) > 0.35).astype(np.float64)
        values = 0.16 * noise + 0.18 * burst * np.sin(2.0 * np.pi * 4200.0 * time)
    return _normalize(values)


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    wavfile.write(path, sample_rate, np.asarray(samples, dtype=np.float32))


def _ffmpeg_mp3_roundtrip(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is unavailable")
    with tempfile.TemporaryDirectory(prefix="v3_p0_channel_") as directory:
        root = Path(directory)
        source = root / "marked.wav"
        encoded = root / "marked.mp3"
        decoded = root / "decoded.wav"
        _write_wav(source, samples, sample_rate)
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(encoded),
            ],
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(encoded),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_f32le",
                str(decoded),
            ],
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        _, values = wavfile.read(decoded)
        values = np.asarray(values, dtype=np.float64)
        if np.issubdtype(values.dtype, np.integer):
            info = np.iinfo(values.dtype)
            values = values / float(max(abs(info.min), info.max))
        return values[: samples.size]


def _safe_correlation(values: np.ndarray) -> float | None:
    if values.shape[0] < 2 or values.shape[1] < 2:
        return None
    correlations = np.corrcoef(values, rowvar=False)
    upper = correlations[np.triu_indices(values.shape[1], k=1)]
    finite = upper[np.isfinite(upper)]
    return float(np.mean(finite)) if finite.size else None


def _band_distortion(clean: np.ndarray, marked: np.ndarray, sample_rate: int, n_fft: int) -> dict[str, float]:
    clean_frames = frame_audio(clean, n_fft, n_fft, pad_end=True)
    marked_frames = frame_audio(marked, n_fft, n_fft, pad_end=True)
    clean_spec = real_fft(clean_frames)
    marked_spec = real_fft(marked_frames)
    delta_db = 20.0 / math.log(10.0) * (
        np.log(np.maximum(np.abs(marked_spec), np.finfo(float).tiny))
        - np.log(np.maximum(np.abs(clean_spec), np.finfo(float).tiny))
    )
    frequencies = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
    result: dict[str, float] = {}
    for low, high in BANDS_HZ:
        mask = (frequencies >= low) & (frequencies < high)
        result[f"{int(low)}-{int(high)}_khz_rms_db"] = float(
            np.sqrt(np.mean(delta_db[:, mask] ** 2))
        )
    return result


def _per_observation_rows(
    clean: np.ndarray,
    marked: np.ndarray,
    received: np.ndarray,
    payload: tuple[int, ...],
    config: object,
    selector: object,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    clean_spec = real_fft(frame_audio(clean, config.n_fft, config.hop_length, pad_end=True))
    marked_spec = real_fft(frame_audio(marked, config.n_fft, config.hop_length, pad_end=True))
    received_spec = real_fft(frame_audio(received, config.n_fft, config.hop_length, pad_end=True))
    rows: list[dict[str, object]] = []
    clean_stats = np.zeros((config.payload_bits, config.frames_per_bit))
    marked_stats = np.zeros_like(clean_stats)
    received_stats = np.zeros_like(clean_stats)
    low_energy_flags: list[int] = []
    for bit_index, expected in enumerate(payload):
        for repetition in range(config.frames_per_bit):
            frame_index = bit_index * config.frames_per_bit + repetition
            group = selector.group_for_frame(frame_index)
            a_bins, b_bins = carrier_sides(group)
            clean_stat = _detection_statistic(clean_spec[frame_index], group, config.strength)
            marked_stat = _detection_statistic(marked_spec[frame_index], group, config.strength)
            received_stat = _detection_statistic(received_spec[frame_index], group, config.strength)
            clean_stats[bit_index, repetition] = clean_stat
            marked_stats[bit_index, repetition] = marked_stat
            received_stats[bit_index, repetition] = received_stat
            all_carrier = np.concatenate((a_bins, b_bins))
            candidate_low = max(1, int(np.ceil(config.candidate_band_hz.low_hz * config.n_fft / config.sample_rate)))
            candidate_high = min(config.n_fft // 2 - 1, int(np.floor(config.candidate_band_hz.high_hz * config.n_fft / config.sample_rate)))
            candidate = np.arange(candidate_low, candidate_high + 1)
            host_magnitude = np.abs(clean_spec[frame_index])
            low_energy_threshold = np.percentile(host_magnitude[candidate], 10.0)
            low_energy_flags.extend(
                (host_magnitude[all_carrier] <= low_energy_threshold).astype(np.int8).tolist()
            )
            rows.append(
                {
                    "bit": bit_index,
                    "repetition": repetition,
                    "expected": expected,
                    "clean_stat": float(clean_stat),
                    "marked_stat": float(marked_stat),
                    "received_stat": float(received_stat),
                    "host_to_marked_sign_flip": int(np.signbit(clean_stat) != np.signbit(marked_stat)),
                    "marked_to_received_sign_flip": int(np.signbit(marked_stat) != np.signbit(received_stat)),
                    "clean_error": int((clean_stat >= 0.0) != bool(expected)),
                    "marked_error": int((marked_stat >= 0.0) != bool(expected)),
                    "received_error": int((received_stat >= 0.0) != bool(expected)),
                }
            )
    summary = {
        "host_to_marked_boundary_crossing_rate": float(np.mean([row["host_to_marked_sign_flip"] for row in rows])),
        "marked_to_mp3_boundary_crossing_rate": float(np.mean([row["marked_to_received_sign_flip"] for row in rows])),
        "clean_ber_by_repetition": float(np.mean([row["clean_error"] for row in rows])),
        "marked_ber_by_repetition": float(np.mean([row["marked_error"] for row in rows])),
        "mp3_ber_by_repetition": float(np.mean([row["received_error"] for row in rows])),
        "repetition_statistic_correlation": _safe_correlation(marked_stats),
        "mp3_repetition_statistic_correlation": _safe_correlation(received_stats),
        "low_energy_carrier_fraction": float(np.mean(low_energy_flags)),
        "per_bit_marked_statistic_mean": [float(value) for value in np.mean(marked_stats, axis=1)],
        "per_bit_mp3_statistic_mean": [float(value) for value in np.mean(received_stats, axis=1)],
        "per_bit_marked_repetitions": marked_stats.tolist(),
        "per_bit_mp3_repetitions": received_stats.tolist(),
    }
    return rows, summary


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = build_embedding_config()
    selector = load_public_selector()
    payload = identity_codeword("UESTC-003")
    all_rows: list[dict[str, object]] = []
    fixture_results: dict[str, object] = {}
    for fixture in FIXTURE_NAMES:
        clean = make_fixture(fixture, sample_rate=config.sample_rate)
        marked = embed_watermark_b1(clean, payload, config, selector)
        received = _ffmpeg_mp3_roundtrip(marked, config.sample_rate)
        detection_clean = detect_watermark_b1(clean, config, selector)
        detection_marked = detect_watermark_b1(marked, config, selector)
        detection_received = detect_watermark_b1(received, config, selector)
        rows, channel_summary = _per_observation_rows(
            clean, marked, received, payload, config, selector
        )
        for row in rows:
            row["fixture"] = fixture
        all_rows.extend(rows)
        fixture_results[fixture] = {
            "synthetic_fixture": True,
            "payload_identity": "UESTC-003",
            "payload_bits": 32,
            "clean_detected_ber": float(np.mean(np.asarray(detection_clean.payload_bits) != payload)),
            "marked_detected_ber": float(np.mean(np.asarray(detection_marked.payload_bits) != payload)),
            "mp3_detected_ber": float(np.mean(np.asarray(detection_received.payload_bits) != payload)),
            "clean_confidence": float(detection_clean.confidence),
            "marked_confidence": float(detection_marked.confidence),
            "mp3_confidence": float(detection_received.confidence),
            "snr_marked_vs_clean_db": signal_snr(clean, marked),
            "snr_mp3_vs_marked_db": signal_snr(marked[: received.size], received),
            "band_log_spectral_distortion": _band_distortion(clean, marked, config.sample_rate, config.n_fft),
            "channel": channel_summary,
        }
    csv_path = output_dir / "per_observation.csv"
    fieldnames = (
        "fixture", "bit", "repetition", "expected", "clean_stat", "marked_stat",
        "received_stat", "host_to_marked_sign_flip", "marked_to_received_sign_flip",
        "clean_error", "marked_error", "received_error",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    report = {
        "provenance": {
            "status": "DIAGNOSTIC_ONLY",
            "fixtures": "deterministic synthetic probes; not licensed source recordings",
            "algorithm": "frozen public REAL_TOP32 B1 QIM",
            "strength": config.strength,
            "seed": config.seed,
            "mp3": "FFmpeg libmp3lame 128k",
        },
        "fixtures": fixture_results,
        "per_observation_csv": str(csv_path),
    }
    (output_dir / "channel_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
