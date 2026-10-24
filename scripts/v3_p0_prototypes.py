"""Run the bounded P0 spread-spectrum trials on synthetic probes.

The trials are development diagnostics only.  They do not use a validation
set to choose a frozen operating point and do not represent real-source
generalization.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from v3_p0_channel_audit import (  # noqa: E402
    FIXTURE_NAMES,
    _ffmpeg_mp3_roundtrip,
    _band_distortion,
    make_fixture,
)
from audio_watermark.metrics import signal_snr  # noqa: E402
from audio_watermark.v3_p0 import (  # noqa: E402
    SpreadSpectrumConfig,
    detect_spread_spectrum,
    embed_spread_spectrum,
)


TRIAL_STRENGTHS = (0.02, 0.04, 0.08)
PAYLOADS = {
    1: (1,),
    8: (1, 0, 1, 1, 0, 0, 1, 0),
}


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for payload_bits, payload in PAYLOADS.items():
        for strength in TRIAL_STRENGTHS:
            config = SpreadSpectrumConfig(
                payload_bits=payload_bits,
                frames_per_bit=32 if payload_bits == 1 else 16,
                strength=strength,
            )
            for fixture in FIXTURE_NAMES:
                clean = make_fixture(fixture, sample_rate=config.sample_rate)
                started = time.perf_counter()
                marked = embed_spread_spectrum(clean, payload, config)
                embed_seconds = time.perf_counter() - started
                clean_detection = detect_spread_spectrum(marked, config)
                started = time.perf_counter()
                received = _ffmpeg_mp3_roundtrip(marked, config.sample_rate)
                mp3_seconds = time.perf_counter() - started
                mp3_detection = detect_spread_spectrum(received, config)
                clean_ber = float(
                    np.mean(np.asarray(clean_detection.payload_bits) != payload)
                )
                mp3_ber = float(
                    np.mean(np.asarray(mp3_detection.payload_bits) != payload)
                )
                rows.append(
                    {
                        "method": "keyed_spread_spectrum_local_norm",
                        "fixture": fixture,
                        "split": "synthetic_development_probe",
                        "payload_bits": payload_bits,
                        "frames_per_bit": config.frames_per_bit,
                        "strength": strength,
                        "clean_ber": clean_ber,
                        "mp3_ber": mp3_ber,
                        "clean_complete_recovery": int(clean_ber == 0.0),
                        "mp3_complete_recovery": int(mp3_ber == 0.0),
                        "false_positive_rate": "NOT_ESTABLISHED_NO_REJECTOR",
                        "snr_marked_vs_clean_db": signal_snr(clean, marked),
                        "spectral_distortion_rms_db": float(
                            np.mean(
                                list(
                                    _band_distortion(
                                        clean, marked, config.sample_rate, config.n_fft
                                    ).values()
                                )
                            )
                        ),
                        "mp3_fidelity_snr_db": signal_snr(marked[: received.size], received),
                        "clean_confidence": clean_detection.confidence,
                        "mp3_confidence": mp3_detection.confidence,
                        "embed_runtime_seconds": embed_seconds,
                        "mp3_roundtrip_seconds": mp3_seconds,
                        "provenance": "synthetic probe only; no licensed source dataset",
                    }
                )
    fieldnames = list(rows[0])
    csv_path = output_dir / "prototype_trials.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "status": "DEVELOPMENT_ONLY",
        "trials": rows,
        "csv": str(csv_path),
        "parameter_policy": "bounded strengths 0.04/0.08/0.12; not selected from an independent test set",
    }
    (output_dir / "prototype_trials.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output_dir)
    for row in report["trials"]:
        print(
            row["payload_bits"], row["strength"], row["fixture"],
            "clean_ber=", row["clean_ber"], "mp3_ber=", row["mp3_ber"],
            "snr=", round(float(row["snr_marked_vs_clean_db"]), 2),
        )


if __name__ == "__main__":
    main()
