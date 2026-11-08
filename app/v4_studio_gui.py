"""Local-only Gradio Blocks UI for Robust Audio Watermarking Studio."""
from __future__ import annotations

import atexit
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np
import soundfile as sf

from .audio_io import AudioData
from .v4_audio_processing import (
    MAX_UPLOAD_BYTES, add_noise, analysis_figures, analyze_pair, fixed_crop,
    load_audio_file, parse_payload, prepare_audio, process_channel, pcm16_safe_pair,
)
from .v4_backends import detect, embed
from .v4_tempfiles import ArtifactStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_TEMP_BASE = os.environ.get("V4_STUDIO_TMP_ROOT")
if _TEMP_BASE:
    Path(_TEMP_BASE).mkdir(mode=0o700, parents=True, exist_ok=True)
    _RUN_TEMP_ROOT = tempfile.mkdtemp(prefix="v4-studio-run-", dir=_TEMP_BASE)
    os.chmod(_RUN_TEMP_ROOT, 0o700)
else:
    _RUN_TEMP_ROOT = None
STORE = ArtifactStore(_RUN_TEMP_ROOT, ttl_seconds=3600)
# Keep Gradio's own upload/output cache inside the same private lifecycle root.
os.environ["GRADIO_TEMP_DIR"] = str(STORE.root / "gradio")
Path(os.environ["GRADIO_TEMP_DIR"]).mkdir(mode=0o700, parents=True, exist_ok=True)
atexit.register(STORE.cleanup)

BACKEND_INFO = {
    "Advanced Neural": "SilentCipher official frozen weights · 40 bit / 5 bytes · mono 44.1 kHz · 12 s",
    "Classic DSP": "Frozen V3 FFT/QIM + REAL_TOP32 + Soft-Code · 8 bit / 1 byte · mono 48 kHz · 6 s",
}


def _safe_path(path: str | None) -> Path:
    if not path:
        raise ValueError("请先上传音频文件。")
    candidate = Path(path)
    if not candidate.is_file() or candidate.stat().st_size <= 0 or candidate.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("音频文件无效或超过 16 MiB 限制。")
    return candidate


def _write_audio(job: Path, name: str, audio: AudioData) -> str:
    target = STORE.checked_path(job, name)
    sf.write(target, audio.samples.astype(np.float32), audio.sample_rate, subtype="PCM_16")
    return str(target)


def _new_job() -> Path:
    STORE.cleanup_expired()
    cache = Path(os.environ["GRADIO_TEMP_DIR"])
    now = time.time()
    for child in cache.iterdir():
        if child.is_symlink():
            continue
        if now - child.stat().st_mtime > STORE.ttl_seconds:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            elif child.is_file():
                child.unlink(missing_ok=True)
    return STORE.new_job()


def _error_text(exc: BaseException) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, TimeoutError):
        return "处理超时，请使用较短音频或稍后重试。"
    logging.getLogger(__name__).warning("request failed category=%s", type(exc).__name__)
    return "处理失败（内部错误已隐藏）。请确认本地音频工具和模型配置。"


def embed_callback(upload, backend: str, message: str):
    job = None
    try:
        source = _safe_path(upload)
        payload = parse_payload(backend, message)
        audio, input_info = load_audio_file(source)
        sr, seconds = (44100, 12) if backend == "Advanced Neural" else (48000, 6)
        prepared = prepare_audio(audio, target_sample_rate=sr, duration_seconds=seconds)
        job = _new_job()
        result = embed(backend, prepared.samples, payload, sr)
        original_samples, marked_samples, export_gain = pcm16_safe_pair(
            prepared.samples, np.asarray(result["audio"], dtype=np.float64))
        original = AudioData(original_samples, sr)
        marked = AudioData(marked_samples, sr)
        original_path = _write_audio(job, "original_prepared.wav", original)
        marked_path = _write_audio(job, "watermarked.wav", marked)
        msg_display = bytes(payload).hex().upper() if isinstance(payload, bytes) else f"{payload:02X}"
        load_time = result.get("model_load_seconds")
        load_detail = "model initialization not applicable" if load_time is None else f"model initialization recorded {load_time:.2f} s"
        summary = (f"Embedded · {backend} · message {msg_display} · {sr} Hz / {seconds} s · "
                   f"SNR {result['embedding_snr_db']:.2f} dB · {result['seconds']:.2f} s CPU · {load_detail} · "
                   f"PCM16 shared peak gain {export_gain:.6f} · "
                   f"input {input_info['sample_rate_hz']} Hz, {input_info['duration_seconds']:.2f} s")
        return original_path, marked_path, marked_path, summary
    except Exception as exc:
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        return None, None, None, _error_text(exc)


