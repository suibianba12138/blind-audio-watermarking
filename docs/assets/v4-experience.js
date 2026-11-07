"use strict";
/* All detector responses are copied from frozen P4 and P9 records.
   The console displays recorded results; it never invokes a watermarking model. */
(() => {
  const P4_URL = "https://github.com/suibianba12138/blind-audio-watermarking/blob/upgrade/v4-github-prep/experiments/v4_end_to_end_acceptance/results.json";
  const P9_URL = "https://github.com/suibianba12138/blind-audio-watermarking/blob/upgrade/v4-github-prep/docs/reports/v4/V4_P9_DETECTION_RELIABILITY_REPORT.md";
  const THRESHOLD = 0.680556;
  const MESSAGE = "A4D97E216B";
  const RECORDS = Object.freeze({
    music_01: {
      label: "MUSIC_01", category:"Music / 01", snr:48.486343, lsd:3.535,
      clean_wav:{score:1.000000,time:6.180431},
      mp3_128k:{score:0.988095,time:6.136543},
      aac_lc_m4a_128k:{score:0.984127,time:6.277591}
    },
    music_02: {
      label:"MUSIC_02",category:"Music / 02",snr:48.477309,lsd:5.241,
      clean_wav:{score:1.000000,time:6.348934},
      mp3_128k:{score:0.996032,time:6.292285},
      aac_lc_m4a_128k:{score:0.992063,time:6.341193}
    },
    "speech-librivox-0004":{
      label:"SPEECH_01",category:"Speech / 01",snr:48.873287,lsd:6.102,
      clean_wav:{score:1.000000,time:6.341314},
      mp3_128k:{score:0.992063,time:6.389740},
      aac_lc_m4a_128k:{score:0.960317,time:6.391216}
    },
    "noise-free-sound-0005":{
      label:"ENVIRONMENT_01",category:"Environment / 01",snr:48.351121,lsd:5.750,
      clean_wav:{score:1.000000,time:6.293903},
      mp3_128k:{score:1.000000,time:6.090209},
      aac_lc_m4a_128k:{score:1.000000,time:6.236998}
    }
  });
  const CODECS = Object.freeze({clean_wav:"CLEAN WAV",mp3_128k:"MP3 128K",aac_lc_m4a_128k:"AAC/M4A 128K"});
  const $=id=>document.getElementById(id);
  let record="music_01",codec="aac_lc_m4a_128k",special=null,runTimer=null;
  const bitHost=$("fingerprintBits");
  if(!bitHost) return;
  const bits=[...MESSAGE.matchAll(/../g)].map(([h])=>parseInt(h,16).toString(2).padStart(8,"0")).join("");
  bits.split("").forEach((b,i)=>{
    const bar=document.createElement("span");
    bar.className=b==="1"?"bit-one":"bit-zero";
    bar.style.height=(b==="1"? 37+(i%4)*14: 12+(i%3)*7)+"%";
    bar.title="Bit "+(i+1)+": "+b;
    bitHost.appendChild(bar);
  });
  function spaced(hex) {return hex?hex.match(/.{1,2}/g).join(" "):"NO MESSAGE";}
  function syncControls(){
    document.querySelectorAll("[data-record]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.record===record)));
    document.querySelectorAll("[data-codec]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.codec===codec)));
    document.querySelectorAll("[data-special]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.special===special)));
  }
  function selectionData(){
    if(special==="p9")return {
      id:"P9 · MUSIC_COMMONS_01 · AAC",
      state:"UNKNOWN", sent:"C3056AF18E",received:"C3056AF18E",score:.674603,
      snr:null,lsd:null,time:null,
      explanation:"The official decoder recovered all 40 bits correctly, but its 0.674603 score was below the frozen 0.680556 presence gate. The detector therefore correctly reported UNKNOWN. This is a false negative in watermark presence, not a payload bit error.",
      provenance:"SOURCE: P9 / 12-SOURCE RELIABILITY EVALUATION",url:P9_URL
    };
    if(special==="negative")return {
      id:"P4 · UNWATERMARKED SPEECH · CLEAN",
      state:"UNKNOWN",sent:null,received:null,score:null,snr:null,lsd:null,time:6.286104,
      explanation:"An independently uploaded unwatermarked speech recording produced UNKNOWN with no candidate. There is no embedded payload to recover. This is a functional negative control, not a formal false-accept-rate estimate.",
      provenance:"SOURCE: P4 / NEGATIVE CONTROL",url:P4_URL
    };
    const r=RECORDS[record],v=r[codec];
    return {
      id:"P4 · "+r.label+" · "+CODECS[codec],state:"IDENTIFIED",sent:MESSAGE,received:MESSAGE,score:v.score,
      snr:r.snr,lsd:r.lsd,time:v.time,
      explanation:"The downloaded "+CODECS[codec]+" file was uploaded separately. The blind detector recovered the exact 5-byte message and accepted it using the frozen provisional presence gate. The reference audio and expected message were not provided to the detector.",
      provenance:"SOURCE: P4 END-TO-END / "+r.label,url:P4_URL
    };
  }
  function render(){
    const d=selectionData();
    $("v4-record-id").textContent=d.id;
    $("v4-result-state").textContent=d.state;
    const stateLine=document.querySelector(".v4-console-statusline");
    stateLine.classList.toggle("is-unknown",d.state!=="IDENTIFIED");
    $("v4-tx-payload").textContent=spaced(d.sent);
    $("v4-rx-payload").textContent=spaced(d.received);
    $("v4-rx-payload").classList.toggle("rejected",d.state!=="IDENTIFIED");
    $("v4-rx-label").textContent=d.state==="UNKNOWN"?"DECODER CANDIDATE / NOT AN ACCEPTED WATERMARK":"INDEPENDENTLY RECOVERED MESSAGE";
    $("v4-confidence").textContent=d.score===null?"N/A":d.score.toFixed(6);
    const marker=$("v4-scale-marker");marker.classList.toggle("no-score",d.score===null);
    if(d.score!==null)marker.style.left=(d.score*100)+"%";
    $("v4-score-scale").setAttribute("aria-label",d.score===null?"No candidate score; presence threshold 0.680556":"Detection score "+d.score.toFixed(6)+"; presence threshold 0.680556");
    $("v4-snr").textContent=d.snr===null?"N/A":d.snr.toFixed(2)+" dB";
    $("v4-lsd").textContent=d.lsd===null?"N/A":d.lsd.toFixed(3)+" dB";
    $("v4-runtime").textContent=d.time===null?"N/A":d.time.toFixed(2)+" s";
    $("v4-result-explanation").textContent=d.explanation;
    $("v4-result-explanation").classList.toggle("is-unknown",d.state!=="IDENTIFIED");
    $("v4-provenance").textContent=d.provenance;
    $("v4-source-link").href=d.url;
    syncControls();
  }
  function replay(){
    clearTimeout(runTimer);
    const consoleNode=document.querySelector(".v4-lab-console"),button=$("v4-replay-run");
    consoleNode.classList.add("replaying");
    button.disabled=true;
    $("v4-result-state").textContent="REPLAYING RECORD";
    runTimer=setTimeout(()=>{
      consoleNode.classList.remove("replaying");
      button.disabled=false;
      render();
    },340);
  }
  document.querySelectorAll("[data-record]").forEach(button=>button.addEventListener("click",()=>{
    record=button.dataset.record;special=null;replay();
  }));
  document.querySelectorAll("[data-codec]").forEach(button=>button.addEventListener("click",()=>{
    codec=button.dataset.codec;special=null;replay();
  }));
  document.querySelectorAll("[data-special]").forEach(button=>button.addEventListener("click",()=>{
    special=button.dataset.special;replay();
  }));
  $("v4-replay-run").addEventListener("click",replay);
  render();
})();