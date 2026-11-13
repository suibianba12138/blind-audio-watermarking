# C2/C3 Online Laboratory

An optional **real** FastAPI/FFmpeg backend for the public DSP course release. The existing `course_watermark.c2` and `.c3` implementations are imported directly and **not modified**. This service does not use the frozen evaluation key.

## API

- `GET /healthz` — liveness check; `GET /api/v1/info` — supported modes / limits.
- `POST /api/v1/embed` (`mode`, `message`, `key`, `source=sample|upload`, optional `reference` file) → actual float32 `watermarked.wav`.
- `POST /api/v1/process` (`channel`, `seconds=6|72`, `audio` file) → actual processed WAV, MP3 or AAC file.
- `POST /api/v1/detect` (`mode`, `key`, `source=sample|upload`, optional `reference` and required `received`) → JSON with recovered payload, presence statistic, similarity and block results. The detector **never receives the expected message**.

Modes: `c2-8`, `c3-16`, `c2-long-id` (72 seconds), `c3-192` (72 seconds).

Channels: `clean`, `mp3`, `aac`, `mp3_aac`, `gain_minus6`, `gain_plus3`, `resample` (48 → 44.1 → 48 kHz). MP3 and AAC are real FFmpeg 128 kbps encodes. The server prepares uploaded source recordings as 48 kHz mono and uses the initial 6/72 seconds.

A 72-second execution is resource intensive, especially on free CPU instances. The server uses **one worker and one in-flight CPU operation**. Responses may be slower than the static showcase. File uploads are limited to 32 MiB/file, and rate limiting is applied. A Render instance should have a suitably configured free/paid tier depending on usage.

## Local run

From repository root:

```bash
python -m pip install -e 'course_release[online,test]'
uvicorn course_release.online.app:app --host 127.0.0.1 --port 10000
```

Install FFmpeg separately; use `python -m pytest course_release/online/tests -q` for the smoke checks. `course_release/Dockerfile.online` is for a **new isolated Render service**, not the existing V3 Dockerfile.

## Privacy and security notes

- Server-side uploads and intermediate files use request-scoped temporary directories and are deleted after the request. No database; no media or keys saved intentionally.
- **No logging of filenames, payloads or keys** by the application. Standard infrastructure request logs may still record IP/timestamps.
- Cross-origin browser calls are limited to configured trusted site origins. This is **not an authentication mechanism**.
- Anonymous access is CPU-expensive, so file limits, request rate limits, and a single compute slot apply; production use should add an authentication layer, abuse monitoring and per-user quotas.
- Audio must be owned or licensed for processing. Do not upload private recordings to a public free-tier demonstration if a local run is preferable.
- This is a classroom **reference-assisted** watermark tool. It does not prove ownership, offer blind decoding, or reproduce historical results created using the withheld evaluation key.

## Deploy

Create a **new** Render Docker web service (free trial tier only if available):

```text
Repo: suibianba12138/blind-audio-watermarking
Branch: main (after reviewed merge)
Dockerfile: course_release/Dockerfile.online
Docker context: .
Health path: /healthz
Region: singapore
Environment: AUDIO_ALLOWED_ORIGINS=https://shengkaini.com,https://www.shengkaini.com,https://suibianba12138.github.io
```

Do **not** modify the existing historical V3 Render service. The static project site can enable `online-lab.js` only after `/api/v1/info` and end-to-end processing are verified against the new service URL.
