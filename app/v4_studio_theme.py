"""Visual system shared with the Embodied Semantic Communication project page.

The selectors are scoped to our own elements or documented Gradio root/role hooks.
This file contains no third-party assets or external network dependencies.
"""

STUDIO_CSS = r"""
/* Project-page tokens, adapted from embodied-semantic-communication/website/css/styles.css */
.gradio-container {
  --nsk-paper: #fafafa;
  --nsk-white: #ffffff;
  --nsk-ink: #182228;
  --nsk-sub: #53616d;
  --nsk-faint: #697984;
  --nsk-line: #e0e5e8;
  --nsk-blue: #2766a5;
  --nsk-teal: #187e7e;
  --nsk-teal-dark: #236f79;
  --nsk-mint: #eaf6f3;
  --nsk-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --nsk-sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-family: var(--nsk-sans) !important;
  color: var(--nsk-ink);
  background: var(--nsk-paper) !important;
}
.gradio-container .main {
  max-width: 1164px;
  margin-inline: auto;
  padding-inline: clamp(14px, 3vw, 28px);
}
.gradio-container .nsk-hero {
  padding: clamp(24px, 4.5vw, 56px) 0 30px;
  border-bottom: 1px solid var(--nsk-line);
  margin-bottom: 10px;
}
.gradio-container .nsk-hero__top {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
  margin-bottom: 53px; flex-wrap: wrap;
}
.gradio-container .nsk-brand {
  font-size: 13px; font-weight: 750; letter-spacing: .01em; color: var(--nsk-ink);
}
.gradio-container .nsk-brand b {
  color: var(--nsk-teal); font-weight: 800; margin-right: 9px;
  font-family: var(--nsk-mono);
}
.gradio-container .nsk-hero__links { display: flex; gap: 20px; flex-wrap: wrap; }
.gradio-container .nsk-hero__links a {
  font-size: 12px; font-weight: 650; color: var(--nsk-sub);
  text-decoration: none;
}
.gradio-container .nsk-hero__links a:hover { color: var(--nsk-teal); text-decoration: underline; }
.gradio-container .nsk-kicker {
  font: 750 10px/1.7 var(--nsk-mono); letter-spacing: 1.4px;
  text-transform: uppercase; color: var(--nsk-teal);
}
.gradio-container .nsk-hero h1 {
  color: var(--nsk-ink); font-size: clamp(36px, 5vw, 58px);
  font-weight: 760; line-height: 1.13; letter-spacing: -2px;
  max-width: 930px; margin: 15px 0 14px;
}
.gradio-container .nsk-hero__lead {
  color: #475b69; font-size: clamp(15px, 1.65vw, 20px);
  line-height: 1.58; max-width: 800px;
}
.gradio-container .nsk-hero__secondary {
  color: var(--nsk-faint); font-size: 13px; margin-top: 10px;
}
.gradio-container .nsk-hero__facts {
  display: flex; flex-wrap: wrap; gap: 9px; margin-top: 27px;
}
.gradio-container .nsk-fact {
  display: inline-flex; align-items: baseline; gap: 10px;
  padding: 9px 13px; background: #fff;
  border: 1px solid var(--nsk-line); border-radius: 6px;
  font-size: 12px; color: var(--nsk-sub);
}
.gradio-container .nsk-fact strong {
  font: 750 13px var(--nsk-mono); color: var(--nsk-teal-dark);
}
.gradio-container .nsk-flow {
  display: grid; grid-template-columns: repeat(4, minmax(0,1fr));
  margin: 20px 0 2px; border: 1px solid var(--nsk-line);
  border-radius: 7px; overflow: hidden; background: #fff;
}
.gradio-container .nsk-flow__step {
  padding: 13px 14px; border-right: 1px solid var(--nsk-line);
}
.gradio-container .nsk-flow__step:last-child { border-right: 0; }
.gradio-container .nsk-flow__step small {
  display: block; color: var(--nsk-teal);
  font: 700 10px/1.6 var(--nsk-mono); letter-spacing: .5px;
}
.gradio-container .nsk-flow__step strong {
  display: block; color: var(--nsk-ink); font-size: 13px; margin: 4px 0 3px;
}
.gradio-container .nsk-flow__step span {
  display: block; color: var(--nsk-faint); font-size: 11px; line-height: 1.5;
}
.gradio-container .nsk-section {
  padding: 21px 0 9px;
}
.gradio-container .nsk-section h2 {
  font-size: clamp(22px, 2.8vw, 30px); line-height: 1.22;
  color: var(--nsk-ink); font-weight: 740; letter-spacing: -.7px;
  margin: 5px 0 8px;
}
.gradio-container .nsk-section p {
  color: var(--nsk-sub); font-size: 13px; line-height: 1.75;
  max-width: 820px;
}
.gradio-container .nsk-panel {
  background: var(--nsk-white) !important;
  border: 1px solid var(--nsk-line) !important;
  border-radius: 8px !important;
  padding: clamp(13px, 2vw, 23px) !important;
  min-width: 0;
}
.gradio-container .nsk-panel__heading {
  margin-bottom: 9px; font: 730 13px var(--nsk-sans);
  color: var(--nsk-ink);
}
.gradio-container .nsk-panel__hint {
  font-size: 11px; color: var(--nsk-faint); margin: 0 0 14px;
  line-height: 1.6;
}
.gradio-container .nsk-panel__hint strong { color: var(--nsk-teal-dark); }
.gradio-container .nsk-quiet-note {
  padding: 12px 14px; border: 1px solid #c4dedb;
  background: #f1f9f7; color: #375965;
  font-size: 12px; line-height: 1.65; border-radius: 6px;
}
.gradio-container .nsk-quiet-note strong { color: #196c72; }
.gradio-container .nsk-results textarea {
  font-family: var(--nsk-mono) !important;
  font-size: 12px !important; line-height: 1.85 !important;
}
.gradio-container .nsk-result-status textarea {
  font-family: var(--nsk-mono) !important; font-size: 13px !important;
  line-height: 1.8 !important;
}
.gradio-container .nsk-action button,
.gradio-container button.nsk-action {
  background: var(--nsk-teal-dark) !important;
  border-color: var(--nsk-teal-dark) !important;
  color: white !important; border-radius: 6px !important;
  font-weight: 650 !important;
}
.gradio-container .nsk-action button:hover,
.gradio-container button.nsk-action:hover {
  background: #185a62 !important;
}
.gradio-container :is(button, input, textarea, select, a):focus-visible {
  outline: 2px solid #449fb1 !important;
  outline-offset: 2px;
}
.gradio-container :is(.nsk-panel, .nsk-plot) :is(input, textarea) {
  border-radius: 5px;
}
.gradio-container .nsk-panel :is(.gr-box, .block) { border-radius: 6px; }
.gradio-container .nsk-plot {
  background: #fff; border: 1px solid var(--nsk-line);
  border-radius: 6px;
}
.gradio-container [role="tablist"] {
  gap: 7px; border-bottom: 1px solid var(--nsk-line);
  flex-wrap: wrap;
}
.gradio-container [role="tablist"] button {
  color: #415b69; font-size: 13px; font-weight: 650;
  border-radius: 6px 6px 0 0;
}
.gradio-container [role="tablist"] button[aria-selected="true"] {
  background: var(--nsk-mint) !important;
  color: #196c72 !important;
  border-bottom: 2px solid var(--nsk-teal) !important;
}
.gradio-container .nsk-footer {
  border-top: 1px solid var(--nsk-line); padding: 20px 0 36px;
  margin-top: 34px; color: #7b8b93; font-size: 11px;
  display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px;
}
.gradio-container .nsk-footer a { color: var(--nsk-blue); text-decoration: none; }
.gradio-container .nsk-footer a:hover { text-decoration: underline; }
@media(max-width:760px) {
 .gradio-container .nsk-hero__top { margin-bottom: 34px; }
 .gradio-container .nsk-hero h1 { letter-spacing: -1.2px; }
 .gradio-container .nsk-flow { grid-template-columns: repeat(2,minmax(0,1fr)); }
 .gradio-container .nsk-flow__step:nth-child(2) { border-right: 0; }
 .gradio-container .nsk-flow__step:nth-child(-n+2) { border-bottom: 1px solid var(--nsk-line); }
 .gradio-container .nsk-hero__links { gap: 13px; }
}
@media(max-width:420px) {
 .gradio-container .nsk-flow { grid-template-columns: 1fr; }
 .gradio-container .nsk-flow__step { border-bottom: 1px solid var(--nsk-line); border-right: 0; }
 .gradio-container .nsk-flow__step:last-child { border-bottom: 0; }
 .gradio-container .nsk-fact { width: 100%; justify-content: space-between; }
}
@media(prefers-reduced-motion:reduce) {
 .gradio-container * { transition: none !important; animation: none !important; }
}
"""

