(()=>{
'use strict';
const API='https://dsp-audio-watermark-api.onrender.com/api/v1/';
const SAMPLE='https://cdn.jsdelivr.net/gh/suibianba12138/blind-audio-watermarking@main/course_release/media/selected_c3_16_showcase/Original.wav';
const SR=48000,N=2048,L=288000,F=141;
const $=id=>document.getElementById(id), BANDS=[[[900,2200],[2200,3500]],[[3500,5000],[5000,6500]],[[6500,8000],[8000,9500]]];
const defaultMessages={'c2-8':'A7','c3-16':'A7C3','c2-long-id':'12345678','c3-192':'D42DEE6FA235F3C07531FD862283452DCB56FF6A8F621E41'};
const stages=[
['01 / FRAME DIVISION','从原音开始，观察分帧','每 6 秒音频分为 141 个不重叠的 2048 点 FFT 帧；最后一帧补零。'],
['02 / FFT','把时域信号转换到频域','选择任意一帧，左边显示输入样本，右边计算本次原音的 2048 点 rFFT。'],
['03 / EMBEDDING','查看本次嵌入的频带变化','对同一帧的原音和本次新生成的水印 WAV 做 FFT，比较三组频带对的平均功率与能量比。'],
['04 / RECONSTRUCTION','观察最终音频与残差','直接比较本次实际生成的水印 WAV 与输入原音，波形及残差均可逐帧查看。'],
['05 / CHANNEL','本次信道处理造成了什么变化','比较新生成的水印 WAV 与这次 FFmpeg 处理得到的音频；本图是浏览器解码后的频谱。'],
['06 / DETECTION','查看这次检测的统计量','这里显示当前任务由真实检测接口返回的 presence、阈值、块状态；不读取任何历史检测 CSV。'],
['07 / RECOVERY','当前运行的恢复结果','展示本次运行返回的候选及已接受消息。C2 长身份采用真实后端的重复融合结果。']
];
const state={step:0,block:0,frame:0,pair:0,seconds:6,original:null,marked:null,received:null,markedBlob:null,receivedBlob:null,report:null,source:null,sourceToken:null,busy:false,env:null,urls:[]};
const fmt=t=>{t=Math.max(0,t);return String(Math.floor(t/60)).padStart(2,'0')+':'+(t%60).toFixed(3).padStart(6,'0')};
const status=(msg,kind='')=>{const e=$('loadStatus');e.textContent=msg;e.className='load-status '+kind};
const set=(id,text)=>$(id).textContent=text;
function phases(which,kind){let el=$(which);el.className=kind;el.textContent={phaseEmbed:'① 嵌入',phaseChannel:'② 信道',phaseDetect:'③ 检测'}[which]+' · '+({running:'运行中',done:'已完成',failed:'失败'}[kind]||'未运行')}
function selected(){const mode=$('liveMode').value,source=$('liveSource').value,file=$('liveFile').files[0]||null,message=$('liveMessage').value.trim().replace(/^0x/i,'').toUpperCase(),key=$('liveKey').value;
if(!new RegExp('^[0-9A-F]{'+defaultMessages[mode].length+'}$').test(message))throw Error('消息需要恰好 '+defaultMessages[mode].length+' 位十六进制数字');
if(key.length<4||key.length>100)throw Error('密钥长度必须为 4–100 字符');
if(source==='upload'&&!file)throw Error('请先上传音频文件');
return{mode,source,file,message,key,seconds:mode==='c2-long-id'||mode==='c3-192'?72:6}}
function form(s){const d=new FormData();d.append('mode',s.mode);d.append('source',s.source);d.append('key',s.key);if(s.source==='upload')d.append('reference',s.file,s.file.name);return d}
async function call(endpoint,data){const r=await fetch(API+endpoint,{method:'POST',body:data,cache:'no-store'});if(!r.ok){let msg='HTTP '+r.status;try{const j=await r.json();msg=typeof j.detail==='string'?j.detail:msg}catch{}throw Error(msg)}return r}
async function decode(bytes){let ctx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:SR});try{const a=await ctx.decodeAudioData(bytes.slice(0));const max=state.seconds*SR;let len=Math.min(a.length,max),out=new Float32Array(max);for(let channel=0;channel<a.numberOfChannels;channel++){const d=a.getChannelData(channel);for(let i=0;i<len;i++)out[i]+=d[i]/a.numberOfChannels}return out}finally{await ctx.close()}}
async function decodedBlob(blob){return decode(await blob.arrayBuffer())}
async function originalSamples(s){if(s.source==='sample'){const r=await fetch(SAMPLE);if(!r.ok)throw Error('示例原音下载失败：'+r.status);return decode(await r.arrayBuffer())}return decodedBlob(s.file)}
function player(id,link,blob,filename){const url=URL.createObjectURL(blob);state.urls.push(url);$(id).src=url;$(id).load();let a=$(link);a.href=url;a.download=filename;a.hidden=false}
function reset(){state.marked=null;state.original=null;state.received=null;state.markedBlob=null;state.receivedBlob=null;state.report=null;state.env=null;state.source=null;state.block=0;state.frame=0;$('processBtn').disabled=true;$('detectBtn').disabled=true;
for(const id of ['phaseEmbed','phaseChannel','phaseDetect'])phases(id,'');
for(const id of ['markedPlayer','receivedPlayer']){$(id).pause();$(id).removeAttribute('src');$(id).load()}
$('markedDownload').hidden=true;$('receivedDownload').hidden=true;for(const u of state.urls)URL.revokeObjectURL(u);state.urls=[];render()}
function populateBlocks(){const sel=$('blockSelect');sel.textContent='';for(let i=0;i<state.seconds/6;i++){let o=document.createElement('option');o.value=i;o.textContent=String(i+1).padStart(2,'0')+' · '+String(i*6).padStart(2,'0')+'–'+String((i+1)*6).padStart(2,'0')+' 秒';sel.appendChild(o)}}
async function embed(){if(state.busy)return;let s;try{s=selected()}catch(e){status(e.message,'error');return}reset();state.busy=true;$('loadBtn').disabled=true;state.seconds=s.seconds;populateBlocks();phases('phaseEmbed','running');status('正在真实执行当前音频的水印嵌入。服务器返回后生成频谱与波形，不使用历史数据。');
try{const d=form(s);d.append('message',s.message);const response=await call('embed',d);state.markedBlob=await response.blob();
const [original,marked]=await Promise.all([originalSamples(s),decodedBlob(state.markedBlob)]);state.original=original;state.marked=marked;state.env=envelope(original);state.source=s;player('markedPlayer','markedDownload',state.markedBlob,'watermarked-'+s.mode+'.wav');
$('processBtn').disabled=false;$('detectBtn').disabled=false;phases('phaseEmbed','done');state.step=2;status('本次嵌入已完成：FFT 与频带变化来自刚生成的水印 WAV。点击“信道处理 + 检测”继续。','good');render()}
catch(e){phases('phaseEmbed','failed');status('嵌入失败：'+e.message,'error')}
finally{state.busy=false;$('loadBtn').disabled=false}}
function matches(s){let a=state.source;return a&&a.mode===s.mode&&a.source===s.source&&a.file===s.file&&a.message===s.message&&a.key===s.key}
async function processRun(){if(state.busy)return;let s;try{s=selected();if(!state.markedBlob||!matches(s))throw Error('参数已变化，需要重新嵌入')}catch(e){status(e.message,'error');return}
state.busy=true;$('processBtn').disabled=true;$('detectBtn').disabled=true;state.report=null;state.received=null;state.receivedBlob=null;phases('phaseChannel','running');phases('phaseDetect','');let channel=$('liveChannel').value;status('正在调用 FFmpeg 真实处理本次水印音频…');
try{const data=new FormData();data.append('channel',channel);data.append('seconds',String(s.seconds));data.append('audio',state.markedBlob,'watermarked.wav');const r=await call('process',data);const blob=await r.blob();state.receivedBlob=blob;state.received=await decodedBlob(blob);let ext=channel==='mp3'?'mp3':channel==='aac'||channel==='mp3_aac'?'m4a':'wav';
player('receivedPlayer','receivedDownload',blob,'received-'+channel+'.'+ext);phases('phaseChannel','done');phases('phaseDetect','running');status('信道处理完成，正在对本次音频执行参考辅助检测…');state.step=4;render();
const d=form(s);d.append('received',blob,'received.'+ext);const det=await call('detect',d);state.report=await det.json();phases('phaseDetect','done');state.step=5;status('检测完成：'+state.report.status+' · '+state.report.accepted_blocks+'/'+state.report.block_count+' 个块通过。','good');render()}
catch(e){phases(state.receivedBlob?'phaseDetect':'phaseChannel','failed');status('执行失败：'+e.message,'error')}
finally{state.busy=false;$('processBtn').disabled=false;$('detectBtn').disabled=false}}
async function detectRun(){if(state.busy)return;let s;try{s=selected();if(!matches(s)||!state.markedBlob)throw Error('请先嵌入当前音频')}catch(e){status(e.message,'error');return}state.busy=true;$('detectBtn').disabled=true;phases('phaseDetect','running');status('正在执行当前音频的真实检测…');
try{const d=form(s);const blob=state.receivedBlob||state.markedBlob;d.append('received',blob,'received.wav');state.report=await(await call('detect',d)).json();phases('phaseDetect','done');state.step=5;status('本次检测完成：'+state.report.status,'good');render()}
catch(e){phases('phaseDetect','failed');status('检测失败：'+e.message,'error')}
finally{state.busy=false;$('detectBtn').disabled=false}}
function envelope(samples){let n=750,result=[];for(let i=0;i<n;i++){let lo=1,hi=-1;for(let j=Math.floor(i*samples.length/n);j<Math.min(samples.length,Math.ceil((i+1)*samples.length/n));j++){let v=samples[j];lo=Math.min(lo,v);hi=Math.max(hi,v)}result.push([lo,hi])}return result}
function frame(src,start){let v=new Float64Array(N);if(src)for(let i=0;i<N;i++)if(start+i<src.length)v[i]=src[start+i];return v}
function fft(x){const re=new Float64Array(x),im=new Float64Array(N);for(let i=1,j=0;i<N;i++){let b=N>>1;while(j&b){j^=b;b>>=1}j^=b;if(i<j){let q=re[i];re[i]=re[j];re[j]=q}}
for(let len=2;len<=N;len*=2){const a=-2*Math.PI/len,wr=Math.cos(a),wi=Math.sin(a);for(let i=0;i<N;i+=len){let cr=1,ci=0;for(let j=0;j<len/2;j++){let l=i+j,r=l+len/2,vr=cr*re[r]-ci*im[r],vi=cr*im[r]+ci*re[r],tr=re[l],ti=im[l];re[l]=tr+vr;im[l]=ti+vi;re[r]=tr-vr;im[r]=ti-vi;let t=cr*wr-ci*wi;ci=cr*wi+ci*wr;cr=t}}}
let amplitude=new Float64Array(N/2+1),power=new Float64Array(N/2+1);for(let i=0;i<amplitude.length;i++){power[i]=re[i]*re[i]+im[i]*im[i];amplitude[i]=Math.sqrt(power[i])}return{amplitude,power}}
function energy(f,pair){let out=[];for(let b of BANDS[pair]){let sum=0,n=0;for(let i=0;i<f.power.length;i++){let hz=i*SR/N;if(hz>=b[0]&&hz<=(b[1]-1e-9)){sum+=f.power[i];n++}}out.push(sum/Math.max(1,n))}return{a:out[0],b:out[1],ratio:10*Math.log10((out[0]+1e-20)/(out[1]+1e-20))}}
function ctx(id){const el=$(id),dpr=Math.min(devicePixelRatio||1,2),r=el.getBoundingClientRect(),w=Math.max(40,Math.floor(r.width*dpr)),h=Math.max(40,Math.floor(r.height*dpr));if(el.width!==w||el.height!==h){el.width=w;el.height=h}const c=el.getContext('2d');c.clearRect(0,0,w,h);return{c,w,h}}
function grid(c,w,h,xlabel){c.strokeStyle='#e5e9e1';for(let i=0;i<4;i++){let y=14+i*(h-42)/3;c.beginPath();c.moveTo(30,y);c.lineTo(w-12,y);c.stroke()}c.fillStyle='#929b91';c.font='10px sans-serif';c.fillText(xlabel,31,h-5)}
function draw(id,series,type,pair=null){const{c,w,h}=ctx(id);grid(c,w,h,type==='freq'?'frequency · 0–10 kHz':'sample index · 0–2047');
const left=32,right=w-12,top=16,bottom=h-30,len=type==='freq'?Math.floor(10000*N/SR)+1:N;
if(type==='freq'&&pair!==null)for(let i=0;i<2;i++){const b=BANDS[pair][i];c.fillStyle=i===0?'rgba(68,111,73,.10)':'rgba(100,129,164,.12)';c.fillRect(left+b[0]/10000*(right-left),top,(b[1]-b[0])/10000*(right-left),bottom-top)}
let max=-Infinity,min=Infinity;if(type==='freq'){for(let s of series)for(let i=0;i<len;i++)max=Math.max(max,20*Math.log10(Math.max(s.data[i],1e-12)));max=Math.max(-80,max);min=max-80}else{max=1e-6;for(let s of series)for(let v of s.data)max=Math.max(max,Math.abs(v));min=-max;max*=1.07;min*=1.07}
for(let s of series){c.strokeStyle=s.color;c.lineWidth=1.5;c.beginPath();for(let i=0;i<len;i++){let v=type==='freq'?20*Math.log10(Math.max(s.data[i],1e-12)):s.data[i],x=left+i/(len-1)*(right-left),y=bottom-Math.min(1,Math.max(0,(v-min)/(max-min)))*(bottom-top);i?c.lineTo(x,y):c.moveTo(x,y)}c.stroke()}
c.font='10px sans-serif';c.fillStyle='#8a948a';c.fillText('0',left,h-15);c.textAlign='right';c.fillText(type==='freq'?'10 kHz':'2048',right,h-15);c.textAlign='left'}
function blockBars(id,stat=false){const{c,w,h}=ctx(id);grid(c,w,h,stat?'presence statistic':'6 s · 141 frames');const left=32,right=w-12,base=h-30;
if(!stat){for(let i=0;i<F;i++){let x=left+i/F*(right-left);c.fillStyle=i===state.frame?'#3d6c4b':'#d8e3d8';c.fillRect(x,24,Math.max(1,(right-left)/F),base-24)}return}
const rows=state.report?.blocks||[],thr=Number(state.report?.threshold)||0.7;c.setLineDash([4,4]);c.strokeStyle='#c58d65';let yy=base-thr*(base-28);c.beginPath();c.moveTo(left,yy);c.lineTo(right,yy);c.stroke();c.setLineDash([]);
for(let i=0;i<state.seconds/6;i++){let v=Number(rows[i]?.presence_stat)||0,bw=(right-left)/(state.seconds/6),x=left+i*bw+3;c.fillStyle=i===state.block?'#326e47':'#91b49a';c.fillRect(x,base-Math.min(1,Math.max(0,v))*(base-28),Math.max(3,bw-6),Math.min(1,Math.max(0,v))*(base-28))}}
function overview(){const{c,w,h}=ctx('overviewPlot');c.strokeStyle='#e5e9e1';c.beginPath();c.moveTo(0,h/2);c.lineTo(w,h/2);c.stroke();if(!state.env){c.font='12px sans-serif';c.fillStyle='#899889';c.fillText('运行嵌入后显示本次原音波形',16,h/2);return}
c.fillStyle='rgba(60,103,73,.10)';let blocks=state.seconds/6;c.fillRect(state.block/blocks*w,0,w/blocks,h);
c.strokeStyle='#829f87';for(let i=0;i<state.env.length;i++){let e=state.env[i],x=i/state.env.length*w;c.beginPath();c.moveTo(x,h/2-e[0]*h*.39);c.lineTo(x,h/2-e[1]*h*.39);c.stroke()}
let x=(state.block*6+state.frame*N/SR)/state.seconds*w;c.strokeStyle='#27633c';c.lineWidth=2;c.beginPath();c.moveTo(x,0);c.lineTo(x,h);c.stroke()}
function measure(items){const root=$('metrics');root.replaceChildren();for(let [value,label]of items){let e=document.createElement('div');e.className='metric';let b=document.createElement('b'),s=document.createElement('small');b.textContent=value;s.textContent=label;e.append(b,s);root.append(e)}}
function textLabels(l,r,lm='',rm='',lf='',rf=''){set('leftTitle',l);set('rightTitle',r);set('leftMeta',lm);set('rightMeta',rm);set('leftFoot',lf);set('rightFoot',rf)}
function resultGrid(){const root=$('recoveredGrid'),wrap=$('recoveredWrap');wrap.hidden=state.step!==6||!state.report;root.replaceChildren();if(wrap.hidden)return;for(let i=0;i<state.seconds/6;i++){const row=state.report.blocks[i],el=document.createElement('button');el.type='button';el.className='recover-block'+(i===state.block?' current':'')+(row?.status==='UNKNOWN'?' unknown':'');const s=document.createElement('small'),b=document.createElement('b');s.textContent='第 '+(i+1)+' 块';b.textContent=row?.recovered||'UNKNOWN';el.append(s,b);el.addEventListener('click',()=>{state.block=i;render()});root.append(el)}}
function render(){
const stage=state.step,[code,title,desc]=stages[stage],start=state.block*L+state.frame*N;
set('stageNumber',code);set('stageTitle',title);set('stageDescription',desc);
document.querySelectorAll('[data-step]').forEach(e=>e.classList.toggle('active',Number(e.dataset.step)===stage));
$('backBtn').disabled=stage===0;$('forwardBtn').disabled=stage===6;$('blockSelect').value=state.block;$('frameSeek').value=state.frame;
set('frameIndex','#'+String(state.frame+1).padStart(3,'0')+' / 141');set('overviewTitle','本次音频 / '+state.seconds+' 秒');set('timeQuarter',fmt(state.seconds/3));set('timeHalf',fmt(state.seconds*2/3));set('timeEnd',fmt(state.seconds));set('timeReadout',fmt(start/SR)+' – '+fmt((start+N)/SR));set('sourceLabel',state.marked?'本次执行 · 真实输出':'尚未执行');
$('pairField').style.display=stage===2?'flex':'none';$('channelField').style.display='none';$('pairSelect').value=state.pair;
set('stageHint',state.marked?'本次真实音频 · 浏览器分析图表':'尚未执行 · 不展示历史数据');
overview();resultGrid();if(!state.original||!state.marked){for(const id of ['leftPlot','rightPlot']){const{c,w,h}=ctx(id);grid(c,w,h,'waiting for current run')}textLabels('等待嵌入','等待本次音频');set('insightTitle','请先执行水印嵌入');set('insightText','不会使用预先绘制的曲线或历史结果冒充当前实验。');measure([]);return}
const x=frame(state.original,start),y=frame(state.marked,start),fx=fft(x),fy=fft(y),g='#437b55',b='#71879a';
if(stage===0){textLabels('本次原音 · 当前帧波形','当前帧在 6 秒中的位置','2048 samples','141 frames');draw('leftPlot',[{data:x,color:g}],'wave');blockBars('rightPlot');set('insightTitle','同一次实验的连续帧');set('insightText','48 kHz 下 2048 点约 42.67 ms；每个 6 秒块共有 141 帧，尾帧用零补足。');measure([['2048','样本 / 帧'],['141','帧 / 6 秒']])}
if(stage===1){textLabels('当前原音帧 · 时域','当前原音帧 · FFT','2048 samples','0–10 kHz');draw('leftPlot',[{data:x,color:g}],'wave');draw('rightPlot',[{data:fx.amplitude,color:g}],'freq');set('insightTitle','选中帧的实际 FFT');set('insightText','与课程算法相同的 2048 点无窗 rFFT，频谱随当前帧指针同步改变。');measure([['23.4375 Hz','频率分辨率'],['1025','单边 FFT bins']])}
if(stage===2){const a=energy(fx,state.pair),c=energy(fy,state.pair);textLabels('嵌入前 / 后 · 频域叠加','当前频带 A / B 能量比','原音蓝灰 / 新水印绿','实测 dB');draw('leftPlot',[{data:fx.amplitude,color:b},{data:fy.amplitude,color:g}],'freq',state.pair);blockBars('rightPlot');set('insightTitle','本次调制在频带对上的实际影响');set('insightText','已写入本次水印 WAV 的最终能量变化；右侧为当前帧位置。预先冻结的逐 bit/chip 映射不参与显示。');measure([[a.ratio.toFixed(3)+' dB','原音 A/B 比'],[(c.ratio-a.ratio).toFixed(4)+' dB','本次能量比变化']])}
if(stage===3){const diff=new Float64Array(N);for(let i=0;i<N;i++)diff[i]=y[i]-x[i];textLabels('本次原音 / 水印 · 叠加','真实水印残差','原音蓝灰 / 水印绿','独立幅度尺度');draw('leftPlot',[{data:x,color:b},{data:y,color:g}],'wave');draw('rightPlot',[{data:diff,color:g}],'wave');let pow=0,err=0;for(let i=state.block*L;i<(state.block+1)*L;i++){let v=state.original[i]||0,d=(state.marked[i]||0)-v;pow+=v*v;err+=d*d}set('insightTitle','当前 6 秒块的实际音频差异');set('insightText','右侧差分图按自身幅度缩放，所以即使左图几乎重叠也可以观察残差结构。');measure([[ (10*Math.log10(pow/Math.max(err,1e-30))).toFixed(2)+' dB','实测 SNR'],[Math.sqrt(err/L).toExponential(2),'残差 RMS']])}
if(stage===4){textLabels('当前水印 WAV','本次信道输出','原始信号','本次处理');draw('leftPlot',[{data:fy.amplitude,color:b}],'freq');draw('rightPlot',[{data:fft(frame(state.received||state.marked,start)).amplitude,color:g}],'freq');set('insightTitle',state.received?'本次信道输出已生成':'等待执行真实信道');set('insightText','调用真实 FFmpeg 后返回本次音频，再由浏览器解码计算频谱。MP3/AAC 可能引入编解码时延，当前图不代表严格样本对齐后的差值。');measure([[state.received?'已生成':'未处理','信道输出'],[$('liveChannel').selectedOptions[0].textContent,'本次处理选项']])}
if(stage===5||stage===6){const rows=state.report?.blocks||[],r=rows[state.block];textLabels('本次 presence 统计','本次消息块状态','后端返回数据','当前任务');blockBars('leftPlot',true);blockBars('rightPlot',true);set('insightTitle',state.report?('本次检测：'+state.report.status):'等待真实检测结果');set('insightText',state.report?'这次的后端确实使用了当前原音、当前密钥和当前接收音。恢复消息与存在性判定独立，不会向检测器传入已知目标消息。':'在上方点击“信道处理 + 检测”或“仅重新检测”，结果返回后展示本次统计。');measure([[r&&r.presence_stat!==undefined?Number(r.presence_stat).toFixed(4):'—','当前块 presence'],[r?.recovered||'UNKNOWN','当前块恢复'],[state.report?.recovered_payload||'UNKNOWN','完整消息']])}
}
function goStep(n){state.step=Math.min(6,Math.max(0,n));render()}
function invalidated(){if(!state.busy){reset();status('输入条件已改变。请重新执行嵌入，旧图表与旧检测结果已清空。')}}
$('liveMode').addEventListener('change',()=>{$('liveMessage').value=defaultMessages[$('liveMode').value];$('liveMessage').maxLength=defaultMessages[$('liveMode').value].length;state.seconds=$('liveMode').value.includes('long')||$('liveMode').value==='c3-192'?72:6;populateBlocks();invalidated()});
$('liveSource').addEventListener('change',()=>{$('uploadField').hidden=$('liveSource').value!=='upload';invalidated()});
for(const id of ['liveFile','liveMessage','liveKey'])$(id).addEventListener('change',invalidated);
$('liveChannel').addEventListener('change',()=>{if(!state.busy){state.received=null;state.receivedBlob=null;state.report=null;phases('phaseChannel','');phases('phaseDetect','');status('信道条件改变，请重新运行信道处理和检测。');render()}});
$('loadBtn').addEventListener('click',embed);$('processBtn').addEventListener('click',processRun);$('detectBtn').addEventListener('click',detectRun);
document.querySelectorAll('[data-step]').forEach(el=>el.addEventListener('click',()=>goStep(+el.dataset.step)));
$('backBtn').addEventListener('click',()=>goStep(state.step-1));$('forwardBtn').addEventListener('click',()=>goStep(state.step+1));
$('blockSelect').addEventListener('change',()=>{state.block=+$('blockSelect').value;render()});
$('frameSeek').addEventListener('input',()=>{state.frame=+$('frameSeek').value;render()});
$('previousFrame').addEventListener('click',()=>{if(state.frame===0&&state.block>0){state.block--;state.frame=F-1}else state.frame=Math.max(0,state.frame-1);render()});
$('nextFrame').addEventListener('click',()=>{if(state.frame===F-1&&state.block<state.seconds/6-1){state.block++;state.frame=0}else state.frame=Math.min(F-1,state.frame+1);render()});
$('pairSelect').addEventListener('change',()=>{state.pair=+$('pairSelect').value;render()});
$('overviewPlot').addEventListener('pointerdown',e=>{const r=e.currentTarget.getBoundingClientRect(),t=Math.min(.99999,Math.max(0,(e.clientX-r.left)/r.width))*state.seconds;state.block=Math.floor(t/6);state.frame=Math.min(F-1,Math.floor((t-state.block*6)*SR/N));render()});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,150)});
populateBlocks();render();
})();