# Hosted demo: container deployment

Status: **deployment files prepared; not publicly deployed or browser-tested**.

The public GitHub Pages site is a static showcase. The real QIM/FFmpeg/blind
detector runs in a separate Python container; no watermark processing can run
on GitHub Pages alone.

## Deployment bundle

- `Dockerfile`: Python 3.11, system FFmpeg, pinned GUI dependencies.
- `app/hosted.py`: Gradio bound to 0.0.0.0, port set by PORT or 7860;
  limited queue and max upload size.
- `.dockerignore`: avoid bundling local media and development files.

The Docker image builds from this repository and preserves the existing
frozen map, strength=1.28 and Hamming threshold=8.

### Test locally

```bash
docker build -t blind-audio-watermarking .
docker run --rm -p 127.0.0.1:7860:7860 blind-audio-watermarking
```

Open http://127.0.0.1:7860 and test upload → embed → MP3 → blind detection,
plus no-watermark rejection. The image was locally built and run on the
development branch; its Gradio root/config endpoints, container FFmpeg, one
6-second UESTC-003 MP3 round-trip, and no-watermark UNKNOWN path passed. This
is local container evidence only, not a public deployment or formal browser
acceptance test.

### Deployment options

Use a host supporting Docker, persistent runtime Python processes, and FFmpeg
(e.g. a user-configured Hugging Face Docker Space, Render, Railway or VPS).
Create the service under your own account, connect the public GitHub repository,
and configure its port and optional budget/spend controls. Do not publish
secrets in Git. Do not assume a free hosting plan is available.

For a Hugging Face Docker Space, create Space with SDK Docker and an
appropriate hardware tier; copy project into the Space or sync its Docker build
context, then monitor build logs. The default public endpoint for a Space is
provider-specific; **never invent a URL**.

### Production gates before enabling public uploads

1. Confirm the exact container image builds from scratch and includes FFmpeg,
   then run the generated WAV and actual 128 kbps MP3 detector contract.
2. Confirm a browser can upload, embed, compress and detect after the app is
   deployed; check 6/15/30-second modes and correct UNKNOWN rejection.
3. Verify Gradio's temp-file behavior on the deployed version. The current
   `app/gui.py` creates session directories with `tempfile.mkdtemp` and **does not
   remove them** after processing. This is a blocker for unattended public use.
   Introduce bounded TTL cleanup and per-session isolation without exposing
   arbitrary paths or weakening blind detection. Ensure Gradio's upload cache
   and user-generated audio files are both deleted on an enforced schedule.
4. Enforce audio-duration/decoded-size limits, concurrency and overall CPU/
   memory caps at the hosting layer, including oversized compressed media.
   Test abuse and error cases. Restrict app availability while these controls
   are not established.
5. Ensure no raw user-uploaded audio or filenames appear in persistent logs or
   metrics; document privacy and retention accurately.
6. Only after the live HTTPS service passes testing, set the static page
   `docs/index.html` meta tag `demo-embed-url` to the **verified** service
   URL, optionally enabling its embedded interface.
7. Update README badges and deployment status only with validated evidence.

### Important

Current site metrics come from historical Course V2 experiments; the public
container has not rerun the 48/48 and 46/48 cohorts. Identity decoding
classifies four possible labels (2 effective data bits); it is not 32-bit
general payload recovery and not cryptographic proof of authorship.
