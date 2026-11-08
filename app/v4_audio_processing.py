"""Bounded audio I/O, channel operations, alignment, and DSP figures for V4."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.signal import resample_poly

from .audio_io import AudioData

MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_AUDIO_SECONDS = 60
FFMPEG_TIMEOUT_SECONDS = 60
PCM16_SAFE_PEAK = 1.0 - 2.0 / 32768.0


def pcm16_safe_pair(reference: np.ndarray, marked: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Apply a shared linear gain when needed to avoid PCM16 export clipping."""
    clean = np.asarray(reference)
    watermarked = np.asarray(marked)
    if clean.ndim != 1 or watermarked.shape != clean.shape or clean.size == 0:
        raise ValueError("Audio pair must be non-empty mono arrays with identical shapes.")
    if not np.all(np.isfinite(clean)) or not np.all(np.isfinite(watermarked)):
        raise ValueError("Audio pair contains invalid numeric samples.")
    peak = float(max(np.max(np.abs(clean)), np.max(np.abs(watermarked))))
    gain = min(1.0, PCM16_SAFE_PEAK / peak) if peak > 0 else 1.0
    if gain == 1.0:
        return clean, watermarked, gain
    return clean * gain, watermarked * gain, gain


def parse_payload(backend: str, text: str) -> bytes | int:
    value = "".join((text or "").split())
    if backend == "Advanced Neural":
        compact = value.removeprefix("0x").removeprefix("0X")
        if len(compact) != 10:
            raise ValueError("Neural 消息必须是恰好 10 位十六进制字符（5 字节）。")
        try:
            return bytes.fromhex(compact)
        except ValueError as exc:
            raise ValueError("Neural 消息必须使用十六进制字符。") from exc
    if backend == "Classic DSP":
        try:
            number = int(value, 0) if value.lower().startswith("0x") else int(value, 10)
        except ValueError as exc:
            raise ValueError("Classic 消息请输入 0–255 十进制整数或 0x 前缀十六进制值。") from exc
        if not 0 <= number <= 255:
            raise ValueError("Classic 消息范围为 0–255（8 bit）。")
        return number
    raise ValueError("请选择有效水印后端。")


def _probe_audio(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("AUDIO_TOOLS_UNAVAILABLE")
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=sample_rate,channels",
             "-of", "json", str(path)],
            check=True, shell=False, capture_output=True, text=True, timeout=10,
        )
        info = json.loads(proc.stdout)
        streams = info.get("streams") or []
        duration = float((info.get("format") or {}).get("duration", 0))
        rate = int(streams[0].get("sample_rate", 0)) if streams else 0
        channels = int(streams[0].get("channels", 0)) if streams else 0
    except (subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("无法读取音频文件信息。") from exc
    if not math.isfinite(duration) or duration <= 0 or duration > MAX_AUDIO_SECONDS:
        raise ValueError(f"音频时长必须大于 0 且不超过 {MAX_AUDIO_SECONDS} 秒。")
    if rate <= 0 or channels <= 0 or channels > 8:
        raise ValueError("音频采样率或声道数无效。")
    return {"duration_seconds": duration, "sample_rate_hz": rate, "channels": channels}


def load_audio_file(path: str | Path) -> tuple[AudioData, dict[str, Any]]:
    """Decode a local file with preflight byte/duration bounds and safe FFmpeg."""
    candidate = Path(path)
    if not candidate.is_file():
        raise ValueError("请上传有效音频文件。")
    if candidate.stat().st_size <= 0 or candidate.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("音频文件必须大于 0 且不超过 16 MiB。")
    meta = _probe_audio(candidate)
    if candidate.suffix.lower() == ".wav":
        try:
            samples, rate = sf.read(candidate, dtype="float32", always_2d=True)
        except Exception as exc:
            raise ValueError("WAV 文件无法解码。") from exc
        mono = samples.mean(axis=1)
        audio = AudioData(mono.astype(np.float64), int(rate))
    else:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("AUDIO_TOOLS_UNAVAILABLE")
        with tempfile.TemporaryDirectory(prefix="v4-decode-") as folder:
            decoded = Path(folder) / "decoded.wav"
            try:
                subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(candidate),
                     "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_f32le", "-f", "wav", str(decoded)],
                    check=True, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    timeout=FFMPEG_TIMEOUT_SECONDS,
                )
                samples, rate = sf.read(decoded, dtype="float32")
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("音频解码超时。") from exc
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                raise ValueError("压缩音频无法解码。") from exc
            audio = AudioData(np.asarray(samples, dtype=np.float64), int(rate))
    if not np.all(np.isfinite(audio.samples)):
        raise ValueError("音频包含无效数值。")
    if audio.samples.size / audio.sample_rate > MAX_AUDIO_SECONDS:
        raise ValueError(f"音频时长必须不超过 {MAX_AUDIO_SECONDS} 秒。")
    meta["input_bytes"] = candidate.stat().st_size
    meta["decoded_duration_seconds"] = audio.samples.size / audio.sample_rate
    return audio, meta


