# Selected Music Case

## Attribution

**Where You Are Now**, Benjamin Orth, featuring Wolf Fly. Source: PJRC audio test library, `SDTEST1.WAV`; original work page: ccMixter. Licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

## Source and preprocessing

- Original source format: 44.1 kHz stereo PCM, 95.166485 seconds.
- Source SHA-256: `221c71b0ec90b070c552a303fa9dd4577b2e07cff91e9461009e1bb020c0c4a6`.
- Preprocessing: arithmetic-mean stereo downmix; `scipy.signal.resample_poly` with 160/147 to 48 kHz; continuous 0–72 second crop after whole-source resampling.
- The included Original and Watermarked WAVs are 48 kHz mono float32. MP3 and AAC/M4A are real whole-file 128 kbps encodes of the 72-second watermarked WAV.
- `message_192bit.txt` records the 12 independent 16-bit messages. The detector did not receive that target during decoding; it is retained here as scoring/presentation evidence.

## Results and boundary

This is a selected showcase, not a population estimate: all 12 blocks were correctly identified in Clean, full-file MP3 128 kbps and full-file AAC-LC/M4A 128 kbps. The independent C3-16 AAC errors remain in `../../EVIDENCE_SUMMARY.md` and are not overwritten by this case. The experiment report did not include a formal listener panel; the presenter should audition the files before classroom playback.

## Figures and data

- `signal_comparison.png`: real original, watermarked waveform and residual.
- `spectrum_comparison.png`: real spectrum comparison.
- `detection_process.png`: actual block-level recovery illustration.
- CSV files contain the corresponding plotted signal, spectrum and detection values. They are derived from this exact selected case.
