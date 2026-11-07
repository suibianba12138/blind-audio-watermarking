"use strict";
/* Static recorded-evidence explorer; never initiates V4 model inference. */
(() => {
  const cases = Object.freeze({
    clean: {name:"Clean WAV",accepted:24,raw:24,note:"PCM16 WAV output re-uploaded independently to the blind detector. All 24 fixed messages were exactly recovered and accepted."},
    mp3: {name:"MP3 · 128 kbps",accepted:24,raw:24,note:"Real FFmpeg libmp3lame CBR compression and decode. All 24 fixed messages passed the frozen presence threshold."},
    aac: {name:"AAC-LC / M4A · 128 kbps",accepted:23,raw:24,note:"One correctly decoded message had confidence 0.674603, just below the frozen provisional 0.680556 threshold. It was returned as UNKNOWN, not as a wrong recovered message."}
  });
  const $ = id => document.getElementById(id);
  function setCondition(key) {
    const d = cases[key];
    if (!d) return;
    document.querySelectorAll("[data-condition]").forEach(button => {
      const active = button.dataset.condition === key;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    $("channel-result").setAttribute("aria-labelledby", "tab-" + key);
    $("successMetric").textContent = d.accepted + " / 24";
    $("percentMetric").textContent = (100*d.accepted/24).toFixed(d.accepted === 24 ? 0 : 1) + "%";
    $("conditionLabel").textContent = d.name;
    $("rawExact").textContent = d.raw + " / 24";
    $("conditionNote").textContent = d.note;
    $("meterFill").style.width = (100*d.accepted/24) + "%";
    $("resultMeter").setAttribute("aria-label", d.name + ": " + d.accepted + " of 24 correctly accepted.");
  }
  const sourceCases = Object.freeze({
    music:{n:2,note:"Music: 2 selected FMA sources, each accepted under Clean WAV, MP3 and AAC/M4A. These are selected demonstration clips."},
    speech:{n:1,note:"Speech: 1 selected LibriVox recording, accepted under all three file conditions. Source recording was originally 16 kHz."},
    environment:{n:1,note:"Environment: 1 selected FreeSound recording, accepted under all three file conditions. Source recording was originally 16 kHz."}
  });
  function setCase(key) {
    const d = sourceCases[key];
    if (!d) return;
    document.querySelectorAll("[data-case]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.case === key)));
    $("caseGrid").innerHTML = ["Clean WAV","MP3 128 kbps","AAC/M4A 128 kbps"].map(label =>
      '<article class="case-card"><small>' + label.toUpperCase() + '</small><strong>' +
      d.n + "/" + d.n + '</strong><span>Exact payload correctly accepted</span></article>'
    ).join("");
    $("caseNote").textContent = d.note + " Human A/B listening and full browser visual validation of the original Studio remain separate outstanding tasks.";
  }
  const tabs = [...document.querySelectorAll("[data-condition]")];
  tabs.forEach((b,i) => {
    b.addEventListener("click", () => setCondition(b.dataset.condition));
    b.addEventListener("keydown", e => {
      if (!["ArrowLeft","ArrowRight","Home","End"].includes(e.key)) return;
      e.preventDefault();
      let next = e.key==="Home"?0:e.key==="End"?tabs.length-1:(i+(e.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;
      tabs[next].focus();setCondition(tabs[next].dataset.condition);
    });
  });
  document.querySelectorAll("[data-case]").forEach(b => b.addEventListener("click",()=>setCase(b.dataset.case)));
  setCondition("mp3");setCase("music");
})();