def prepare_audio(audio: AudioData, *, target_sample_rate: int, duration_seconds: int) -> AudioData:
    if target_sample_rate not in (44100, 48000) or duration_seconds not in (6, 12):
        raise ValueError("后端音频配置无效。")
    divisor = math.gcd(audio.sample_rate, target_sample_rate)
    samples = audio.samples
    if divisor != audio.sample_rate or target_sample_rate != audio.sample_rate:
        samples = resample_poly(samples, target_sample_rate // divisor, audio.sample_rate // divisor)
    count = target_sample_rate * duration_seconds
    samples = np.asarray(samples[:count], dtype=np.float64)
    if samples.size < count:
        samples = np.pad(samples, (0, count - samples.size))
    return AudioData(samples, target_sample_rate)


def add_noise(audio: AudioData, *, snr_db: float, seed: int) -> AudioData:
    if not math.isfinite(snr_db) or not 0 <= snr_db <= 60:
        raise ValueError("噪声 SNR 必须在 0–60 dB。")
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("噪声种子必须是 0–4294967295 整数。")
    values = audio.samples.astype(np.float64)
    power = float(np.mean(values**2))
    if power < 1e-14:
        raise ValueError("音频过静音，无法按 SNR 添加噪声。")
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(values.shape)
    noise *= math.sqrt(power / (10 ** (snr_db / 10)) / float(np.mean(noise**2)))
    return AudioData(values + noise, audio.sample_rate)


def fixed_crop(audio: AudioData, *, start_seconds: float, duration_seconds: float) -> AudioData:
    if not math.isfinite(start_seconds) or not math.isfinite(duration_seconds) or start_seconds < 0 or duration_seconds <= 0:
        raise ValueError("裁剪起点和时长必须为非负/正数。")
    start = int(round(start_seconds * audio.sample_rate))
    count = int(round(duration_seconds * audio.sample_rate))
    stop = start + count
    if count <= 0 or stop > audio.samples.size:
        raise ValueError("裁剪区间必须完全位于音频时长内。")
    return AudioData(audio.samples[start:stop].copy(), audio.sample_rate)


def _encode_codec(audio: AudioData, codec: str, output_dir: Path, stem: str) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("AUDIO_TOOLS_UNAVAILABLE")
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / f"{stem}_source.wav"
    sf.write(source, audio.samples.astype(np.float32), audio.sample_rate, subtype="PCM_16")
    if codec == "MP3 128 kbps":
        encoded, args = output_dir / f"{stem}.mp3", ["-c:a", "libmp3lame", "-b:a", "128k"]
    elif codec == "AAC 128 kbps":
        encoded, args = output_dir / f"{stem}.m4a", ["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
    else:
        raise ValueError("请选择 MP3 或 AAC 128 kbps。")
    decoded = output_dir / f"{stem}_decoded.wav"
    started = time.perf_counter()
    try:
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-ac", "1",
                        "-ar", str(audio.sample_rate), *args, str(encoded)], check=True, shell=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=FFMPEG_TIMEOUT_SECONDS)
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(encoded), "-ac", "1",
                        "-ar", str(audio.sample_rate), "-c:a", "pcm_f32le", "-f", "wav", str(decoded)],
                       check=True, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                       timeout=FFMPEG_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("FFmpeg 编码或解码超时。") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("FFmpeg 编码或解码失败。") from exc
    samples, rate = sf.read(decoded, dtype="float32")
    samples = np.asarray(samples, dtype=np.float32)
    decoded_sample_count = int(samples.size)
    output: dict[str, Any] = {
        "audio": AudioData(samples.astype(np.float64), int(rate)),
        "play_path": str(decoded), "encoded_path": str(encoded),
        "decoded_path": str(decoded), "codec_seconds": time.perf_counter() - started,
        "encoded_bytes": encoded.stat().st_size,
        "output_duration_seconds": samples.size / int(rate),
    }
    if codec == "AAC 128 kbps":
        # This path generated the M4A itself, so FFmpeg has the muxer priming
        # metadata available. Keep its decoded start unchanged and only trim
        # trailing frame padding beyond the known source sample count. Never
        # apply this rule to an externally uploaded AAC/ADTS file.
        encoded_metadata = _probe_audio(encoded)
        if encoded_metadata["sample_rate_hz"] != audio.sample_rate or encoded_metadata["channels"] != 1:
            raise RuntimeError("AAC 编码输出的采样率或声道数与输入不匹配。")
        if decoded_sample_count < audio.samples.size:
            raise RuntimeError("AAC 解码有效样本短于输入，无法安全确定有效区间。")
        valid_sample_count = int(audio.samples.size)
        valid_samples = samples[:valid_sample_count]
        sf.write(decoded, valid_samples, int(rate), subtype="FLOAT", format="WAV")
        result = AudioData(valid_samples.astype(np.float64), int(rate))
        output.update({
            "audio": result,
            "output_duration_seconds": result.samples.size / result.sample_rate,
            "encoded_metadata": encoded_metadata,
            "decoded_sample_count_before_trim": decoded_sample_count,
            "effective_sample_range_samples": [0, valid_sample_count],
            "leading_samples_discarded": 0,
            "tail_padding_samples_removed": decoded_sample_count - valid_sample_count,
        })
    return output


