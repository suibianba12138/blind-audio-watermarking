# Deployment preparation plan

## Current status

`SPACES_PREPARATION = COMPLETE` means the repository contains a conventional
Gradio entry point and dependency declaration suitable for a later review. No
Hugging Face Space was created, uploaded, or made public in this task.

## Local run

```bash
python -m app.gui
```

The app binds to `127.0.0.1`, sets no sharing flag, and uses temporary session
directories. For a controlled local run, set `GRADIO_ANALYTICS_ENABLED=False`.

The audited local environment used Python 3.13 in an isolated
`--system-site-packages` virtual environment so that the existing NumPy 2.1.3
and SciPy 1.15.3 were not upgraded. Gradio/web packages were installed into
that environment with the exact versions listed in `requirements.txt`; the
editable project was installed with `python -m pip install -e . --no-deps
--no-build-isolation`. A clean machine should use the ordinary requirements
install shown in the README and review the resolved scientific stack before
deployment.

## Future Spaces checklist

1. Resolve `LICENSE_DECISION_REQUIRED` and dataset attribution review.
2. Review the final `requirements.txt` lock policy and FFmpeg availability in
   the selected Spaces runtime.
3. Configure upload size, duration, concurrency, temporary-file cleanup, and
   process isolation at the hosting layer.
4. Run the generated-signal smoke test and an approved audio fixture inside the
   target image without changing the frozen strength, threshold, map, or
   detector contract.
5. Confirm that logs do not retain user filenames or uploaded audio.
6. Only then perform a separately authorized upload.
