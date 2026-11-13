# Third-Party Notices

## Music showcase

**Where You Are Now**, Benjamin Orth, featuring Wolf Fly. Source: [PJRC audio test library](https://www.pjrc.com/teensy/td_libs_AudioDataFiles.html), file `SDTEST1.WAV`; original work: [ccMixter](https://www.ccmixter.org/files/Benjamin_Orth/33036). Licensed under [Creative Commons Attribution 3.0 (CC BY 3.0)](https://creativecommons.org/licenses/by/3.0/).

The included 72-second excerpt was downmixed, resampled, cropped, watermarked, and encoded for a course demonstration. Included derivatives retain this attribution. Source SHA-256: `221c71b0ec90b070c552a303fa9dd4577b2e07cff91e9461009e1bb020c0c4a6`.

## Software dependencies

- NumPy — BSD-3-Clause.
- SciPy — BSD-3-Clause.
- FFmpeg is an external executable and is not bundled. Its build may use codecs with separate licensing terms; verify the installed build and local requirements before redistribution.

## Algorithms and provenance

The C2 and C3 modules are course DSP implementations authored by the project contributors and released under the accompanying MIT license. The packaged modules require the caller to supply a key; the frozen evaluation keys are intentionally omitted. Only the key field provisioning differs from the frozen source. DSP operations, frequency bands, embedding strength, detection scoring, and thresholds are not changed.