def process_channel(audio: AudioData, operation: str, output_dir: Path, *, seed: int = 2026,
                    snr_db: float = 20.0, crop_start_seconds: float = 0.0,
                    crop_duration_seconds: float = 3.0) -> dict[str, Any]:
    if operation in ("MP3 128 kbps", "AAC 128 kbps"):
        result = _encode_codec(audio, operation, output_dir, "channel")
        result["details"] = f"FFmpeg {operation} encode/decode; mono {audio.sample_rate} Hz"
        return result
    if operation == "Additive noise":
        processed = add_noise(audio, snr_db=snr_db, seed=seed)
        destination = output_dir / "channel_noise.wav"
        sf.write(destination, processed.samples.astype(np.float32), processed.sample_rate, subtype="PCM_16")
        return {"audio": processed, "play_path": str(destination), "encoded_path": str(destination),
                "decoded_path": str(destination), "codec_seconds": 0.0, "encoded_bytes": destination.stat().st_size,
                "output_duration_seconds": processed.samples.size / processed.sample_rate,
                "details": f"Additive white Gaussian noise; target SNR {snr_db:.1f} dB; seed {seed}; PCM16 WAV"}
    if operation == "Fixed crop":
        processed = fixed_crop(audio, start_seconds=crop_start_seconds, duration_seconds=crop_duration_seconds)
        destination = output_dir / "channel_crop.wav"
        sf.write(destination, processed.samples.astype(np.float32), processed.sample_rate, subtype="PCM_16")
        return {"audio": processed, "play_path": str(destination), "encoded_path": str(destination),
                "decoded_path": str(destination), "codec_seconds": 0.0, "encoded_bytes": destination.stat().st_size,
                "output_duration_seconds": processed.samples.size / processed.sample_rate,
                "details": f"Crop start {crop_start_seconds:.3f} s; duration {crop_duration_seconds:.3f} s; PCM16 WAV"}
    raise ValueError("请选择有效信道操作。")