def channel_callback(upload, operation: str, seed: int, noise_snr: float,
                     crop_start: float, crop_duration: float):
    job = None
    try:
        source = _safe_path(upload)
        audio, meta = load_audio_file(source)
        job = _new_job()
        result = process_channel(audio, operation, job, seed=seed, snr_db=noise_snr,
                                 crop_start_seconds=crop_start, crop_duration_seconds=crop_duration)
        encoded = result["encoded_path"]
        details = (f"{result['details']} · output {Path(encoded).suffix.upper()} · "
                   f"{result['output_duration_seconds']:.2f} s · {result['encoded_bytes']} bytes · "
                   f"{result['codec_seconds']:.2f} s · input {meta['sample_rate_hz']} Hz, "
                   f"{meta['duration_seconds']:.2f} s. Channel availability does not imply watermark robustness.")
        return result["play_path"], encoded, details
    except Exception as exc:
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        return None, None, _error_text(exc)


def blind_detect_callback(upload, backend: str):
    """Independent detection: no message, original, or embed-session arguments."""
    try:
        source = _safe_path(upload)
        audio, meta = load_audio_file(source)
        sr, seconds = (44100, 12) if backend == "Advanced Neural" else (48000, 6)
        prepared = prepare_audio(audio, target_sample_rate=sr, duration_seconds=seconds)
        result = detect(backend, prepared.samples, sr)
        candidate = result.get("candidate")
        if backend == "Advanced Neural":
            decoded = bytes(candidate).hex().upper() if candidate is not None else "None"
        else:
            decoded = f"{candidate:02X}" if candidate is not None else "None"
        confidence = result.get("confidence")
        score = "unavailable" if confidence is None else f"{confidence:.6f}"
        status = result.get("state", "DECODE_ERROR")
        text = (f"{status}\nCandidate decode (diagnostic): {decoded}\nScore: {score}\n"
                f"Policy: {result.get('presence_calibration', 'unknown')}\n"
                f"Presence threshold: {result.get('presence_threshold', result.get('threshold', 'n/a'))}\n"
                f"Detection CPU: {result.get('seconds', 0):.2f} s · loaded input {meta['duration_seconds']:.2f} s")
        return text
    except Exception as exc:
        return f"DECODE_ERROR\n{_error_text(exc)}"


def analysis_callback(reference_upload, modified_upload, max_offset: float):
    try:
        reference, ref_meta = load_audio_file(_safe_path(reference_upload))
        modified, mod_meta = load_audio_file(_safe_path(modified_upload))
        result = analyze_pair(reference, modified, max_offset_seconds=max_offset)
        wave, spectra, difference = analysis_figures(result)
        if result["metrics_available"]:
            metrics = (f"Aligned SNR: {result['snr_db']:.2f} dB · LSD: {result['lsd_db']:.3f} dB · "
                       f"lag: {result['lag_seconds']:+.4f} s · compared: {result['compared_seconds']:.2f} s")
        else:
            metrics = (f"SNR/LSD unavailable: alignment confidence {result['alignment_score']:.3f} below policy; "
                       "do not interpret unaligned metrics. "
                       f"Estimated lag {result['lag_seconds']:+.4f} s; compared {result['compared_seconds']:.2f} s")
        metadata = (f"Reference {ref_meta['sample_rate_hz']} Hz / {ref_meta['duration_seconds']:.2f} s; "
                    f"processed {mod_meta['sample_rate_hz']} Hz / {mod_meta['duration_seconds']:.2f} s; "
                    "analysis resampled to 48 kHz and used bounded cross-correlation alignment.")
        return wave, spectra, difference, metrics + "\n" + metadata
    except Exception as exc:
        return None, None, None, _error_text(exc)


