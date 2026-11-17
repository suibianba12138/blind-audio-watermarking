(()=>{
'use strict';
const $=id=>document.getElementById(id);
const API='https://dsp-audio-watermark-api.onrender.com/api/v1/';
const SAMPLE='https://cdn.jsdelivr.net/gh/suibianba12138/blind-audio-watermarking@main/course_release/media/selected_c3_16_showcase/Original.wav';
const FS=48000,N=2048,CHUNK=288000,COUNT=141;
const PAIRS=[[[900,2200],[2200,3500]],[[3500,5000],[5000,6500]],[[6500,8000],[8000,9500]]];
const MESSAGES={'c2-8':'A7','c3-16':'A7C3','c2-long-id':'12345678','c3-192':'D42DEE6FA235F3C07531FD862283452DCB56FF6A8F621E41'};
const descriptions=[
 ['从整段原始音频开始','原音不是一个抽象文件，它是一串随时间变化的采样值。我们先找到待处理的声音。','原始声音的振幅随时间怎样变化？','原始波形是全部处理的起点；接下来我们从其中取出一段。'],
 ['把声音切成一帧一帧','把每个 6 秒块切成 141 个非重叠分析帧，每帧 2048 个样本。点击绿色高亮区域或移动滑块，观察被选中的小片段。','FFT 实际处理的是哪 2048 个样本？','被选中的小窗口，正是下一步 FFT 的输入。'],
 ['让一个时间窗口变成频谱','同一段 2048 点波形，左边显示时域采样，右边计算它的 FFT 频谱。这里不会混用其他时间位置。','同一帧里，哪些频率成分更强？','FFT 不会改变声音，只是把它从时间的角度转换到频率的角度观察。'],
 ['在三组频带对中嵌入信息','选中频带对 A / B，绿色和蓝色区域对应算法使用的真实频带；微小能量变化可以用放大的相对能量读数看清。','信息究竟写进了哪些频率区域？','本算法通过改变频带之间的相对能量嵌入信息，而不是把某一个频率点替换成 bit。'],
 ['把修改后的频谱还原为音频','现在对比真实输入 WAV 和这次生成的水印 WAV。两条波形通常很接近，所以用一张独立缩放的差分图显示细微修改。','加入水印后，原来的声音改变了多少？','水印是一段幅度很小的信号修改；差分图会放大显示，不代表听到的声音突然变大。'],
 ['让水印音频经过真实信道','对刚生成的水印 WAV 运行你选择的 MP3、AAC、增益或重采样。观察当前音频处理前后频谱的变化。','经过编码和处理，哪些频率发生了变化？','信道处理会改变音频。检测器需要从这种变化后的声音中恢复消息。'],
 ['通过参考辅助检测恢复消息','检测器拿到接收音、对应原音和密钥，重新统计频带变化，恢复候选消息并判断是否接受。这里显示本次服务端返回的结果。','真实处理之后，消息还能恢复出来吗？','显示的是本次检测结果：通过存在性判定与消息是否恰好正确，不是同一个概念。']
];
const s={step:0,mode:'guided',block:0,frame:0,pair:0,seconds:6,original:null,marked:null,received:null,markedBlob:null,receivedBlob:null,report:null,config:null,busy:false,progress:0,auto:false,timer:null,env:null,urls:[],processingLabel:'Clean'};
const status=(message,kind='')=>{$('status').textContent=message;$('status').className='status '+kind};
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const time=t=>String(Math.floor(t/60)).padStart(2,'0')+':'+(t%60).toFixed(3).padStart(6,'0');
const phase=(id,state)=>{let el=$(id);el.className=state||'';const names={'state-prep':'读取原音','state-embed':'水印嵌入','state-process':'信道处理','state-detect':'消息检测'};el.textContent=names[id]+' · '+({running:'进行中',done:'已完成',failed:'失败'}[state]||'未开始')};
function readConfig(){const mode=$('mode').value,source=$('source').value,file=$('upload').files[0],key=$('key').value,payload=$('payload').value.trim().replace(/^0x/i,'').toUpperCase(),channel=$('channel').value;
if(!new RegExp('^[0-9A-F]{'+MESSAGES[mode].length+'}$').test(payload))throw Error('此模式需要 '+MESSAGES[mode].length+' 位十六进制消息');
if(key.length<4||key.length>100)throw Error('密钥长度应为 4–100 个字符');
if(source==='upload'&&!file)throw Error('请先选择自己的音频文件');
return{mode,source,file,key,payload,channel,seconds:['c2-long-id','c3-192'].includes(mode)?72:6}
}
function baseForm(c){let d=new FormData();d.append('mode',c.mode);d.append('source',c.source);d.append('key',c.key);if(c.source==='upload')d.append('reference',c.file,c.file.name);return d}
async function post(endpoint,form){let r=await fetch(API+endpoint,{method:'POST',body:form,cache:'no-store'});if(!r.ok){let msg='HTTP '+r.status;try{const e=await r.json();if(typeof e.detail==='string')msg=e.detail}catch{}throw Error(msg)}return r}
async function decodeArray(buffer){const ctx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:FS});try{const audio=await ctx.decodeAudioData(buffer.slice(0));const target=new Float32Array(s.seconds*FS),length=Math.min(target.length,audio.length);for(let c=0;c<audio.numberOfChannels;c++){const data=audio.getChannelData(c);for(let i=0;i<length;i++)target[i]+=data[i]/audio.numberOfChannels}return target}finally{await ctx.close()}}
async function decodeBlob(blob){return decodeArray(await blob.arrayBuffer())}
async function sourceAudio(c){if(c.source==='upload')return decodeBlob(c.file);let r=await fetch(SAMPLE,{cache:'force-cache'});if(!r.ok)throw Error('未能加载示例音乐 WAV：HTTP '+r.status);return decodeArray(await r.arrayBuffer())}
function audible(element,link,blob,name){let url=URL.createObjectURL(blob);s.urls.push(url);$(element).src=url;$(element).load();$(link).href=url;$(link).download=name;$(link).hidden=false}
function clear(){stopAuto();for(let url of s.urls)URL.revokeObjectURL(url);s.urls=[];s.original=null;s.marked=null;s.received=null;s.markedBlob=null;s.receivedBlob=null;s.env=null;s.report=null;s.config=null;s.block=0;s.frame=0;s.progress=0;
for(const id of ['markedAudio','channelAudio']){$(id).pause();$(id).removeAttribute('src');$(id).load()}
$('markedLink').hidden=true;$('channelLink').hidden=true;
for(const id of ['state-prep','state-embed','state-process','state-detect'])phase(id,'');
render()}
function env(samples){let segments=900,arr=[];for(let k=0;k<segments;k++){let lo=1,hi=-1,start=Math.floor(k*samples.length/segments),end=Math.ceil((k+1)*samples.length/segments);for(let j=start;j<end&&j<samples.length;j++){const v=samples[j];lo=Math.min(lo,v);hi=Math.max(hi,v)}arr.push([lo,hi])}return arr}
function chooseFrame(){s.frame=clamp(s.frame,0,140);s.block=clamp(s.block,0,s.seconds/6-1)}
function fillBlocks(){const b=$('block');b.replaceChildren();for(let i=0;i<s.seconds/6;i++){const opt=document.createElement('option');opt.value=i;opt.textContent='第 '+(i+1)+' 块 · '+(i*6)+'–'+(i*6+6)+' s';b.append(opt)}}
async function run(){if(s.busy)return;let c;try{c=readConfig()}catch(e){status(e.message,'error');return}clear();s.seconds=c.seconds;fillBlocks();s.busy=true;$('run').disabled=true;s.step=0;status('开始当前实验：首先读取这次选择的原音…');phase('state-prep','running');
try{
 s.original=await sourceAudio(c);s.env=env(s.original);phase('state-prep','done');s.progress=1;render();
 phase('state-embed','running');status('原音已读取，可以查看波形和 FFT。正在调用原始 C2/C3 算法进行真实水印嵌入…');
 const emb=baseForm(c);emb.append('message',c.payload);const r=await post('embed',emb);s.markedBlob=await r.blob();s.marked=await decodeBlob(s.markedBlob);s.config=c;s.progress=4;
 audible('markedAudio','markedLink',s.markedBlob,'watermarked-'+c.mode+'.wav');phase('state-embed','done');s.step=1;render();
 const args=new FormData();args.append('channel',c.channel);args.append('seconds',String(c.seconds));args.append('audio',s.markedBlob,'watermarked.wav');
 phase('state-process','running');status('真实水印音频已生成；正在执行 '+$('channel').selectedOptions[0].textContent+' 信道处理…');
 const proc=await post('process',args);s.receivedBlob=await proc.blob();s.received=await decodeBlob(s.receivedBlob);const ext=c.channel==='mp3'?'mp3':c.channel==='aac'||c.channel==='mp3_aac'?'m4a':'wav';
 audible('channelAudio','channelLink',s.receivedBlob,'received-'+c.channel+'.'+ext);s.processingLabel=$('channel').selectedOptions[0].textContent;
 phase('state-process','done');s.progress=5;phase('state-detect','running');status('信道输出已经生成。正在运行真实参考辅助检测…');render();
 const det=baseForm(c);det.append('received',s.receivedBlob,'received.'+ext);const response=await post('detect',det);s.report=await response.json();s.progress=7;phase('state-detect','done');
 status('本次实验全部完成：'+s.report.status+'，'+s.report.accepted_blocks+'/'+s.report.block_count+' 个块通过。现在开始逐步观察真实结果。','good');setStage(0);$('lab').scrollIntoView({behavior:'smooth',block:'start'});startAuto();
}catch(e){let phaseId=!s.original?'state-prep':!s.marked?'state-embed':!s.received?'state-process':'state-detect';phase(phaseId,'failed');status('本次运行中断：'+e.message+'。已完成的步骤仍可查看。','error');render()}
finally{s.busy=false;$('run').disabled=false}
}
function signal(samples,offset){const a=new Float64Array(N);if(samples)for(let i=0;i<N&&offset+i<samples.length;i++)a[i]=samples[offset+i];return a}
function fft(samples){let re=new Float64Array(samples),im=new Float64Array(N);for(let i=1,j=0;i<N;i++){let bit=N>>1;for(;j&bit;bit>>=1)j^=bit;if(i<j){let tmp=re[i];re[i]=re[j];re[j]=tmp}}
for(let len=2;len<=N;len<<=1){const theta=-2*Math.PI/len,wcos=Math.cos(theta),wsin=Math.sin(theta);for(let i=0;i<N;i+=len){let ur=1,ui=0;for(let j=0;j<len/2;j++){const a=i+j,b=a+len/2,xr=ur*re[b]-ui*im[b],xi=ur*im[b]+ui*re[b];let tr=re[a],ti=im[a];re[a]=tr+xr;im[a]=ti+xi;re[b]=tr-xr;im[b]=ti-xi;let temp=ur*wcos-ui*wsin;ui=ur*wsin+ui*wcos;ur=temp}}}
const amp=new Float64Array(N/2+1),pow=new Float64Array(N/2+1);for(let i=0;i<amp.length;i++){pow[i]=re[i]*re[i]+im[i]*im[i];amp[i]=Math.sqrt(pow[i])}return{amp,pow}}
function getPair(f,pair){const values=PAIRS[pair].map((bounds,idx)=>{let sum=0,count=0;for(let i=0;i<f.pow.length;i++){const hz=i*FS/N;if(hz>=bounds[0]&&(idx===1?hz<=bounds[1]:hz<bounds[1])){sum+=f.pow[i];count++}}return sum/Math.max(1,count)});return{a:values[0],b:values[1],ratio:10*Math.log10((values[0]+1e-20)/(values[1]+1e-20))}}
function cv(id){const element=$(id),w=Math.max(30,Math.floor(element.getBoundingClientRect().width*Math.min(devicePixelRatio||1,2))),h=Math.max(30,Math.floor(element.getBoundingClientRect().height*Math.min(devicePixelRatio||1,2)));if(element.width!==w||element.height!==h){element.width=w;element.height=h}const ctx=element.getContext('2d');ctx.clearRect(0,0,w,h);return{ctx,w,h}}
function axes(ctx,w,h,text){const x=42,right=w-17,top=21,bottom=h-37;ctx.strokeStyle='#e0e9e0';ctx.lineWidth=1;for(let i=0;i<=4;i++){let y=top+i*(bottom-top)/4;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(right,y);ctx.stroke()}ctx.font='11px sans-serif';ctx.fillStyle='#849386';ctx.fillText(text,x,h-10);return{x,right,top,bottom}}
function lines(id,items,frequency=false,pair=null){
const{ctx,w,h}=cv(id),b=axes(ctx,w,h,frequency?'频率 0–10 kHz':'时间 · 当前 2048 个采样点');let len=frequency?Math.floor(10000*N/FS)+1:N;
if(frequency&&pair!==null){PAIRS[pair].forEach((p,i)=>{ctx.fillStyle=i===0?'rgba(75,150,95,.13)':'rgba(116,148,178,.18)';ctx.fillRect(b.x+p[0]/10000*(b.right-b.x),b.top,(p[1]-p[0])/10000*(b.right-b.x),b.bottom-b.top)})}
let hi=frequency?-Infinity:1e-7,lo=0;
if(frequency){for(let item of items)for(let i=0;i<len;i++)hi=Math.max(hi,20*Math.log10(Math.max(item.data[i],1e-12)));hi=Math.max(-75,hi);lo=hi-75}
else{for(let item of items)for(let val of item.data)hi=Math.max(hi,Math.abs(val));hi*=1.1;lo=-hi}
for(let item of items){ctx.beginPath();ctx.strokeStyle=item.color;ctx.lineWidth=item.width||1.8;for(let i=0;i<len;i++){let val=frequency?20*Math.log10(Math.max(item.data[i],1e-12)):item.data[i],px=b.x+(i/(len-1))*(b.right-b.x),py=b.bottom-clamp((val-lo)/(hi-lo),0,1)*(b.bottom-b.top);if(i===0)ctx.moveTo(px,py);else ctx.lineTo(px,py)}ctx.stroke()}
ctx.fillStyle='#98a79c';ctx.font='11px sans-serif';ctx.fillText('0',b.x,b.bottom+18);ctx.textAlign='right';ctx.fillText(frequency?'10 kHz':'2048',b.right,b.bottom+18);ctx.textAlign='left';
}
function overview(){
const{ctx,w,h}=cv('heroPlot');let b=axes(ctx,w,h,'时间 · 0–'+s.seconds+' 秒');if(!s.env){ctx.fillStyle='#899c8c';ctx.font='16px sans-serif';ctx.fillText('运行一次真实实验后，这里会显示刚选择的音频',b.x+12,h/2);return}
const left=b.x,right=b.right,mid=(b.top+b.bottom)/2;ctx.fillStyle='rgba(71,140,82,.09)';ctx.fillRect(left+s.block/(s.seconds/6)*(right-left),b.top,(right-left)/(s.seconds/6),b.bottom-b.top);
for(let i=0;i<s.env.length;i++){let px=left+i/s.env.length*(right-left);ctx.strokeStyle='#83a78c';ctx.lineWidth=1.3;ctx.beginPath();ctx.moveTo(px,mid-s.env[i][0]*(b.bottom-b.top)*.43);ctx.lineTo(px,mid-s.env[i][1]*(b.bottom-b.top)*.43);ctx.stroke()}
const cursor=s.block*6+s.frame*N/FS;let px=left+cursor/s.seconds*(right-left);ctx.strokeStyle='#287548';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(px,b.top);ctx.lineTo(px,b.bottom);ctx.stroke();
ctx.fillStyle='#287548';ctx.font='bold 12px sans-serif';ctx.fillText(time(cursor),Math.min(px+7,right-95),b.top+15);
}
function selectedFrames(){let offset=s.block*CHUNK+s.frame*N;const original=signal(s.original,offset),marked=signal(s.marked,offset),received=signal(s.received,offset);return{offset,original,marked,received,fo:fft(original),fm:fft(marked),fr:fft(received)}}
function showMini(data){$('spectrumStrip').hidden=false;lines('miniWave',[{data:data.original,color:'#477f5b'}]);lines('miniSpectrum',[{data:data.fo.amp,color:'#467c5b'}],true)}
function pairInfo(data){$('comparison').hidden=false;const before=getPair(data.fo,s.pair),after=getPair(data.fm,s.pair),delta=after.ratio-before.ratio;setText('ratioBefore',before.ratio.toFixed(3)+' dB');setText('ratioAfter',after.ratio.toFixed(3)+' dB');setText('ratioDelta',(delta>=0?'+':'')+delta.toFixed(4)+' dB');setText('deltaNote','带宽比在这一帧中变化 '+Math.abs(delta).toFixed(4)+' dB')}
function setText(id,value){$(id).textContent=value}
function simpleSpectrum(data,which){let sources=which==='channel'?[{data:data.fm.amp,color:'#7890a0'},{data:data.fr.amp,color:'#45945c'}]:[{data:data.fo.amp,color:'#7890a0'},{data:data.fm.amp,color:'#47915e'}];lines('heroPlot',sources,true,which==='embed'?s.pair:null)}
function residual(data){let difference=new Float64Array(N);for(let i=0;i<N;i++)difference[i]=data.marked[i]-data.original[i];lines('heroPlot',[{data:difference,color:'#478d5c'}])}
function detectPlot(){const{ctx,w,h}=cv('heroPlot'),axis=axes(ctx,w,h,'本次 6 秒块 · presence 统计量 / 判决阈值');const blocks=s.seconds/6,rows=s.report?.blocks||[],thr=Number(s.report?.threshold)||0.7;
if(!s.report){ctx.fillStyle='#7b8f80';ctx.font='15px sans-serif';ctx.fillText('等待本次检测结果',axis.x+20,h/2);return}
ctx.setLineDash([6,5]);ctx.strokeStyle='#b87a4d';let ty=axis.bottom-thr*(axis.bottom-axis.top);ctx.beginPath();ctx.moveTo(axis.x,ty);ctx.lineTo(axis.right,ty);ctx.stroke();ctx.setLineDash([]);
for(let i=0;i<blocks;i++){let row=rows[i],value=Number(row?.presence_stat)||0;const width=(axis.right-axis.x)/blocks,x=axis.x+i*width+4,barWidth=Math.max(4,width-8),top=axis.bottom-clamp(value,0,1)*(axis.bottom-axis.top);
ctx.fillStyle=i===s.block?'#328252':'#a4c8ae';ctx.fillRect(x,top,barWidth,axis.bottom-top);
ctx.fillStyle='#67806b';ctx.font='11px sans-serif';ctx.textAlign='center';ctx.fillText(String(i+1),x+barWidth/2,axis.bottom+17)}ctx.textAlign='left'}
function recoverBlocks(){
$('recovery').hidden=s.step!==6||!s.report;const node=$('blockGrid');node.replaceChildren();if(!s.report)return;
setText('recoverHeadline',s.report.status==='IDENTIFIED'?'完整消息已通过检测':'完整消息未通过接受条件');
setText('recoverTotals',s.report.accepted_blocks+' / '+s.report.block_count+' 块通过');
for(let i=0;i<s.seconds/6;i++){const block=s.report.blocks[i],btn=document.createElement('button');btn.type='button';btn.className='block'+(s.block===i?' current':'')+(block?.status!=='IDENTIFIED'?' bad':'');
const small=document.createElement('small');small.textContent='第 '+(i+1)+' 块 · '+(i*6)+' s';const strong=document.createElement('b');strong.textContent=block?.recovered||'UNKNOWN';btn.append(small,strong);btn.addEventListener('click',()=>{stopAuto();s.block=i;render()});node.append(btn)}
}
function legend(html){$('plotLegend').innerHTML=html}
function setStage(i){s.step=clamp(i,0,6);render()}
function render(){
const current=s.step,[title,explain,question,takeaway]=descriptions[current];
setText('stageIndex','STEP '+String(current+1).padStart(2,'0')+' / 07');setText('stageTitle',title);setText('stageExplain',explain);setText('stageQuestion',question);setText('takeaway',takeaway);
document.querySelectorAll('[data-step]').forEach(el=>{let idx=Number(el.dataset.step);el.classList.toggle('current',idx===current);el.classList.toggle('done',idx<current)});
$('prevStep').disabled=current===0;$('nextStep').disabled=current===6;$('nextStep').textContent=current===6?'已经到最后一步':'下一步，看看发生了什么 →';
$('explorePanel').hidden=s.mode!=='explore';$('guidedMode').classList.toggle('selected',s.mode==='guided');$('exploreMode').classList.toggle('selected',s.mode==='explore');$('guidedMode').setAttribute('aria-pressed',String(s.mode==='guided'));$('exploreMode').setAttribute('aria-pressed',String(s.mode==='explore'));
$('frame').value=s.frame;$('block').value=s.block;setText('frameCount',(s.frame+1)+' / 141');setText('frameTime',time(s.block*6+s.frame*N/FS)+' – '+time(s.block*6+(s.frame+1)*N/FS));
$('spectrumStrip').hidden=true;$('comparison').hidden=true;$('recovery').hidden=true;
$('band').value=s.pair;
if(!s.original){setText('plotHeading','这里将展示真实输入音频');setText('plotTag','等待本次实验');legend('<span class="legend">先在上方点击「运行完整实验」</span>');overview();return}
const data=selectedFrames();
if(current===0){setText('plotHeading','① 真实原音 · 全段波形');setText('plotTag',s.seconds+' 秒 · '+FS+' Hz');overview();legend('<span class="legend"><i class="green"></i>本次输入音频</span><span>绿色竖线表示选择的时间位置；可以点击波形选帧</span>')}
if(current===1){setText('plotHeading','② 放大一个 2048 点音频帧');setText('plotTag','42.67 ms / 帧');lines('heroPlot',[{data:data.original,color:'#478a5a'}]);showMini(data);legend('<span class="legend"><i class="green"></i>这 2048 个真实采样点</span><span>下面左侧是同一帧，右侧是其 FFT 结果</span>')}
if(current===2){setText('plotHeading','③ 同一个时间窗口对应的 FFT 频谱');setText('plotTag','23.4375 Hz / bin');lines('heroPlot',[{data:data.fo.amp,color:'#478a5a'}],true);showMini(data);legend('<span class="legend"><i class="green"></i>原音 FFT 幅度谱</span><span>时域信号与频域信号一一对应</span>')}
if(current===3){setText('plotHeading','④ 水印嵌入前后 · 频带真实变化');setText('plotTag',s.marked?'本次真实嵌入结果':'等待水印音频');if(s.marked){simpleSpectrum(data,'embed');pairInfo(data)}else lines('heroPlot',[{data:data.fo.amp,color:'#478a5a'}],true,s.pair);
legend('<span class="legend"><i class="blue"></i>原始音频</span><span class="legend"><i class="green"></i>本次水印音频</span><span class="legend"><i class="amber"></i>频带 A/B 已高亮</span>')}
if(current===4){setText('plotHeading','⑤ 只显示水印带来的真实微小残差');setText('plotTag','残差已单独调整显示尺度');if(s.marked)residual(data);else overview();showMini(data);legend('<span class="legend"><i class="green"></i>本次水印 WAV − 本次原音 WAV</span><span>单独放大残差 ≠ 实际音量放大</span>')}
if(current===5){setText('plotHeading','⑥ 信道前 / 后的频谱');setText('plotTag',s.processingLabel);if(s.received)simpleSpectrum(data,'channel');else if(s.marked)lines('heroPlot',[{data:data.fm.amp,color:'#478a5a'}],true);else overview();
legend('<span class="legend"><i class="blue"></i>信道前水印 WAV</span><span class="legend"><i class="green"></i>真实信道输出</span><span>有损编解码可能引入时延</span>')}
if(current===6){setText('plotHeading','⑦ 真实检测 presence 与判定阈值');setText('plotTag',s.report?s.report.status:'等待检测');detectPlot();recoverBlocks();legend('<span class="legend"><i class="green"></i>本次各块的 presence</span><span class="legend"><i class="amber"></i>检测接受阈值</span>')}
}
function stopAuto(){s.auto=false;clearTimeout(s.timer);s.timer=null;$('autoPlay').textContent='▶ 自动讲解';setText('playState','可暂停、回退或手动跳转')}
function startAuto(){stopAuto();s.auto=true;$('autoPlay').textContent='Ⅱ 暂停讲解';setText('playState','按顺序展示已计算的真实结果');scheduleNext()}
function scheduleNext(){clearTimeout(s.timer);if(!s.auto)return;s.timer=setTimeout(()=>{if(s.step>=6){stopAuto();return}setStage(s.step+1);scheduleNext()},4300)}
function inputChanged(){if(s.busy)return;clear();status('实验参数已改变。旧图表已清空，请重新运行当前输入。')}
$('mode').addEventListener('change',()=>{$('payload').value=MESSAGES[$('mode').value];$('payload').maxLength=MESSAGES[$('mode').value].length;s.seconds=['c2-long-id','c3-192'].includes($('mode').value)?72:6;fillBlocks();inputChanged()});
$('source').addEventListener('change',()=>{$('uploadWrap').hidden=$('source').value!=='upload';inputChanged()});
for(const id of ['upload','payload','key','channel'])$(id).addEventListener('change',inputChanged);
$('run').addEventListener('click',run);
document.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>{stopAuto();setStage(+b.dataset.step)}));
$('prevStep').addEventListener('click',()=>{stopAuto();setStage(s.step-1)});
$('nextStep').addEventListener('click',()=>{stopAuto();setStage(s.step+1)});
$('autoPlay').addEventListener('click',()=>s.auto?stopAuto():startAuto());
$('guidedMode').addEventListener('click',()=>{s.mode='guided';render()});
$('exploreMode').addEventListener('click',()=>{stopAuto();s.mode='explore';render()});
$('band').addEventListener('change',()=>{stopAuto();s.pair=+$('band').value;render()});
$('block').addEventListener('change',()=>{stopAuto();s.block=+$('block').value;render()});
$('frame').addEventListener('input',()=>{stopAuto();s.frame=+$('frame').value;render()});
$('prevFrame').addEventListener('click',()=>{stopAuto();if(s.frame===0&&s.block>0){s.block--;s.frame=COUNT-1}else s.frame=Math.max(0,s.frame-1);render()});
$('nextFrame').addEventListener('click',()=>{stopAuto();if(s.frame===COUNT-1&&s.block<s.seconds/6-1){s.block++;s.frame=0}else s.frame=Math.min(COUNT-1,s.frame+1);render()});
$('heroPlot').addEventListener('pointerdown',e=>{if(!s.original||s.step>1)return;stopAuto();const bounds=e.currentTarget.getBoundingClientRect(),portion=clamp((e.clientX-bounds.left)/bounds.width,0,.999999);let t=portion*s.seconds;s.block=Math.floor(t/6);s.frame=clamp(Math.floor((t%6)*FS/N),0,COUNT-1);render()});
let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(render,110)});
fillBlocks();render();
})();
