"""Minimal CPU reproduction of Sony SilentCipher's official 44.1 kHz model.

Keep third-party code and model files outside the project. Example:
  PYTHONPATH=/path/to/silentcipher/src /path/to/python scripts/v4_p0_silentcipher_probe.py \
    --source /path/to/MUSAN/music-hd-0035.wav \
    --model-dir /path/to/Models/44_1_khz/73999_iteration \
    --output experiments/v4_p0/SILENTCIPHER_REPRODUCTION.json
"""
from __future__ import annotations
import argparse, hashlib, json, math, resource, subprocess, tempfile, time
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
import librosa


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--model-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--threads', type=int, default=4)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    from silentcipher import get_model

    model_dir = args.model_dir
    t0 = time.perf_counter()
    model = get_model(model_type='44.1k', ckpt_path=str(model_dir),
                      config_path=str(model_dir / 'hparams.yaml'), device='cpu')
    load_s = time.perf_counter() - t0
    x, source_sr = sf.read(args.source, dtype='float32', always_2d=False)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if source_sr != 44100:
        x = librosa.resample(x, orig_sr=source_sr, target_sr=44100)
    sr, n = 44100, 44100 * 12
    x = x[:n]
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))

    message = [83, 67, 86, 52, 7]
    t0 = time.perf_counter()
    marked, reported_sdr = model.encode_wav(x, sr, message, calc_sdr=True)
    encode_s = time.perf_counter() - t0
    marked = np.asarray(marked, dtype=np.float32)
    err = float(np.mean((x - marked) ** 2))
    snr = float(10 * math.log10(float(np.mean(x ** 2)) / err))
    t0 = time.perf_counter()
    clean_result = model.decode_wav(marked, sr, phase_shift_decoding=False)
    clean_decode_s = time.perf_counter() - t0

    with tempfile.TemporaryDirectory(prefix='silentcipher-p0-') as td:
        wav = Path(td) / 'marked.wav'
        mp3 = Path(td) / 'marked.mp3'
        decoded_wav = Path(td) / 'decoded.wav'
        sf.write(wav, marked, sr, subtype='PCM_16')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(wav),
                        '-ac', '1', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '128k', str(mp3)],
                       check=True, timeout=120)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp3),
                        '-ac', '1', '-ar', '44100', '-c:a', 'pcm_f32le', str(decoded_wav)],
                       check=True, timeout=120)
        mp3_audio, mp3_sr = sf.read(decoded_wav, dtype='float32')
        mp3_audio = mp3_audio[:n]
        t0 = time.perf_counter()
        mp3_result = model.decode_wav(mp3_audio, mp3_sr, phase_shift_decoding=False)
        mp3_decode_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        negative_result = model.decode_wav(x, sr, phase_shift_decoding=False)
        negative_decode_s = time.perf_counter() - t0
        mp3_bytes = mp3.stat().st_size

    data = {
        'status': 'RUNTIME_PASS_SINGLE_MUSIC_CLIP',
        'official_repository': 'sony/silentcipher',
        'official_source_commit': 'c11afe0e2df73f1ac0f848e2903b8af36e6a0b10',
        'official_release_asset': 'Models.tar.gz',
        'official_release_asset_bytes': 64389731,
        'local_archive_sha256': 'cd2beaa9824102c4bae5fe9de7b737cda2682b109ab5f2375a72f3303172af78',
        '44k_checkpoint_sha256': {
            'enc_c.ckpt': 'ff64f80d2391fdfc888e4103c499be4a2c958e59626587a1eab6db93204814c7',
            'dec_c.ckpt': 'c23b57635172b2fbd3a8531d15ba76b5885a10d0fe902ccb823c521c56041b33',
            'dec_m_0.ckpt': '829540c058270d29788f05294894d45bf436e44add0e1099422242ebb94b7088',
        },
        'python': '3.12.14', 'torch': torch.__version__, 'device': 'cpu',
        'torch_threads': args.threads, 'input_kind': 'MUSAN classical music excerpt; source 16 kHz, resampled to 44.1 kHz',
        'model_sample_rate_hz': sr, 'duration_s': 12.0, 'capacity_bits': 40,
        'message_bytes': message, 'model_load_s_warm_cache': load_s,
        'encode_s': encode_s, 'clean_decode_s': clean_decode_s,
        'mp3_decode_s': mp3_decode_s, 'negative_decode_s': negative_decode_s,
        'reported_sdr_db': float(reported_sdr), 'measured_snr_db': snr,
        'clean_decode': clean_result, 'mp3_128k_decode': mp3_result,
        'unwatermarked_negative': negative_result, 'mp3_bytes': mp3_bytes,
        'peak_rss_kib': int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        'phase_shift_decoding': False,
        'source_path_recorded': False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')
    print(json.dumps(data, indent=2, sort_keys=True, default=str))

if __name__ == '__main__':
    main()