STUDIO_HERO = """
<header class="nsk-hero">
  <div class="nsk-hero__top">
    <span class="nsk-brand"><b>NSK</b> / AUDIO WATERMARKING</span>
    <nav class="nsk-hero__links" aria-label="Project links">
      <a href="https://shengkaini.com/embodied-semantic-communication/" target="_blank" rel="noopener noreferrer">Project family ↗</a>
      <a href="https://github.com/suibianba12138/blind-audio-watermarking" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
    </nav>
  </div>
  <div class="nsk-kicker">DIGITAL SIGNAL PROCESSING · INTERACTIVE STUDIO</div>
  <h1>Robust Audio<br>Watermarking Studio</h1>
  <p class="nsk-hero__lead">Embed a message into audio, test real compression channels,
  and recover it independently—without the original signal at the detector.</p>
  <p class="nsk-hero__secondary">盲音频水印实验平台 · 真实 MP3/AAC 信道 · 时域与频域分析</p>
  <div class="nsk-hero__facts" aria-label="System capabilities">
    <span class="nsk-fact"><strong>40 bit</strong> Neural payload</span>
    <span class="nsk-fact"><strong>MP3 / AAC</strong> Codec lab</span>
    <span class="nsk-fact"><strong>CPU</strong> Local execution</span>
    <span class="nsk-fact"><strong>8 bit</strong> Classic DSP baseline</span>
  </div>
  <div class="nsk-flow" aria-label="Four-stage watermarking workflow">
    <div class="nsk-flow__step"><small>01 / EMBED</small><strong>Watermark</strong><span>Prepare a source and insert a message</span></div>
    <div class="nsk-flow__step"><small>02 / TRANSMIT</small><strong>Channel Lab</strong><span>Export real MP3 or AAC files</span></div>
    <div class="nsk-flow__step"><small>03 / RECOVER</small><strong>Blind Detection</strong><span>Upload received audio independently</span></div>
    <div class="nsk-flow__step"><small>04 / INSPECT</small><strong>Signal Analysis</strong><span>Compare waveform, STFT and distortion</span></div>
  </div>
</header>
"""

STUDIO_FOOTER = """
<footer class="nsk-footer">
  <span>Robust Audio Watermarking Studio · Communication Engineering</span>
  <span>Local research demonstration · Selected codec tests are not universal guarantees</span>
  <a href="https://github.com/suibianba12138/blind-audio-watermarking" target="_blank" rel="noopener noreferrer">Source / Documentation ↗</a>
</footer>
"""


def section_intro(number: str, kicker: str, title: str, detail: str) -> str:
    """Render fixed, developer-authored section text (not user input)."""
    return (
        '<header class="nsk-section">'
        f'<div class="nsk-kicker">{number} / {kicker}</div>'
        f'<h2>{title}</h2>'
        f'<p>{detail}</p>'
        '</header>'
    )
