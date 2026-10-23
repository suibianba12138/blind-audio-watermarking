# Limitations

- The frozen identity results are evidence from the Course V2 validation record,
  not a new public-repository benchmark. Re-run them only with the original
  approved data and provenance process.
- The identity mode carries 2 bits of identity information. Its accuracy does
  not imply reliable recovery of arbitrary 32-bit messages.
- Formal reliability evidence covers 6 seconds / 1 block. The 15/30-second
  modes are implemented as real repeated blocks but are not promoted to a
  formal validation claim here.
- One of 60 historical identity negatives was falsely identified, at distance
  8. The public release keeps the frozen threshold and does not retune it.
- Two historical MP3 positives were rejected as UNKNOWN. The demo must expose
  this behavior rather than replace it with a cached answer.
- `FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`. Objective peak checks do not
  replace a controlled listening study.
- No raw MUSAN or other audio is distributed. Dataset terms, code ownership,
  and final software licensing require maintainer review.
- FFmpeg is an external runtime dependency. The release does not bundle a
  binary or assert a particular system build license.
- The GUI is a localhost teaching prototype. It is not a hardened multi-user
  service and has no public upload deployment in this release.
