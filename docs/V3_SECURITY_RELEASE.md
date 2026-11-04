# Public V3 / Legacy hosting security notes

This branch is a staging candidate. The existing hosted `main` remains
unchanged until merge; Render has `autoDeployTrigger: off`.

* Public upload service: Gradio 6.31.0 with its own matching dependencies.
* The Gradio queue has `api_open=False`, 1 default concurrent task, queue 4,
  max input 16 MiB and restricted paths for application code / system folders.
* V3 + Legacy is the default on the NEXT manually approved deployment. Set `V3_DEMO_ENABLED=0` to revert to Legacy without changing the application commit. Render `autoDeployTrigger: off` remains unchanged.
* V3 MP3 is carried as file bytes for independent blind detection.
* GitHub Actions unit and container checks must pass on the upgraded runtime.
* Do not place secrets in `render.yaml`, repository code, screenshots,
  action logs, PR comments, or public UI text. Configure service-side secrets
  only using your hosting provider's secured environment controls.
* The public algorithm's selector/seed is not a confidential authentication key.
* A literal absolute path in old public research manifests is not a secret
  credential, but should be anonymized; older Git objects remain public until
  history is deliberately rewritten and verified.
* The current demo is a prototype, not an authentication or imperceptibility
  guarantee. Formal listening evaluation has not been completed.

Reference original freeze: 8-bit MP3 128kbps accepted-exact 117/120 on
60 independent sources; one MP3-clean false positive among 60 controls.