def analyze_pair(reference: AudioData, modified: AudioData, *, max_offset_seconds: float = 0.5,
                 target_sample_rate: int = 48000, min_alignment_score: float = 0.15) -> dict[str, Any]:
    if not math.isfinite(max_offset_seconds) or not 0 <= max_offset_seconds <= 15:
        raise ValueError("最大对齐偏移必须在 0–15 秒。")
    def resample_preserving_length(audio: AudioData) -> AudioData:
        if audio.sample_rate == target_sample_rate:
            return audio
        divisor = math.gcd(audio.sample_rate, target_sample_rate)
        samples = resample_poly(audio.samples, target_sample_rate // divisor,
                                audio.sample_rate // divisor)
        return AudioData(np.asarray(samples, dtype=np.float64), target_sample_rate)

    # Metrics must retain true durations; backend padding/truncation would
    # create synthetic overlap (especially for crops) and bias SNR/LSD.
    ref = resample_preserving_length(reference)
    mod = resample_preserving_length(modified)
    factor = max(1, int(round(target_sample_rate / 2000)))
    ref_ds = resample_poly(ref.samples, 1, factor)
    mod_ds = resample_poly(mod.samples, 1, factor)
    corr = signal.correlate(mod_ds, ref_ds, mode="full", method="fft")
    lags = signal.correlation_lags(mod_ds.size, ref_ds.size, mode="full")
    allowed = np.abs(lags) <= int(round(max_offset_seconds * target_sample_rate / factor))
    lags, corr = lags[allowed], corr[allowed]
    ref_start = np.maximum(-lags, 0)
    mod_start = np.maximum(lags, 0)
    overlap = np.minimum(ref_ds.size - ref_start, mod_ds.size - mod_start)
    valid = overlap >= 1000
    lags, corr, ref_start, mod_start, overlap = (a[valid] for a in (lags, corr, ref_start, mod_start, overlap))
    if lags.size == 0:
        return _unavailable_analysis(ref, mod, 0.0, 0.0, target_sample_rate)
    ref_energy = np.concatenate(([0.0], np.cumsum(ref_ds**2)))
    mod_energy = np.concatenate(([0.0], np.cumsum(mod_ds**2)))
    ref_power = ref_energy[ref_start + overlap] - ref_energy[ref_start]
    mod_power = mod_energy[mod_start + overlap] - mod_energy[mod_start]
    scores = np.abs(corr) / np.sqrt(np.maximum(ref_power * mod_power, 1e-30))
    best = int(np.argmax(scores))
    lag_samples = int(lags[best] * factor)
    score = float(scores[best])
    rs = max(-lag_samples, 0)
    ms = max(lag_samples, 0)
    count = min(ref.samples.size - rs, mod.samples.size - ms)
    x, y = ref.samples[rs:rs + count], mod.samples[ms:ms + count]
    seconds = count / target_sample_rate
    base = {"metrics_available": False, "alignment_score": score,
            "lag_seconds": lag_samples / target_sample_rate, "compared_seconds": seconds,
            "sample_rate_hz": target_sample_rate, "snr_db": None, "lsd_db": None,
            "reference_aligned": x, "modified_aligned": y}
    if score < min_alignment_score or seconds < 1.0:
        return base
    noise_power = float(np.mean((x - y) ** 2))
    signal_power = float(np.mean(x**2))
    snr = float(10 * np.log10((signal_power + 1e-30) / (noise_power + 1e-30)))
    _, _, sx = signal.stft(x, fs=target_sample_rate, window="hann", nperseg=4096, noverlap=2048,
                           boundary=None, padded=False)
    _, _, sy = signal.stft(y, fs=target_sample_rate, window="hann", nperseg=4096, noverlap=2048,
                           boundary=None, padded=False)
    mx, my = np.abs(sx), np.abs(sy)
    epsilon = max(float(mx.max()) * 1e-8, 1e-12)
    delta_db = 20 * np.log10((my + epsilon) / (mx + epsilon))
    base.update({"metrics_available": True, "snr_db": snr,
                 "lsd_db": float(np.sqrt(np.mean(delta_db**2))), "reference_aligned": x,
                 "modified_aligned": y, "reference_spectrum": mx, "modified_spectrum": my,
                 "spectral_difference_db": delta_db})
    return base


def _unavailable_analysis(ref: AudioData, mod: AudioData, lag: float, score: float, rate: int) -> dict[str, Any]:
    return {"metrics_available": False, "alignment_score": score, "lag_seconds": lag,
            "compared_seconds": 0.0, "sample_rate_hz": rate, "snr_db": None, "lsd_db": None,
            "reference_aligned": ref.samples[:0], "modified_aligned": mod.samples[:0]}


def analysis_figures(result: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Create waveform, STFT magnitude, and aligned spectral-difference figures."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    x = np.asarray(result["reference_aligned"])
    y = np.asarray(result["modified_aligned"])
    rate = int(result["sample_rate_hz"])
    if x.size == 0 or y.size == 0:
        raise ValueError("无法形成可比较的对齐音频。")
    stride = max(1, int(math.ceil(max(x.size, y.size) / 6000)))
    times = np.arange(x.size)[::stride] / rate
    wave = go.Figure()
    wave.add_trace(go.Scatter(x=times, y=x[::stride], name="Reference", mode="lines"))
    wave.add_trace(go.Scatter(x=times, y=y[::stride], name="Processed", mode="lines", opacity=0.75))
    wave.update_layout(title="Time-aligned waveform", xaxis_title="Time (s)", yaxis_title="Amplitude", template="plotly_white")

    if not result["metrics_available"]:
        empty = go.Figure().update_layout(title="STFT unavailable: alignment confidence too low", template="plotly_white")
        diff = go.Figure().update_layout(title="Spectral difference unavailable without alignment", template="plotly_white")
        return wave, empty, diff

    reference = np.asarray(result["reference_spectrum"])
    modified = np.asarray(result["modified_spectrum"])
    diff_data = np.asarray(result["spectral_difference_db"])
    frequencies = np.fft.rfftfreq(4096, 1 / rate)
    times_s = (np.arange(reference.shape[1]) * 2048 + 2048) / rate
    fstride = max(1, int(math.ceil(reference.shape[0] / 300)))
    tstride = max(1, int(math.ceil(reference.shape[1] / 500)))
    reference_db = 20 * np.log10(np.maximum(reference, 1e-12))
    modified_db = 20 * np.log10(np.maximum(modified, 1e-12))
    sub = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Reference STFT", "Processed STFT"))
    sub.add_trace(go.Heatmap(x=times_s[::tstride], y=frequencies[::fstride], z=reference_db[::fstride, ::tstride], colorscale="Viridis", showscale=False), row=1, col=1)
    sub.add_trace(go.Heatmap(x=times_s[::tstride], y=frequencies[::fstride], z=modified_db[::fstride, ::tstride], colorscale="Viridis", showscale=False), row=2, col=1)
    sub.update_layout(title="STFT magnitude (dB)", template="plotly_white", height=650)
    delta = go.Figure(go.Heatmap(x=times_s[::tstride], y=frequencies[::fstride], z=diff_data[::fstride, ::tstride], colorscale="RdBu", zmid=0))
    delta.update_layout(title="Aligned spectral difference: processed − reference (dB)", xaxis_title="Time (s)", yaxis_title="Frequency (Hz)", template="plotly_white")
    return wave, sub, delta