def build_demo():
    import gradio as gr

    # Visual-only redesign: callbacks, backend contracts and API names stay frozen.
    from .v4_studio_theme import STUDIO_CSS, STUDIO_HERO, STUDIO_FOOTER, section_intro

    with gr.Blocks(title="Robust Audio Watermarking Studio") as demo:
        gr.HTML(STUDIO_HERO)
        with gr.Tab("Watermark"):
            gr.HTML(section_intro(
                "01", "MESSAGE EMBEDDING", "Embed a watermark",
                "Select the neural 40-bit model or the frozen 8-bit DSP baseline. "
                "Upload a source, enter the payload, then compare and download the marked WAV."
            ))
            with gr.Row(equal_height=False):
                with gr.Column(scale=5, elem_classes=["nsk-panel"]):
                    gr.HTML('<div class="nsk-panel__heading">INPUT / PAYLOAD</div>'
                            '<p class="nsk-panel__hint">Neural: <strong>10 hex digits</strong> '
                            '(40 bit) · Classic: <strong>0–255</strong> (8 bit)</p>')
                    backend = gr.Radio(list(BACKEND_INFO), value="Advanced Neural",
                                       label="Watermark backend")
                    backend_info = gr.Markdown(BACKEND_INFO["Advanced Neural"])
                    backend.change(lambda x: BACKEND_INFO[x], backend, backend_info,
                                   api_name="backend_info")
                    source = gr.File(label="Upload source audio", file_types=["audio"],
                                     type="filepath")
                    message = gr.Textbox(value="123456789A",
                                         label="Message · Neural: 10 hex digits / Classic: integer 0–255")
                    embed_button = gr.Button("Embed watermark →", variant="primary",
                                             elem_classes=["nsk-action"])
                with gr.Column(scale=6, elem_classes=["nsk-panel"]):
                    gr.HTML('<div class="nsk-panel__heading">AUDIO / RESULT</div>'
                            '<p class="nsk-panel__hint">Listen to the prepared original and '
                            'the watermarked export at a consistent playback volume.</p>')
                    with gr.Row():
                        original_player = gr.Audio(label="Prepared original", type="filepath")
                        marked_player = gr.Audio(label="Watermarked audio", type="filepath")
                    marked_download = gr.File(label="Download watermarked WAV")
                    embed_status = gr.Textbox(label="Embedding details", interactive=False,
                                              lines=4, elem_classes=["nsk-results"])
            embed_button.click(embed_callback, [source, backend, message],
                               [original_player, marked_player, marked_download, embed_status],
                               concurrency_limit=1, api_name="embed")

        with gr.Tab("Channel Lab"):
            gr.HTML(section_intro(
                "02", "AUDIO CHANNEL", "Test a transmission channel",
                "Apply a real MP3/AAC codec round trip or a diagnostic transform. "
                "Download the output and send it to Blind Detection as an independent file."
            ))
            with gr.Row(equal_height=False):
                with gr.Column(scale=5, elem_classes=["nsk-panel"]):
                    gr.HTML('<div class="nsk-panel__heading">CHANNEL CONFIGURATION</div>')
                    channel_input = gr.File(label="Upload watermarked WAV", file_types=["audio"],
                                            type="filepath")
                    operation = gr.Dropdown(
                        ["MP3 128 kbps", "AAC 128 kbps", "Additive noise", "Fixed crop"],
                        value="MP3 128 kbps", label="Channel operation"
                    )
                    with gr.Row():
                        seed = gr.Number(value=2026, precision=0, label="Noise seed")
                        noise_snr = gr.Slider(0, 60, value=20, step=1,
                                              label="Noise target SNR (dB)")
                    with gr.Row():
                        crop_start = gr.Number(value=0.0, label="Crop start (s)")
                        crop_duration = gr.Number(value=3.0, label="Crop duration (s)")
                    channel_button = gr.Button("Apply channel →", variant="primary",
                                                elem_classes=["nsk-action"])
                with gr.Column(scale=6, elem_classes=["nsk-panel"]):
                    gr.HTML('<div class="nsk-panel__heading">PROCESSED OUTPUT</div>')
                    channel_player = gr.Audio(label="Processed audio", type="filepath")
                    channel_download = gr.File(label="Download processed output")
                    channel_details = gr.Textbox(
                        label="Applied operation and parameters", interactive=False,
                        lines=4, elem_classes=["nsk-results"]
                    )
                    gr.HTML('<div class="nsk-quiet-note"><strong>Scope:</strong> '
                            'MP3/AAC are verified on selected full-length 12 s clips. '
                            'Noise and crop are experimental stressors and may break recovery.</div>')
            channel_button.click(
                channel_callback,
                [channel_input, operation, seed, noise_snr, crop_start, crop_duration],
                [channel_player, channel_download, channel_details],
                concurrency_limit=1, api_name="channel"
            )

        with gr.Tab("Blind Detection"):
            gr.HTML(section_intro(
                "03", "INDEPENDENT DECODING", "Recover the hidden message",
                "Upload a received WAV, MP3 or M4A file separately. "
                "Detection has no access to the original audio, expected message or embed session."
            ))
            with gr.Row(equal_height=False):
                with gr.Column(scale=5, elem_classes=["nsk-panel"]):
                    gr.HTML('<div class="nsk-panel__heading">RECEIVED AUDIO</div>')
                    detect_backend = gr.Radio(
                        list(BACKEND_INFO), value="Advanced Neural",
                        label="Detection backend"
                    )
                    received = gr.File(label="Received audio", file_types=["audio"],
                                        type="filepath")
                    detect_button = gr.Button("Blind detect →", variant="primary",
                                               elem_classes=["nsk-action"])
                with gr.Column(scale=6, elem_classes=["nsk-panel"]):
                    gr.HTML('<div class="nsk-panel__heading">DETECTION RESULT</div>')
                    detect_output = gr.Textbox(
                        label="Detection state and diagnostic candidate", lines=7,
                        interactive=False, elem_classes=["nsk-result-status"]
                    )
                    gr.HTML('<div class="nsk-quiet-note"><strong>Interpretation:</strong> '
                            '<code>IDENTIFIED</code> is an accepted watermark; '
                            '<code>UNKNOWN</code> is not accepted. Diagnostic candidates '
                            'below the provisional threshold are not identified messages.</div>')
            detect_button.click(blind_detect_callback, [received, detect_backend],
                                [detect_output], concurrency_limit=1, api_name="detect")

        with gr.Tab("Signal Analysis"):
            gr.HTML(section_intro(
                "04", "DIGITAL SIGNAL PROCESSING", "Inspect waveform and spectrum",
                "Compare the reference and processed file with bounded temporal alignment. "
                "Inspect signal quality using SNR, log-spectral distance and STFT views."
            ))
            with gr.Column(elem_classes=["nsk-panel"]):
                with gr.Row():
                    reference = gr.File(label="Reference / original audio",
                                         file_types=["audio"], type="filepath")
                    modified = gr.File(label="Watermarked / processed audio",
                                        file_types=["audio"], type="filepath")
                max_offset = gr.Slider(0, 2, value=0.5, step=0.05,
                                        label="Maximum alignment offset (s)")
                analyze_button = gr.Button("Analyze aligned signals →", variant="primary",
                                            elem_classes=["nsk-action"])
                metrics = gr.Textbox(
                    label="Aligned quality metrics and audio metadata", lines=4,
                    interactive=False, elem_classes=["nsk-results"]
                )
            with gr.Row():
                wave_plot = gr.Plot(label="Aligned waveforms", elem_classes=["nsk-plot"])
                spectrum_plot = gr.Plot(label="STFT magnitude comparison",
                                        elem_classes=["nsk-plot"])
            difference_plot = gr.Plot(label="Aligned spectral difference",
                                      elem_classes=["nsk-plot"])
            gr.HTML('<div class="nsk-quiet-note">SNR and LSD are objective engineering '
                    'metrics, not proof of inaudibility. Metrics are withheld when '
                    'alignment is insufficient.</div>')
            analyze_button.click(
                analysis_callback, [reference, modified, max_offset],
                [wave_plot, spectrum_plot, difference_plot, metrics],
                concurrency_limit=1, api_name="analyze"
            )

        gr.HTML(STUDIO_FOOTER)
    return demo.queue(default_concurrency_limit=1, max_size=4)


def main():
    import gradio as gr

    from .v4_studio_theme import STUDIO_CSS

    demo = build_demo()
    demo.launch(server_name="127.0.0.1", server_port=int(os.environ.get("V4_STUDIO_PORT", "7862")),
                share=False, show_error=False, inbrowser=False, max_threads=1, max_file_size="16mb",
                theme=gr.themes.Soft(), css=STUDIO_CSS)


if __name__ == "__main__":
    main()
