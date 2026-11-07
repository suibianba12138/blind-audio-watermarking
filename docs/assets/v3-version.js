"use strict";
/* Exact frozen V3 Soft-Code encoder, independently verified against b1_soft.py
   from feat/v3-8bit-integration. This shows encoding only. */
(() => {
 const slider=document.getElementById("v3-message-slider");
 const input=document.getElementById("v3-message-number");
 const bar=document.getElementById("v3-codebar");
 const bitsOut=document.getElementById("v3-message-bits");
 const codeOut=document.getElementById("v3-code-text");
 if(!slider||!input||!bar)return;
 function encode(value){
   const bits=Array.from({length:8},(_,i)=>(value>>(7-i))&1);
   const code=Array.from({length:32},(_,index)=>{
     const x=Array.from({length:5},(_,i)=>(index>>i)&1);
     const basis=[1,...x,x[0]&x[1],x[0]&x[2]];
     return basis.reduce((acc,b,i)=>acc ^ (b & bits[i]),0);
   });
   return {bits,code};
 }
 function render(value){
   const num=Number(value);if(!Number.isFinite(num)||num<0||num>255||!Number.isInteger(num))return;
   slider.value=String(num);input.value=String(num);
   const {bits,code}=encode(num);
   bitsOut.textContent=bits.join("");
   const groups=code.join("").match(/.{8}/g);
   codeOut.textContent=groups.join(" ");
   bar.replaceChildren();
   code.forEach((bit,index)=>{
     const s=document.createElement("span");
     s.className=bit?"high":"mid";
     s.title="Physical bit "+(index+1)+": "+bit;
     bar.appendChild(s);
   });
   bar.setAttribute("aria-label","32 physical bits for message "+num+": "+code.join(""));
 }
 slider.addEventListener("input",()=>render(slider.value));
 input.addEventListener("change",()=>{const n=Number(input.value);if(Number.isInteger(n)&&n>=0&&n<=255)render(n);else render(slider.value)});
 render(173);
})();