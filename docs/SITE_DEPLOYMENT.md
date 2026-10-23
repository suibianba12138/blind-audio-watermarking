# Website deployment and backend integration

This branch contains a static, RecallVision-inspired project showcase:

- docs/index.html
- docs/assets/site.css
- docs/assets/site.js

The website is **not a hosted audio watermarking engine**. Its local waveform preview uses the browser Web Audio API and keeps the uploaded file in the user's browser. The genuine Python pipeline is in the repository's Gradio app and can be run locally.

## Publishing the static website

After merging the reviewed website branch into main, configure GitHub Pages in repository Settings → Pages with **Deploy from a branch**, main branch, **/docs** folder. Wait for the Pages deployment to succeed. Do not claim that the Pages site runs embedding or detection.

The page uses relative asset URLs so that it works under a project path.

## Deploying real watermark processing

GitHub Pages cannot execute Python or FFmpeg. Deploy a separate Gradio service (such as a properly configured Hugging Face Space), with:

- server binding suitable for its deployment container, rather than the localhost-only development binding;
- exact runtime dependencies, including FFmpeg;
- payload-size and duration limits, CPU/runtime safeguards, concurrency limits and rate limiting;
- temporary file handling, deletion and no retention of users' uploaded material;
- an independent, blind detector with no expected identity supplied;
- actual user-browser testing before publishing an active Demo badge.

The static page intentionally has an empty `demo-embed-url` meta property by default. After the backend is publicly deployed, tested and trusted, set that value to the **real HTTPS Gradio app URL**. The page then reveals a hosted-app launch link and offers an optional iframe. Do not configure a speculative URL or a fake detection result.

## Scope

The historical evaluation numbers on the site are reproduced from the frozen Course V2 report and must not be described as a new website benchmark. Keep the four-identity / 2-bit information and audio-quality limitations visible.
