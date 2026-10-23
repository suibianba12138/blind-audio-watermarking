"use strict";
/* Local audio visualization only. Never sends the selected file to any service.
   No watermark embedding or detection is performed by this static website. */
const $ = (id) => document.getElementById(id);
const audioInput = $("local-audio"), audioPlayer = $("local-player");
const canvas = $("wave-canvas"), ctx = canvas.getContext("2d");
let objectUrl = null;
let activeAudioContext = null;
function drawPlaceholder() {
  const ratio = window.devicePixelRatio || 1, width = canvas.clientWidth || 480, height = 135;
  canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
  ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,width,height);
  ctx.strokeStyle="#31516d";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,height/2);ctx.lineTo(width,height/2);ctx.stroke();
  ctx.font="11px system-ui";ctx.textAlign="center";ctx.fillStyle="#8da7bf";ctx.fillText("Select an audio file to preview its waveform",width/2,height/2-12);
}
function drawWaveform(channel) {
  const ratio=window.devicePixelRatio||1,w=canvas.clientWidth||480,h=135;
  canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);
  ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
  ctx.strokeStyle="#234560";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke();
  const step=Math.max(1,Math.floor(channel.length/w));
  ctx.strokeStyle="#69e0d0";ctx.lineWidth=1.7;ctx.beginPath();
  for(let x=0;x<w;x++){let min=1,max=-1,at=x*step;for(let i=at;i<Math.min(channel.length,at+step);i++){min=Math.min(min,channel[i]);max=Math.max(max,channel[i]);}if(min>max){min=0;max=0}ctx.moveTo(x,(1+min)*h/2);ctx.lineTo(x,(1+max)*h/2)}ctx.stroke();
}
drawPlaceholder();
window.addEventListener("resize",()=>{if(!audioInput.files?.length)drawPlaceholder()});
audioInput.addEventListener("change",async()=>{
  const file=audioInput.files?.[0];
  if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null}
  audioPlayer.removeAttribute("src"); audioPlayer.load();
  if(!file){$("file-message").textContent="No file selected · preview only";$("wave-duration").textContent="—";drawPlaceholder();return}
  if(!file.type.startsWith("audio/")&&!/\.(wav|mp3|flac|ogg|m4a|aac)$/i.test(file.name)){$("file-message").textContent="Please select an audio file.";drawPlaceholder();return}
  if(file.size>30*1024*1024){$("file-message").textContent="Local preview is limited to 30 MB.";drawPlaceholder();return}
  objectUrl=URL.createObjectURL(file);audioPlayer.src=objectUrl;
  $("file-message").textContent=file.name+" · local preview only";
  $("wave-duration").textContent="Decoding…";
  try{
    const bytes=await file.arrayBuffer();
    if(!activeAudioContext) activeAudioContext=new (window.AudioContext||window.webkitAudioContext)();
    const decoded=await activeAudioContext.decodeAudioData(bytes);
    const channel=decoded.getChannelData(0);
    drawWaveform(channel);
    $("wave-duration").textContent=decoded.duration.toFixed(1)+" s";
  }catch{
    $("wave-duration").textContent="Preview unavailable";
    $("file-message").textContent=file.name+" · browser decoder could not draw a waveform; try playback";
    drawPlaceholder();
  }
});
const menu=$("menu-toggle"),nav=$("navigation");
menu.addEventListener("click",()=>{let opened=menu.getAttribute("aria-expanded")==="true";menu.setAttribute("aria-expanded",String(!opened));nav.classList.toggle("is-open",!opened)});
nav.querySelectorAll("a").forEach(el=>el.addEventListener("click",()=>{menu.setAttribute("aria-expanded","false");nav.classList.remove("is-open")}));
/* Opt-in deployment only: configure a trusted HTTPS Gradio URL in the meta tag.
   A URL is never invented. Show an external launch link by default; iframe is optional. */
const endpoint=document.querySelector('meta[name="demo-embed-url"]')?.content?.trim()||"";
try{
  if(endpoint){
    const u=new URL(endpoint);
    if(u.protocol==="https:"&&/^[a-z0-9.-]+$/i.test(u.hostname)){
      const hosted=$("hosted-app");hosted.hidden=false;$("local-app").hidden=true;
      $("launch-app").href=u.toString();
      $("toggle-embed").addEventListener("click",()=>{
        const shell=$("embed-shell");shell.hidden=!shell.hidden;
        $("toggle-embed").textContent=shell.hidden?"Show embedded processor ↓":"Hide embedded processor ↑";
        if(!shell.hidden&&!shell.firstChild){const frame=document.createElement("iframe");frame.title="Hosted Blind Audio Watermarking processor";frame.loading="lazy";frame.referrerPolicy="no-referrer";frame.allow="microphone";frame.src=u.toString();shell.append(frame)}
      });
      const status=document.querySelector(".demo-status strong");status.textContent="HOSTED BACKEND CONFIGURED";document.querySelector(".demo-status>div>span:last-child").textContent="Use the hosted processor for real embedding and blind detection.";
    }
  }
}catch{ /* Invalid configuration keeps local-only messaging. */ }