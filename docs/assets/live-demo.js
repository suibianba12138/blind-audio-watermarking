/* Lazy-load the real Render Gradio backend only after user interaction. */
(function(){
  "use strict";
  const url = document.querySelector('meta[name="demo-embed-url"]')?.content?.trim();
  const button = document.getElementById("load-live-demo");
  const container = document.getElementById("live-iframe-container");
  const shell = document.getElementById("live-frame");
  const status = document.getElementById("live-frame-status");
  if (!button || !container || !shell || !url) return;
  let trusted = false;
  try {const u = new URL(url); trusted = u.protocol==="https:" && u.hostname==="blind-audio-watermarking-demo.onrender.com";}catch{}
  if (!trusted) {button.disabled=true;button.textContent="Live endpoint unavailable";return;}
  button.addEventListener("click",()=>{
    const open=shell.hidden;
    shell.hidden=!open;
    button.setAttribute("aria-expanded",String(open));
    button.innerHTML=open?'Hide embedded demo <span aria-hidden="true">↑</span>':'Load demo inside this page <span aria-hidden="true">↓</span>';
    if(open && !container.querySelector("iframe")){
      status.textContent="Connecting · free service may be sleeping";
      const frame=document.createElement("iframe");
      frame.title="Render-hosted audio watermarking processor";
      frame.src=url;
      frame.loading="lazy";
      frame.referrerPolicy="no-referrer";
      frame.allow="microphone";
      frame.addEventListener("load",()=>{status.textContent="Frame loaded · verify interactive workflow inside";});
      container.append(frame);
    }
    if(open) shell.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"instant":"smooth",block:"start"});
  });
})();
