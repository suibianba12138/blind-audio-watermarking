"use strict";
/* V4 actual audio playback. Only explicitly verified published assets are enabled.
   Manifest is written by scripts/publish_v4_audio.py after SHA256 checks. */
(() => {
  const $ = id => document.getElementById(id);
  if (!$("v4-player-original")) return;
  const tracks={
    music_01:{
      label:"Sax & piano",source:"https://freemusicarchive.org/music/maarten-schellekens/public-domain-1/sax-and-piano-free-track/",
      scores:["1.000000","0.988095","0.984127"],snr:"48.49 dB",lsd:"3.535 dB"
    },
    music_02:{
      label:"Free To Use",source:"https://freemusicarchive.org/music/Monplaisir/Free_To_Use/Monplaisir_-_Free_To_Use_-_01_Free_To_Use_1/",
      scores:["1.000000","0.996032","0.992063"],snr:"48.48 dB",lsd:"5.241 dB"
    }
  };
  const prefix="./assets/v4-audio/";
  const names=["original","watermarked","mp3","aac"];
  const players={
    original:$("v4-player-original"),watermarked:$("v4-player-watermarked"),
    mp3:$("v4-player-mp3"),aac:$("v4-player-aac")
  };
  let selected="music_01",available={},activation=0,abSide="original";
  const status=$("v4-audio-status");
  function setStatus(message,cls){
    status.textContent=message;
    status.classList.remove("ready","unavailable");
    if(cls)status.classList.add(cls);
    $("v4-audio-availability").textContent=cls==="ready"?"AUDIO · VERIFIED FILES":cls==="unavailable"?"AUDIO · NOT YET PUBLISHED":"AUDIO · CHECKING";
  }
  function deactivate(){
    for(const player of Object.values(players)){
      player.pause();player.removeAttribute("src");player.load();
    }
    $("v4-ab-toggle").disabled=true;
    for(const name of ["mp3","aac"]){
      const a=$("v4-"+name+"-download");a.hidden=true;a.removeAttribute("href");
    }
  }
  function updateLabels(){
    document.querySelectorAll("[data-audio-track]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.audioTrack===selected)));
    const t=tracks[selected];
    ["clean","mp3","aac"].forEach((name,i)=>{ $("v4-listen-"+name).textContent=t.scores[i]; });
    $("v4-listen-snr").textContent=t.snr;
    $("v4-listen-lsd").textContent=t.lsd;
    $("v4-audio-origin").href=t.source;
  }
  async function hasFile(url){
    try{
      const res=await fetch(url,{method:"HEAD",cache:"no-store"});
      return res.ok && ((res.headers.get("content-type")||"").toLowerCase().indexOf("text/html")===-1);
    }catch{return false;}
  }
  function safeFile(value){
    return typeof value==="string" && /^music_0[12]_(original_prepared|watermarked)\.wav$|^music_0[12]_mp3_128k\.mp3$|^music_0[12]_aac_lc_m4a_128k\.m4a$/.test(value);
  }
  async function loadSelected(){
    const id=++activation;
    deactivate();updateLabels();
    const record=available[selected];
    if(!record || record.published!==true || record.validation!=="SHA256_VERIFIED"){
      setStatus("Authentic P4 A/B files have not yet been published. This player will only activate after the original WAV, marked WAV, MP3 and M4A pass the frozen SHA256 checks.","unavailable");
      return;
    }
    if(!names.every(name=>safeFile(record[name]?.file))){
      setStatus("Audio manifest is incomplete or contains an unexpected filename. Playback is disabled.","unavailable");return;
    }
    const urls={};
    for(const name of names){urls[name]=prefix+encodeURIComponent(record[name].file);}
    const checks=await Promise.all(names.map(name=>hasFile(urls[name])));
    if(id!==activation)return;
    if(checks.some(ok=>!ok)){
      setStatus("Verified audio manifest exists, but at least one media file is not available on GitHub Pages. Playback remains disabled.","unavailable");
      return;
    }
    for(const name of names)players[name].src=urls[name];
    $("v4-mp3-download").href=urls.mp3;$("v4-mp3-download").hidden=false;
    $("v4-aac-download").href=urls.aac;$("v4-aac-download").hidden=false;
    $("v4-ab-toggle").disabled=false;
    abSide="original";
    $("v4-ab-toggle").textContent="Switch A → B at playback position";
    setStatus("Four authentic P4 audio files are available for this music source. They were hash-verified against frozen experiment exports before publication. The scores beside them remain recorded detector results.","ready");
  }
  $("v4-ab-toggle").addEventListener("click",async()=>{
    const from=players[abSide],toName=abSide==="original"?"watermarked":"original",to=players[toName];
    const t=Number.isFinite(from.currentTime)?from.currentTime:0;
    const playing=!from.paused;
    from.pause();
    const max=Number.isFinite(to.duration)?to.duration:t;
    try{to.currentTime=Math.min(t,Math.max(0,max-.02));}catch{}
    abSide=toName;
    $("v4-ab-toggle").textContent=abSide==="original"?"Switch A → B at playback position":"Switch B → A at playback position";
    if(playing){try{await to.play()}catch{$("v4-audio-comparison-note").textContent="Playback was blocked by your browser. Use the player controls to continue."}}
  });
  document.querySelectorAll("[data-audio-track]").forEach(b=>b.addEventListener("click",()=>{
    selected=b.dataset.audioTrack;loadSelected();
  }));
  for(const [name,el] of Object.entries(players)){
    el.addEventListener("play",()=>{for(const [key,other] of Object.entries(players)){if(key!==name)other.pause();}});
  }
  async function init(){
    setStatus("Checking for verified V4 audio assets…");
    try{
      const resp=await fetch(prefix+"manifest.json",{cache:"no-store"});
      if(!resp.ok)throw Error("manifest unavailable");
      const data=await resp.json();
      if(data.version!==1 || data.protocol!=="P4_END_TO_END_FROZEN" || !data.tracks || typeof data.tracks!=="object")throw Error("unexpected manifest");
      available=data.tracks;
    }catch{
      available={};
    }
    loadSelected();
  }
  init();
})();