# V4 End-to-End Performance Acceptance

**Final status: `V4_END_TO_END_STATUS = PARTIAL`**

The frozen SilentCipher path completed real upload → embed → file download → FFmpeg channel processing → independent file re-upload → blind detection for two music excerpts, one speech excerpt and one environment recording. All 12 positive file/condition checks (four sources × Clean/MP3/AAC) returned the newly chosen 40-bit message with `IDENTIFIED`. An unwatermarked speech file returned `UNKNOWN`. The limiter-free exported results also survived the P8 AAC/M4A path after a small PCM16 peak-safety correction described below.

Status remains **PARTIAL** because this session could not attach the in-app browser runtime, so the page layout and physical browser interaction were not checked, and the generated A/B files have not received human listening review. SNR/LSD do not substitute for listening.

## 1. Frozen configuration

- Backend: official Sony SilentCipher, 44.1 kHz, 40-bit payload, 12-second mono model input.
- `message_sdr`: 47 dB, verified in the official checkpoint `hparams.yaml`; no model parameter or checkpoint was changed.
- Decoder: official hard decoder, phase-shift search disabled.
- Presence policy: P1 threshold `0.6805555373430252`, still provisional; `status=True` alone is not treated as presence.
- V3 and its frozen DSP settings remain untouched. This acceptance covered the neural Studio path.
- FFmpeg: 6.1.1-3ubuntu5. MP3 CBR 128 kbps; AAC-LC 128 kbps in M4A using the P8 Studio channel handler.
- All three checkpoint file hashes matched the P9 frozen result. No weight was downloaded or edited.
- A new legal payload, `A4D97E216B`, was fixed before this run. It is not one of the P1/P9 fixed messages. The detector endpoint received only each uploaded received file and backend selection. Exact-match comparison was performed offline after the response; it was not sent to `/detect`.

## 2. Sources and protocol

The source manifest and full machine-readable result are saved under [`experiments/v4_end_to_end_acceptance/`](../../../experiments/v4_end_to_end_acceptance/). The source files were verified against their frozen manifest hashes before cropping. The four 12-second mono input WAVs, all Studio downloads, decoded Channel Lab playback files and A/B pairs are retained locally in that directory. These are demonstration cases selected from previously used, licensed recordings, not a performance sample or a generalization estimate.

| Source | Kind / input rate | Crop | License | Full source SHA256 | Uploaded crop SHA256 |
|---|---|---:|---|---|---|
| `music_01` | FMA music, 44.1 kHz MP3 source | 18.745 s | CC0 1.0, source track page in manifest | `83b8c88b10bbb21788636bccca8f0aa6817d195ef91557507d0981f323865ff1` | `c7436d25a4dcb27321561eeb13289e6fb92d2fcfa491516d20a6bba8efe51af8` |
| `music_02` | FMA music, 44.1 kHz MP3 source | 1.173 s | CC0 1.0, source track page in manifest | `44c5a2df842e3dcee420e391a39170e5f94e62d1031521c8851bc796917b4a12` | `a432beb6ebc9bf668cf7e899c2d9f5afd3efbfd0357e16cb3fdbde3aa7257c25` |
| `speech-librivox-0004` | Speech, native 16 kHz WAV | 20 s | Public Domain per MUSAN/LibriVox license | `76965f20b10ce0ed48beed1670d8c5ed81182a2bc797ed5e4d7dbe24c4c58ae8` | `cff8ebe055d76589b92453a1830ccfd0ad70936400a8767e1ca8a1162c68e789` |
| `noise-free-sound-0005` | Environment, native 16 kHz WAV | 2 s | Public Domain per local MUSAN/FreeSound license | `71a5ca36940fc9ee6ba1571c7f36b30bf192ddf1783bd31d1205acfb9fea5bf6` | `9f053c1c0e1159c7d63e38c0d4f262e02877364ccce61ba64f813eafe2be5a99` |

The two music sources are the previously validated high-rate FMA items available locally. They are 44.1 kHz MP3 sources, not lossless masters. Speech and environment were read at native 16 kHz and resampled once by the Studio preparation path to 44.1 kHz.

## 3. Real Studio operation results

These operations went through the running Gradio service’s `/embed`, `/channel`, `/detect` and `/analyze` HTTP endpoints. Every WAV/MP3/M4A was downloaded to a local file and uploaded again as a separate detection request. The detector did not receive a reference, known message, session state or ground truth.

