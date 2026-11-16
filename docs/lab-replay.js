(()=>{'use strict';
const BASE='https://cdn.jsdelivr.net/gh/suibianba12138/blind-audio-watermarking@main/course_release/media/selected_c3_16_showcase/';
const $=id=>document.getElementById(id);
const SR=48000,N=2048,BLOCK=6*SR,FRAMES=Math.ceil(BLOCK/N);
const bands=[[[900,2200],[2200,3500]],[[3500,5000],[5000,6500]],[[6500,8000],[8000,9500]]];
const headings=[
 ['01 / FRAME DIVISION','观察分帧之前的声音','把每个 6 秒音频块划分为 2048 样本的无重叠 FFT 帧；不足 2048 点的尾帧补零。'],
 ['02 / FREQUENCY ANALYSIS','让一个音频帧进入频域','同一帧在左边显示 2048 个采样点，右边显示 rFFT 的实际幅度谱。频率分辨率为 23.4375 Hz。'],
 ['03 / WATERMARK EMBEDDING','观察三组频带对的微小变化','选择频带对，比较原音与最终水印音在该帧的真实频谱，以及两组频带的平均功率与相对能量比。'],
 ['04 / AUDIO RECONSTRUCTION','水印最终改变了多少声音？','用保存回读的两份真实 WAV 对照当前帧波形和差分残差，并计算当前 6 秒块的实际嵌入 SNR。'],
 ['05 / CHANNEL EFFECTS','编码之后，频谱发生了什么？','比较最终水印 WAV 与真实 MP3 / AAC 编码后再经浏览器解码的频谱；注意有损编码可能引入时延。'],
 ['06 / REFERENCE DETECTION','每一个 6 秒块的检测统计量','这里显示保存的真实检测记录（presence 与阈值），不是浏览器仿造的检测器或在线重新检测。'],
 ['07 / PAYLOAD RECOVERY','一段音乐，十二个消息块','查看精选 C3-16 音乐在 Clean / MP3 / AAC 条件下实际恢复的十二个 16-bit 消息块。']
];
const state={step:0,block:0,frame:0,pair:0,channel:'clean',audio:{},env:null,records:[],loading:false,loaded:false,error:''};
const blockSelect=$('blockSelect');
for(let i=0;i<12;i++){let o=document.createElement('option');o.value=i;o.textContent=String(i+1).padStart(2,'0')+' · '+String(i*6).padStart(2,'0')+'–'+String((i+1)*6).padStart(2,'0')+' 秒';blockSelect.append(o)}
blockSelect.remove(0);
const names={clean:'Clean WAV',mp3:'MP3 128 kbps',aac:'AAC 128 kbps'};
const filenames={original:'Original.wav',marked:'Watermarked.wav',mp3:'Watermarked.mp3',aac:'Watermarked.m4a'};
const status=(str,type='')=>{$('loadStatus').textContent=str;$('loadStatus').className='load-status '+type};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const fmt=t=>{let m=Math.floor(t/60),s=(t%60).toFixed(3);return String(m).padStart(2,'0')+':'+String(+s<10?'0'+s:s)};
async function fetchAudio(key){
 if(state.audio[key])return state.audio[key];
 const r=await fetch(BASE+filenames[key]);if(!r.ok)throw Error(filenames[key]+' HTTP '+r.status);
 const bytes=await r.arrayBuffer();
 const ctx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:SR});
 try{const decoded=await ctx.decodeAudioData(bytes.slice(0));const data=new Float32Array(decoded.getChannelData(0));state.audio[key]=data;return data}
 finally{await ctx.close()}
}
async function fetchDetection(){
 const r=await fetch(BASE+'detection_data.csv');if(!r.ok)throw Error('检测 CSV HTTP '+r.status);
 const text=await r.text(),lines=text.trim().split(/\r?\n/),headers=lines.shift().split(',');
 state.records=lines.map(line=>{let cells=line.split(','),out={};headers.forEach((h,i)=>out[h.trim()]=(cells[i]||'').trim());return out})
}
async function loadCore(){
 if(state.loading)return;state.loading=true;$('loadBtn').disabled=true;status('正在读取公开原音和水印音频，并计算真实波形索引…');
 try{await Promise.all([fetchAudio('original'),fetchAudio('marked'),fetchDetection()]);state.env=buildEnvelope(state.audio.original);state.loaded=true;status('真实 72 秒音频与检测记录已载入。可逐帧浏览、切换处理阶段。','good');$('loadBtn').textContent='实验数据已就绪';render()}
 catch(err){state.error=String(err.message||err);status('读取失败：'+state.error+'。可再次尝试；请检查网络或 CDN。','error');$('loadBtn').disabled=false}
 finally{state.loading=false}
}
async function loadChannel(){
 if(state.channel==='clean'||state.audio[state.channel])return;
 status('正在读取 '+names[state.channel]+' 的真实音频文件…');
 try{await fetchAudio(state.channel);status('已载入 '+names[state.channel]+'；现在显示浏览器解码后对应时刻的频谱。','good')}
 catch(err){status('信道音频读取失败：'+err.message,'error')}
}
function buildEnvelope(data){
 let count=900,out=new Array(count),seg=data.length/count;
 for(let i=0;i<count;i++){let lo=1,hi=-1,start=Math.floor(i*seg),end=Math.min(data.length,Math.ceil((i+1)*seg));for(let j=start;j<end;j++){let v=data[j];if(v<lo)lo=v;if(v>hi)hi=v}out[i]=[lo,hi]}
 return out;
}
function frame(data,offset){const out=new Float64Array(N);if(!data)return out;for(let i=0;i<N;i++){const j=offset+i;if(j>=0&&j<data.length)out[i]=data[j]}return out}
function fft(x){
 const re=new Float64Array(x),im=new Float64Array(N);
 for(let i=1,j=0;i<N;i++){let b=N>>1;for(;j&b;b>>=1)j^=b;j^=b;if(i<j){let a=re[i];re[i]=re[j];re[j]=a}}
 for(let len=2;len<=N;len*=2){const ang=-2*Math.PI/len,wr=Math.cos(ang),wi=Math.sin(ang);for(let i=0;i<N;i+=len){let cr=1,ci=0;for(let j=0;j<len/2;j++){const a=i+j,b=i+j+len/2,vr=cr*re[b]-ci*im[b],vi=cr*im[b]+ci*re[b],tr=re[a],ti=im[a];re[a]=tr+vr;im[a]=ti+vi;re[b]=tr-vr;im[b]=ti-vi;let nr=cr*wr-ci*wi;ci=cr*wi+ci*wr;cr=nr}}}
 const magnitude=new Float64Array(N/2+1),power=new Float64Array(N/2+1);for(let i=0;i<magnitude.length;i++){power[i]=re[i]*re[i]+im[i]*im[i];magnitude[i]=Math.sqrt(power[i])}
 return {magnitude,power}
}
function bandPower(power,lo,hi,includeHi){let sum=0,n=0;for(let k=0;k<power.length;k++){let f=k*SR/N;if(f>=lo&&(includeHi?f<=hi:f<hi)){sum+=power[k];n++}}return sum/Math.max(1,n)}
function energy(fftObj,pair){const p=bands[pair];let ea=bandPower(fftObj.power,p[0][0],p[0][1],false),eb=bandPower(fftObj.power,p[1][0],p[1][1],true);return {a:ea,b:eb,ratio:10*Math.log10((ea+1e-20)/(eb+1e-20))}}
function canvas(id){const el=$(id),dpr=Math.min(2,window.devicePixelRatio||1),r=el.getBoundingClientRect(),w=Math.max(10,Math.floor(r.width*dpr)),h=Math.max(10,Math.floor(r.height*dpr));if(el.width!==w||el.height!==h){el.width=w;el.height=h}const c=el.getContext('2d');c.clearRect(0,0,w,h);return{c,w,h,dpr}}
function axes(c,w,h,label){c.strokeStyle='#e4e8e1';c.lineWidth=1;for(let i=0;i<5;i++){let y=12+(h-32)*i/4;c.beginPath();c.moveTo(32,y);c.lineTo(w-12,y);c.stroke()}c.fillStyle='#8c968c';c.font='10px sans-serif';c.fillText(label,34,h-5)}
function plotSeries(id,series,kind,shadePair){
 const {c,w,h}=canvas(id);axes(c,w,h,kind==='wave'?'time / samples':kind==='residual'?'residual · amplitude':'frequency / kHz');
 const left=34,right=w-12,top=15,bottom=h-29,span=right-left;
 if(shadePair!==null&&kind==='fft'){const bandsPair=bands[shadePair];bandsPair.forEach((b,i)=>{c.fillStyle=i===0?'rgba(58,111,76,.095)':'rgba(105,130,153,.11)';let x=left+(b[0]/10000)*span,x2=left+(b[1]/10000)*span;c.fillRect(x,top,x2-x,bottom-top)})}
 let values=series.map(s=>s.data);let lo=0,hi=1;
 if(kind==='fft'){const all=values.flatMap(v=>Array.from(v.slice(0,Math.floor(10000*N/SR)+1),x=>20*Math.log10(Math.max(x,1e-12))));hi=Math.max(...all,-50);lo=hi-72}
 else{const max=Math.max(0.000001,...values.map(v=>{let m=0;for(let i=0;i<v.length;i++)m=Math.max(m,Math.abs(v[i]));return m}));hi=max*1.09;lo=-hi}
 series.forEach(s=>{
  c.beginPath();c.strokeStyle=s.color;c.lineWidth=1.6;c.globalAlpha=.94;
  const n=kind==='fft'?Math.floor(10000*N/SR)+1:s.data.length;
  for(let j=0;j<n;j++){const k=j,x=left+(j/(n-1))*span;let v=kind==='fft'?20*Math.log10(Math.max(s.data[k],1e-12)):s.data[k];const y=bottom-clamp((v-lo)/(hi-lo),0,1)*(bottom-top);if(j===0)c.moveTo(x,y);else c.lineTo(x,y)}
  c.stroke();c.globalAlpha=1;
 });
 c.fillStyle='#9ca69c';c.font='10px sans-serif';c.fillText(kind==='fft'?'0':kind==='wave'?'0':'−',left,h-15);c.textAlign='right';c.fillText(kind==='fft'?'10 kHz':kind==='wave'?'2048':'2048',right,h-15);c.textAlign='left';
}
function plotBlockFrames(id){
 const {c,w,h}=canvas(id),left=33,right=w-12,top=18,bottom=h-28;
 axes(c,w,h,'0 – 6 s · non-overlapping FFT frames');
 c.fillStyle='#dee6db';for(let i=0;i<FRAMES;i++){let x=left+i*(right-left)/FRAMES;c.fillRect(x,top,.65,bottom-top)}
 c.fillStyle='rgba(54,106,67,.20)';const x=left+state.frame*(right-left)/FRAMES;c.fillRect(x,top,Math.max(3,(right-left)/FRAMES),bottom-top);
 c.strokeStyle='#3e624b';c.beginPath();c.moveTo(x,top);c.lineTo(x,bottom);c.stroke();
}
function plotOverview(){
 let {c,w,h}=canvas('overviewPlot');c.strokeStyle='#e3e8df';c.beginPath();c.moveTo(0,h/2);c.lineTo(w,h/2);c.stroke();
 if(!state.env){c.fillStyle='#879588';c.font='12px sans-serif';c.fillText('载入真实音频后显示波形',13,h/2-8);return}
 const activeStart=state.block/12*w,activeEnd=(state.block+1)/12*w;
 c.fillStyle='rgba(59,107,73,.09)';c.fillRect(activeStart,0,activeEnd-activeStart,h);
 c.strokeStyle='#91a695';c.lineWidth=1;for(let i=0;i<state.env.length;i++){let x=i/state.env.length*w;c.beginPath();c.moveTo(x,h/2-state.env[i][0]*h*.4);c.lineTo(x,h/2-state.env[i][1]*h*.4);c.stroke()}
 let time=state.block*6+state.frame*N/SR,x=time/72*w;c.strokeStyle='#315f3e';c.lineWidth=2;c.beginPath();c.moveTo(x,0);c.lineTo(x,h);c.stroke();
}
function metrics(list){const parent=$('metrics');parent.textContent='';list.forEach(item=>{let div=document.createElement('div');div.className='metric';let b=document.createElement('b'),small=document.createElement('small');b.textContent=item[0];small.textContent=item[1];div.append(b,small);parent.append(div)})}
function setText(id,value){$(id).textContent=value}
function findRecord(channel,block){return state.records.find(x=>x.channel===channel&&Number(x.block)===block+1)}
function plotDetection(id,channel){
 const {c,w,h}=canvas(id);axes(c,w,h,'detector presence · saved CSV');
 let vals=Array.from({length:12},(_,i)=>findRecord(channel,i)),left=34,right=w-12,top=20,bottom=h-30;
 const threshold=.7199080718655814;
 c.strokeStyle='#b67c4d';c.setLineDash([5,4]);let y=bottom-threshold*(bottom-top);c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.setLineDash([]);
 vals.forEach((r,i)=>{let v=r?Number(r.presence_stat):0;if(!Number.isFinite(v))v=0;let x=left+i*(right-left)/12+3,bw=(right-left)/12-6; c.fillStyle=i===state.block?'#3f6950':'#a1b6a6';c.fillRect(x,bottom-clamp(v,0,1)*(bottom-top),Math.max(bw,2),clamp(v,0,1)*(bottom-top))});
 c.fillStyle='#8c968c';c.font='10px sans-serif';c.fillText('block 1',left,h-14);c.textAlign='right';c.fillText('12',right,h-14);c.textAlign='left';
}
function plotEnergy(id,orig,marked,pair){
 const {c,w,h}=canvas(id);axes(c,w,h,'average band power / relative dB');
 let a=energy(orig,pair),b=energy(marked,pair);let vals=[a.a,a.b,b.a,b.b].map(v=>10*Math.log10(Math.max(v,1e-20))),mx=Math.max(...vals),mn=Math.min(...vals)-1,base=h-32,top=24,left=36,dx=(w-left-25)/4;
 vals.forEach((v,i)=>{let normalized=(v-mn)/Math.max(1,mx-mn);let x=left+(i+.15)*dx,y=base-(base-top)*normalized;c.fillStyle=i<2?'#71869a':'#52775b';c.fillRect(x,y,dx*.62,base-y);c.fillStyle='#7d897e';c.font='10px sans-serif';c.textAlign='center';c.fillText(i%2?'B':'A',x+dx*.31,h-16)});c.textAlign='left';
}
function plotResultMini(id,channel){
 const {c,w,h}=canvas(id),vals=Array.from({length:12},(_,i)=>findRecord(channel,i));axes(c,w,h,'6 seconds / block');
 vals.forEach((r,i)=>{let left=34+i*(w-47)/12+2,bw=(w-47)/12-4;c.fillStyle=r&&r.status==='IDENTIFIED'?'#83ad89':'#c6a59b';c.fillRect(left,40,Math.max(3,bw),h-75);if(i===state.block){c.strokeStyle='#325c40';c.lineWidth=2;c.strokeRect(left-2,37,bw+4,h-69)}})
}
function renderRecovered(){
 const wrap=$('recoveredWrap');wrap.hidden=state.step!==6;if(wrap.hidden)return;
 const grid=$('recoveredGrid');grid.textContent='';
 for(let i=0;i<12;i++){let r=findRecord(state.channel,i);let btn=document.createElement('button');btn.type='button';btn.className='recover-block'+(i===state.block?' current':'')+(!r||r.status!=='IDENTIFIED'?' unknown':'');let s=document.createElement('small'),b=document.createElement('b');s.textContent=String(i+1).padStart(2,'0')+' · '+String(i*6).padStart(2,'0')+'s';b.textContent=r&&r.recovered&&r.recovered!=='None'?r.recovered:'UNKNOWN';btn.append(s,b);btn.addEventListener('click',()=>{state.block=i;render()});grid.append(btn)}
}
async function goChannel(name){state.channel=name;if(state.step>=4&&state.step<=6)await loadChannel();render()}
function render(){
 const stage=state.step,hd=headings[stage],start=state.block*BLOCK+state.frame*N,original=state.audio.original,marked=state.audio.marked;
 setText('stageNumber',hd[0]);setText('stageTitle',hd[1]);setText('stageDescription',hd[2]);
 document.querySelectorAll('[data-step]').forEach(el=>{const active=Number(el.dataset.step)===stage;el.classList.toggle('active',active);el.setAttribute('aria-current',active?'step':'false')});
 $('backBtn').disabled=stage===0;$('forwardBtn').disabled=stage===6;
 blockSelect.value=state.block;$('frameSeek').value=state.frame;setText('frameIndex','#'+String(state.frame+1).padStart(3,'0')+' / '+FRAMES);
 setText('timeReadout','选中 '+fmt(start/SR)+' – '+fmt((start+N)/SR));setText('sourceLabel',state.loaded?'已载入真实音频':'等待真实音频');
 $('pairField').style.display=stage===2?'flex':'none';$('channelField').style.display=stage>=4?'flex':'none';$('pairSelect').value=state.pair;$('channelSelect').value=state.channel;
 const hint=['选择任意帧，右侧显示它在 6 秒块中的位置。','时域和频域使用同一个 2048 点窗口。','A / B 频带由课程算法固定配置。','残差是真实样本差值，不是放大的音量效果。','MP3/AAC 经浏览器解码，不假设样本已精确对齐。','统计量来自已保存的冻结实验记录。','精选 C3-16 音乐案例；不代表全部音源表现。'][stage];setText('stageHint',hint);
 plotOverview();renderRecovered();
 if(!original||!marked){setText('leftTitle','等待原始音频');setText('rightTitle','等待水印音频');setText('leftMeta','真实数据');setText('rightMeta','真实数据');setText('insightTitle','请先载入真实实验数据');setText('insightText','图表不会用随机生成的波形替代真实结果。');metrics([]);['leftPlot','rightPlot'].forEach(id=>{const{c,w,h}=canvas(id);axes(c,w,h,'等待真实音频')});return}
 const x=frame(original,start),y=frame(marked,start),fx=fft(x),fy=fft(y);
 if(stage===0){setText('leftTitle','所选帧 · 时域波形');setText('rightTitle','141 帧分配位置');setText('leftMeta','x[n] / 2048 samples');setText('rightMeta','6 seconds');setText('leftFoot','原始 WAV · 所选 2048 点，无重叠分帧');setText('rightFoot','最后一帧长度不足时按算法补零');plotSeries('leftPlot',[{data:x,color:'#537b5d'}],'wave',null);plotBlockFrames('rightPlot');setText('insightTitle','分析窗口长度为 42.67 ms');setText('insightText','6 秒音频有 288000 个样本，按 2048 个一帧得到 141 帧（尾帧补零）。当前选择与下一步 FFT 共享同一位置。');metrics([[String(FRAMES),'每 6 秒帧数'],[(SR/N).toFixed(4)+' Hz','频率分辨率']])}
 if(stage===1){setText('leftTitle','当前 2048 点时域信号');setText('rightTitle','当前帧 FFT 幅度谱');setText('leftMeta','48 kHz');setText('rightMeta','0–10 kHz view');setText('leftFoot','横轴：2048 个时间样本');setText('rightFoot','rFFT 共 1025 个非负频率 bin；本图放大 0–10 kHz');plotSeries('leftPlot',[{data:x,color:'#537b5d'}],'wave',null);plotSeries('rightPlot',[{data:fx.magnitude,color:'#567b68'}],'fft',null);setText('insightTitle','同一帧：从样本到频率');setText('insightText','使用与课程算法一致的 2048 点 rFFT（前向变换不加窗）；频谱随所选音频帧实时更新。');metrics([['2048','FFT 点数'],['1025','单边频谱点数']])}
 if(stage===2){const a=energy(fx,state.pair),b=energy(fy,state.pair);setText('leftTitle','嵌入前 / 后的真实频谱');setText('rightTitle','A / B 频带平均功率');setText('leftMeta','原音灰蓝 · 水印绿');setText('rightMeta','灰蓝 原音 · 绿色 水印');setText('leftFoot','绿色高亮：频带 A；蓝灰高亮：频带 B · 仅显示 0–10 kHz');setText('rightFoot','柱形为 dB 对数功率，按当前绘图区自适应高度');plotSeries('leftPlot',[{data:fx.magnitude,color:'#71869a'},{data:fy.magnitude,color:'#3f7652'}],'fft',state.pair);plotEnergy('rightPlot',fx,fy,state.pair);setText('insightTitle','这一步改变的是相对频带能量');setText('insightText','图中显示已写入 WAV 的最终结果（包括嵌入后的 SNR 缩放），不是未经缩放的频域调制值。这里不猜测冻结密钥下的 bit/chip 位置。');metrics([[a.ratio.toFixed(3)+' dB','原音 A/B 相对能量比'],[(b.ratio-a.ratio>=0?'+':'')+(b.ratio-a.ratio).toFixed(4)+' dB','实际能量比变化']])}
 if(stage===3){let diff=new Float64Array(N);for(let i=0;i<N;i++)diff[i]=y[i]-x[i];setText('leftTitle','嵌入前 / 后波形叠加');setText('rightTitle','真实差分残差');setText('leftMeta','原音灰蓝 · 水印绿');setText('rightMeta','y[n] − x[n]');setText('leftFoot','两个曲线非常接近是正常现象');setText('rightFoot','差分图按残差自身幅值自动缩放，并非与左图同一比例');plotSeries('leftPlot',[{data:x,color:'#71869a'},{data:y,color:'#3f7652'}],'wave',null);plotSeries('rightPlot',[{data:diff,color:'#52775b'}],'residual',null);
 let p=0,e=0,off=state.block*BLOCK;for(let i=off;i<off+BLOCK;i++){const v=original[i],d=marked[i]-v;p+=v*v;e+=d*d}let snr=10*Math.log10(p/Math.max(e,1e-30));setText('insightTitle','水印不会凭空变成另一段声音');setText('insightText','水印音等于原音加上缩放后的调制残差。右图放大了真实差值，可观察其结构而不是用肉耳主观判断。');metrics([[snr.toFixed(2)+' dB','当前 6 秒块实际嵌入 SNR'],[(Math.sqrt(e/BLOCK)).toExponential(2),'残差 RMS']])}
 if(stage===4){const channelData=state.channel==='clean'?marked:state.audio[state.channel];const fc=fft(frame(channelData,start));setText('leftTitle','水印 WAV 的真实频谱');setText('rightTitle',names[state.channel]+' 解码后频谱');setText('leftMeta','原始采样位置');setText('rightMeta','浏览器解码后的相邻时刻');setText('leftFoot','输入：真实水印 WAV');setText('rightFoot','有损编码音频可能带时延；并非严格逐样本对应');plotSeries('leftPlot',[{data:fy.magnitude,color:'#71869a'}],'fft',null);if(channelData){plotSeries('rightPlot',[{data:fc.magnitude,color:'#3f7652'}],'fft',null)}else{const {c,w,h}=canvas('rightPlot');axes(c,w,h,'正在读取 '+names[state.channel]);}setText('insightTitle','观察真实编码后的频谱变化');setText('insightText','音频来源于已经发布的 MP3/AAC 文件；浏览器对其解码后用于频谱展示。当前界面不做参考对齐，因此不能把两图差值当作严格的检测残差。');metrics([[names[state.channel],'当前处理条件'],[channelData?'已解码':'读取中','真实信号状态']])}
 if(stage===5){const rec=findRecord(state.channel,state.block);setText('leftTitle','12 块 presence 检测统计量');setText('rightTitle','12 块状态概览');setText('leftMeta','虚线：接受阈值');setText('rightMeta','实际接受状态');setText('leftFoot','所选块深绿；虚线是 C3-16 冻结接受阈值');setText('rightFoot','绿色：IDENTIFIED；暖色：UNKNOWN');plotDetection('leftPlot',state.channel);plotResultMini('rightPlot',state.channel);setText('insightTitle','使用真实保存的检测结果');setText('insightText','检测器使用匹配原音、密钥和接收音，先形成候选消息，再检查 presence。这里绘制的是保存的 CSV，不会凭空重算缺少冻结密钥的检测器统计。');metrics([[rec?Number(rec.presence_stat).toFixed(4):'—','选中块 presence'],[rec?Number(rec.threshold).toFixed(4):'—','接受阈值']])}
 if(stage===6){const rec=findRecord(state.channel,state.block),all=Array.from({length:12},(_,i)=>findRecord(state.channel,i)),ok=all.filter(r=>r&&r.status==='IDENTIFIED').length;setText('leftTitle','逐块检测统计量');setText('rightTitle','十二个消息块恢复');setText('leftMeta','真实检测记录');setText('rightMeta',names[state.channel]);setText('leftFoot','不同 6 秒块的 presence 变化');setText('rightFoot','选中块已标出；点击下方任意数据块可跳转');plotDetection('leftPlot',state.channel);plotResultMini('rightPlot',state.channel);setText('insightTitle','恢复消息与是否接受需要区分');setText('insightText','C3-16 每个块独立承载 16 bit。下面以真实 CSV 中记录的消息和状态为准；绿色只代表通过检测器的存在性条件。');metrics([[ok+'/12','通过检测的块'],[rec&&rec.recovered?rec.recovered:'UNKNOWN','当前块恢复消息']])}
}
function chooseStep(n){state.step=clamp(n,0,6);if(state.step>=4)loadChannel().then(render);render()}
document.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>chooseStep(Number(b.dataset.step))));
$('backBtn').addEventListener('click',()=>chooseStep(state.step-1));$('forwardBtn').addEventListener('click',()=>chooseStep(state.step+1));
blockSelect.addEventListener('change',()=>{state.block=Number(blockSelect.value);render()});
$('frameSeek').addEventListener('input',()=>{state.frame=Number($('frameSeek').value);render()});
$('previousFrame').addEventListener('click',()=>{if(state.frame===0&&state.block>0){state.block--;state.frame=FRAMES-1}else state.frame=Math.max(0,state.frame-1);render()});
$('nextFrame').addEventListener('click',()=>{if(state.frame===FRAMES-1&&state.block<11){state.block++;state.frame=0}else state.frame=Math.min(FRAMES-1,state.frame+1);render()});
$('pairSelect').addEventListener('change',()=>{state.pair=Number($('pairSelect').value);render()});
$('channelSelect').addEventListener('change',()=>{goChannel($('channelSelect').value)});
$('loadBtn').addEventListener('click',loadCore);
$('overviewPlot').addEventListener('pointerdown',e=>{const r=e.currentTarget.getBoundingClientRect();let t=clamp((e.clientX-r.left)/r.width,0,.999999)*72;state.block=Math.floor(t/6);state.frame=clamp(Math.floor((t-state.block*6)*SR/N),0,FRAMES-1);render()});
window.addEventListener('resize',()=>{clearTimeout(window.__labResize);window.__labResize=setTimeout(render,120)});
render();
})();