# V3 safe hosting integration (review candidate)

This integration is based on the existing hosted **main** and adds only the frozen 8-bit
V3 runtime modules. It preserves the existing Course V2 entrypoint and website.

## Deployment switch

- Default: `V3_DEMO_ENABLED=0` (or unset), unchanged Legacy UI.
- Opt in after acceptance: `V3_DEMO_ENABLED=1`, combined V3 + Legacy UI.

The existing `Dockerfile`, `render.yaml` and `docs/` website remain unchanged.
No new PyTorch runtime or additional paid service is needed.

## Provenance

Algorithm modules and fixed configuration were copied from
`feat/v3-8bit-integration@7fe678234e8af1d0be34a0a3e56297c7182945ff`.
Only hosting integration imports use `app.v3_session_store` to avoid changing
the existing `app.session_store` and its Legacy session safety tests.

## Verification gates

This is a **review candidate**, not a successful production deployment.
Before setting `V3_DEMO_ENABLED=1` in Render:

1. GitHub Actions unit and Docker smoke checks must pass.
2. Check the actual browser upload, download and re-upload path (Gradio HTTP-only check is not full browser acceptance).
3. Confirm cold-start, real 6-second MP3 128-kbps round trip and memory budget on Render.
4. Conduct an appropriate preliminary listening check; no formal perceptual evidence exists.
5. Preserve rollback to `V3_DEMO_ENABLED=0` and the previous known-good service commit.

Published V3 evidence: 117/120 correct accepted 8-bit MP3-128 trials on 60 sources.
The independent study observed 1/60 false positive on clean MP3 audio.
No general FPR below 1%, imperceptibility or cryptographic authentication claim is made.