| Source | Clean WAV | MP3 128 kbps | AAC-LC/M4A 128 kbps | Embed CPU / returned SNR | Aligned LSD |
|---|---|---|---|---:|---:|
| `music_01` | `IDENTIFIED`, exact, 1.000000 | `IDENTIFIED`, exact, 0.988095 | `IDENTIFIED`, exact, 0.984127 | 4.54 s / 48.49 dB | 3.535 dB |
| `music_02` | `IDENTIFIED`, exact, 1.000000 | `IDENTIFIED`, exact, 0.996032 | `IDENTIFIED`, exact, 0.992063 | 3.46 s / 48.50 dB | 5.241 dB |
| `speech-librivox-0004` | `IDENTIFIED`, exact, 1.000000 | `IDENTIFIED`, exact, 0.992063 | `IDENTIFIED`, exact, 0.960317 | 3.47 s / 48.88 dB | 6.102 dB |
| `noise-free-sound-0005` | `IDENTIFIED`, exact, 1.000000 | `IDENTIFIED`, exact, 1.000000 | `IDENTIFIED`, exact, 1.000000 | 3.43 s / 48.35 dB | 5.750 dB |

All 12 positive cases returned `A4D97E216B` and were correctly accepted. There were no wrong-message accepts. Each decode took about 6.09–6.39 seconds end-to-end through the local API. The Channel Lab’s own codec times were approximately 0.16–0.18 seconds for MP3 and 0.21–0.25 seconds for M4A. The four-case run took 103.57 seconds in total, including uploads, embeds, channel operations, detections and analysis callbacks. Model initialization was reported as 0.04 seconds in the warm local process.

The M4A files were 44.1 kHz mono and reported 12.000 s; each Channel Lab decoded playback WAV contained exactly 529,200 samples (12 seconds). MP3 container duration was 12.042449 s due to codec framing; the Studio decoded playback WAV was also exactly 529,200 samples. AAC used M4A metadata-aware decode and the P8 trailing-padding rule; no ADTS path or fixed 1,024-sample trim was involved.

### Saved output hashes

| Source | Downloaded watermarked WAV SHA256 | MP3 128k SHA256 | AAC/M4A SHA256 |
|---|---|---|---|
| `music_01` | `85289a63aa3dcdb257b6a9df5e8f9179ebeb94814b48327a5a617debbc08f0` | `30ed55cdc13e30f887dfa1e11e197c6e53c42c1b8ce458d5de9a9f6daf08ce2b` | `18fd87b6f8400facd260484a00794582baee9d2f650203e2698855e0c860cd35` |
| `music_02` | `98fe7c41dfccc29166bdbcf771962f3758db93fc183d22e3a589a7c2fead917a` | `9af756799508b227405cc747550b1a78b4b588ff0b5980e3c86feeca483f4f5c` | `30a89c1163c475086f4620936a3a182db51cfa9f257e87868bd7df1c4134189f` |
| `speech-librivox-0004` | `436deef2de6928807dce2763f2ef7ff4d8afe5bcf8bb32afc423c825d8ba1f88` | `f2063f2c3a678d98ada8fba033ef460c9fd9c6ac5685bfea37faade53cb41051` | `0355077d1b1c4aefe291c066391305a07ea18b5d61e2532f61e953ba7a063e26` |
| `noise-free-sound-0005` | `0851edc061d4427d46d856e92b33b04c3c242a0b393251f57063fdb56b8202dc` | `4d1c4661303beab78afc46a6b2c320f2c04abfbdef9e63c8921a52e96dfa42a1` | `f3a4489b63f02da0e7aaef00c1e60bf1fab55fefee454d9ffc9e7c4915f3ffac` |

The JSON inventory also contains hashes for prepared originals and decoded Channel Lab playback WAVs.

## 4. Negative case, invalid inputs and repeated operations

- A separate `/detect` upload of the unwatermarked `speech-librivox-0004` crop returned `UNKNOWN`, with no candidate and no score. It was the same source recording as the positive speech case, so this is a functional negative control, not an independent-source false-acceptance study.
- Invalid 40-bit message text was rejected before model execution; output files were empty and the UI returned a safe validation message.
- A text file uploaded to detection returned `DECODE_ERROR` with a safe audio-read message; no path or traceback was exposed.
- Four sequential source runs each completed embedding, two real codec operations, three separate file-based detections and signal analysis. This confirms repeated request handling for this short local smoke run; it is not a load or concurrency test.

## 5. Signal analysis and listening

