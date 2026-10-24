# Hosted demo: container deployment

Status: **Render Free Blueprint prepared; no hosted service created or browser-tested**.

The public GitHub Pages site is a static showcase. The real QIM/FFmpeg/blind
detector runs in a separate Python container; no watermark processing can run
on GitHub Pages alone.

## Deployment bundle

- `Dockerfile`: Python 3.11, system FFmpeg, pinned GUI dependencies.
- `app/hosted.py`: Gradio bound to 0.0.0.0, port set by PORT or 7860;
  limited queue and max upload size.
- `.dockerignore`: avoid bundling local media and development files.
- `render.yaml`: explicitly `plan: free`, Docker runtime, Singapore region,
  and manual-only deployments (`autoDeployTrigger: off`).

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

### Render Free trial — no paid resources

1. First merge the validated `feat/hosted-audio-demo` branch into `main`.
2. In Render choose **New → Blueprint**, connect this public GitHub
   repository and use the checked-in `render.yaml`.
3. Before approving, verify that **every provisioned service** is a **Free Web
   Service**, Docker runtime, no database, no persistent disk, and no paid
   add-ons. If anything shows a cost, cancel.
4. Choose the free configuration without payment details if your account permits.
   `render.yaml` explicitly pins the Free plan to avoid defaulting to paid.
5. Let Render run the initial deployment; `autoDeployTrigger: off` avoids
   auto-deploys for subsequent pushes.
6. Copy the real `onrender.com` HTTPS URL from the Render dashboard. Do not
   guess it from the service name. Confirm `/` and `/config` return a valid
   response, then perform real browser upload → embed → MP3 → blind detect.
7. Assess actual memory and cold-start behavior before promoting the link on
   GitHub Pages. Free offers 0.1 CPU and 512 MB RAM. 6-second inputs are the
   first pilot; longer modes may overload the free instance.

A Render Free instance can sleep after 15 minutes idle; wake-up may take around
a minute. Its filesystem is ephemeral, which is acceptable for short-lived
demo audio, not for persistent storage. Monitor free usage and spending limits.
If performance is poor, stop the trial rather than upgrading to a paid plan.

**One-click Blueprint entry:** https://render.com/deploy?repo=https://github.com/suibianba12138/blind-audio-watermarking

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
3. Confirm hosted session cleanup in practice: `app/session_store.py` now keeps
   each output behind an opaque token, with a 20-minute idle TTL and an 8-session
   cap. Gradio 4.44.1 has `delete_cache=(60, 1200)` for its own temporary cache.
   These controls passed local tests, **not** remote lifecycle/retention checks.
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