The Signal Analysis endpoint returned three non-empty Plotly figures for each source: aligned waveforms, STFT magnitude comparison and spectral difference. It reported 12.00 seconds compared and zero estimated lag for each same-length Clean/marked pair. Its metrics compare the prepared original with the exported watermarked WAV after bounded alignment and common-rate analysis; they do not measure the MP3 or M4A files.

Exported PCM16 SNR was 48.35–48.87 dB. LSD was 3.535–6.102 dB. Watermarked peak magnitude after the output safety step was 0.605–0.994. No saved output had a full-scale PCM16 sample or a newly clipped sample. These results are engineering measurements, not proof of perceptual transparency. A/B pairs are saved as `listen_ab/<source>_A_original.wav` and `listen_ab/<source>_B_watermarked.wav`; human listening is **pending**. In particular, the three LSD values above 5 dB should be reviewed by listening before claiming good subjective fidelity.

## 6. Minimal issue found and correction

The first run showed six new full-scale samples in the environment watermarked WAV after PCM16 export (the original excerpt already contained nine). The model output was being cast directly to PCM16, which can hard-clip samples above full scale. A bounded correction was added in `app/v4_audio_processing.py::pcm16_safe_pair()` and called by the Watermark callback: when either member of the original/marked pair exceeds the safe PCM16 peak, apply one common linear gain to both before saving. This is not a per-sample limiter and does not change the model, message strength, detector or presence policy.

For the environment clip the shared gain was `0.882616`; the exported pair then had zero full-scale samples, while clean/MP3/AAC detection remained successful. Other cases used gain 1.000000. Two new unit tests cover the overrange and unchanged-in-range paths. The end-to-end four-source regression was rerun after this correction.

The existing external compressed-file path still decodes non-WAV files to 48 kHz before SilentCipher preparation resamples them to 44.1 kHz. P10 documented this redundant conversion; its bounded comparison did not change the detection state. This round also passed through that path for all 8 compressed positive files. It was not changed because this acceptance did not show a detection failure attributable to it.

## 7. Studio page coverage

| Studio page | Fresh runtime coverage | Result |
|---|---|---|
| Watermark | Four licensed uploads; new 40-bit message; downloaded prepared original and watermarked PCM16 WAV | API pass; four embeds |
| Channel Lab | Re-upload downloaded marked WAV; actual FFmpeg MP3 and AAC/M4A; retain encoded download and decoded playback WAV | API pass; all 8 channel files generated |
| Blind Detection | Separately re-upload Clean, MP3 and M4A files; upload unwatermarked speech and invalid text | API pass; 12 exact identified, negative UNKNOWN, invalid `DECODE_ERROR` |
| Signal Analysis | Upload prepared original and downloaded marked WAV | API pass; 12 Plotly figures total and aligned metrics |

Browser/visual acceptance was **not completed**. The in-app browser control attempt failed because the browser runtime did not expose its `agent` binding in this session. Gradio HTTP API calls exercise the live callbacks and actual file transfers, but they are not represented as a browser click-through or visual review.

## 8. Verification and remaining limits

- Relevant P2/P4 and peak-safety unit tests: 18/18 passed when run as targeted suites (P2: 4, P4: 12, peak safety: 2).
- A broad `test_v4_*.py` discovery also attempted an unrelated existing TensorFlow test module which could not import `pytest`; `pytest` was not installed as part of this acceptance. This does not invalidate the targeted results or live API run.
- The V3 checkout remained on its existing branch and clean; no V3 algorithm or online service was touched.
- P0–P11 result files and official weights were not modified.
- The demonstration is intentionally selected and small: 4 source recordings, one new message, one negative recording. It does not establish general reliability or a false-acceptance rate.
- Browser layout and file-picker interactions remain unchecked here; human A/B audition remains pending; SNR/LSD alone do not clear subjective audio quality.
- The P1 presence threshold remains provisional. The local demo should show unknown/failure states faithfully and should not imply population-level detection guarantees.

## 9. Final decision

`V4_END_TO_END_STATUS = PARTIAL`

The current local Studio produced repeatable real-message recovery for the selected music, speech and environment examples across Clean, MP3 128 kbps and AAC-LC/M4A 128 kbps. File-based blind detection, the negative case and Signal Analysis callbacks worked after downloaded files were re-uploaded. The export clipping issue was corrected with a shared peak-safe gain and the complete smoke run passed again.

The system is suitable for a **local technical demo with these saved clips**, but it is not fully accepted as an audio-quality showcase until a human listens to the A/B pairs and a real browser pass verifies page interaction, playback and downloads. Do not generalize the selected examples to overall robustness.
