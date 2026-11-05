from __future__ import annotations
import os, sys, json, time, math, hashlib, random, resource, tempfile, subprocess, traceback
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
import torch

V4=Path(__file__).resolve().parents[1]
V3=Path(os.environ['V3_SOURCE_ROOT'])
P0=Path(os.environ['SILENTCIPHER_SOURCE_ROOT'])
MODEL=Path(os.environ['SILENTCIPHER_MODEL_DIR'])
MANIFEST=V4/'configs/v4_p1_source_manifest.json'
OUT=V4/'experiments/v4_p1'
MSG=[ [0x12,0x34,0x56,0x78,0x9A], [0xED,0xCB,0xA9,0x87,0x65] ]
V3MSG=[0x12,0xED]
SEED=20261104

def source_path(s):
    if s['source_id'].startswith('music_'):
        return Path(os.environ['V4_P1_MUSIC_ROOT'])/s['relative_path']
    return Path(os.environ['V4_P1_MUSAN_ROOT'])/s['relative_path']

def read_segment(s):
    p=source_path(s)
    x,sr=sf.read(p,dtype='float32',always_2d=True)
    x=x.mean(axis=1)
    start=int(s['start_seconds']*sr); n=int(s['duration_seconds']*sr)
    x=x[start:start+n]
    if len(x)!=n: raise ValueError('source shorter than frozen segment')
    if sr!=44100: x=librosa.resample(x,orig_sr=sr,target_sr=44100)
    x=np.asarray(x,dtype=np.float32)
    n441=44100*12
    if len(x)<n441: x=np.pad(x,(0,n441-len(x)))
    return x[:n441]

def mp3_roundtrip(x, root, stem, sr=44100):
    with tempfile.TemporaryDirectory(prefix='v4-p1-codec-') as td:
        td=Path(td); wav=td/'in.wav'; mp3=td/'rt.mp3'; out=td/'out.wav'
        sf.write(wav,x,sr,subtype='PCM_16')
        t=time.perf_counter()
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-ac','1','-ar',str(sr),'-c:a','libmp3lame','-b:a','128k',str(mp3)],check=True,timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mp3),'-ac','1','-ar',str(sr),'-c:a','pcm_f32le','-f','wav',str(out)],check=True,timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        codec_s=time.perf_counter()-t
        y,sr=sf.read(out,dtype='float32')
        n=int(sr*12); y=np.asarray(y[:n],dtype=np.float32)
        if len(y)<n: y=np.pad(y,(0,n-len(y)))
        return y,codec_s,mp3.stat().st_size

def snr_lsd(x,y):
    n=min(len(x),len(y)); x=np.asarray(x[:n],np.float64); y=np.asarray(y[:n],np.float64)
    err=np.mean((x-y)**2); power=np.mean(x*x)
    snr=float(10*np.log10((power+1e-30)/(err+1e-30)))
    # Frozen analysis: 4096 Hann, 2048 hop, magnitude log difference, dB RMS over bins/frames.
    def spec(z):
        if len(z)<4096: z=np.pad(z,(0,4096-len(z)))
        frames=np.lib.stride_tricks.sliding_window_view(z,4096)[::2048]
        return np.abs(np.fft.rfft(frames*np.hanning(4096),axis=1))
    a,b=spec(x),spec(y); eps=max(float(np.max(a))*1e-8,1e-12)
    delta=20*np.log10((b+eps)/(a+eps))
    lsd=float(np.sqrt(np.mean(delta*delta)))
    return snr,lsd

def normalize_result(r):
    if isinstance(r,list): r=r[0] if r else {}
    return {'status':bool(r.get('status',False)), 'messages':r.get('messages',[]), 'confidences':r.get('confidences',[]), 'error':r.get('error')}

def decode_sc(model,x,condition,source_id,message_id=None):
    t=time.perf_counter(); err=None
    try: r=normalize_result(model.decode_wav(x,44100,phase_shift_decoding=False))
    except Exception as e: r={'status':False,'messages':[],'confidences':[],'error':type(e).__name__}; err=type(e).__name__
    dt=time.perf_counter()-t
    candidate=(r['messages'][0] if r['messages'] else None)
    conf=(float(r['confidences'][0]) if r['confidences'] else None)
    exact=bool(message_id is not None and candidate==MSG[message_id])
    return {'engine':'SilentCipher','source_id':source_id,'condition':condition,'message_id':message_id,'status':r['status'],'decoded_message':candidate,'confidence':conf,'per_frame_confidences':r['confidences'],'exact_message_recovery':exact if message_id is not None else None,'wrong_message_acceptance_raw_status':bool(message_id is not None and r['status'] and not exact),'decode_error':err or r.get('error'),'decode_seconds':dt}

def main():
    torch.set_num_threads(4)
    sys.path.insert(0,str(P0/'src'))
    sys.path.insert(0,str(V3/'src'))
    sys.path.insert(0,str(V3))
    from silentcipher import get_model
    from app.v3_api import embed_message as v3_embed, detect_message as v3_detect
    from app.audio_io import AudioData
    t=time.perf_counter(); model=get_model(model_type='44.1k',ckpt_path=str(MODEL),config_path=str(MODEL/'hparams.yaml'),device='cpu'); load_s=time.perf_counter()-t
    sources=json.load(open(MANIFEST))['sources']
    records=[]; source_meta={}; marked_cache={}
    # SilentCipher: 24 embeddings and 72 decodes (48 marked, 24 negatives).
    for s in sources:
        sid=s['source_id']; x=read_segment(s); source_meta[sid]=s
        neg_mp3,neg_codec,neg_bytes=mp3_roundtrip(x,OUT,sid+'_negative')
        source_meta[sid]['mp3_codec_seconds']=neg_codec
        source_meta[sid]['mp3_bytes_negative']=neg_bytes
        records.append(decode_sc(model,x,'negative_raw',sid))
        records.append(decode_sc(model,neg_mp3,'negative_mp3_128k',sid))
        for mid,msg in enumerate(MSG):
            t=time.perf_counter(); marked,reported=model.encode_wav(x,44100,msg,calc_sdr=True); enc_s=time.perf_counter()-t
            marked=np.asarray(marked,dtype=np.float32)
            snr,lsd=snr_lsd(x,marked)
            mp3,codec_s,mp3_bytes=mp3_roundtrip(marked,OUT,sid+f'_m{mid}')
            marked_cache[(sid,mid)]=marked
            rec=decode_sc(model,marked,'positive_clean',sid,mid); rec.update({'encode_seconds':enc_s,'reported_sdr_db':float(reported),'embedding_snr_db':snr,'embedding_lsd_db':lsd}); records.append(rec)
            rec=decode_sc(model,mp3,'positive_mp3_128k',sid,mid); rec.update({'encode_seconds':enc_s,'mp3_codec_seconds':codec_s,'mp3_bytes':mp3_bytes,'embedding_snr_db':snr,'embedding_lsd_db':lsd}); records.append(rec)
        print(f'SILENTCIPHER_SOURCE_DONE {sid}',flush=True)
    # V3: fixed public 6 s / 48 kHz / 8-bit protocol, same source, two payloads.
    for s in sources:
        sid=s['source_id']; x=read_segment(s); x6=x[:44100*6]
        from app.audio_io import resample_audio
        v3raw=resample_audio(AudioData(x6,44100),48000)
        v3mp3full,_,_=mp3_roundtrip(x,OUT,sid+'_v3neg')
        v3mp3=resample_audio(AudioData(v3mp3full[:44100*6],44100),48000)
        for cond,a in [('negative_raw',v3raw),('negative_mp3_128k',v3mp3)]:
            t=time.perf_counter()
            try: d=v3_detect(a); e=None
            except Exception as ex: d=None; e=type(ex).__name__
            records.append({'engine':'V3','source_id':sid,'condition':cond,'message_id':None,'status':bool(d and d.status=='IDENTIFIED'),'decoded_message':(d.message if d else None),'confidence':(d.presence_score if d else None),'threshold':(d.threshold if d else 0.7855073980199624),'exact_message_recovery':None,'wrong_message_acceptance_raw_status':None,'decode_error':e,'decode_seconds':time.perf_counter()-t})
        for mid,msg40 in enumerate(MSG):
            m8=V3MSG[mid]
            t=time.perf_counter()
            try: emb=v3_embed(v3raw,m8); enc_s=time.perf_counter()-t; marked48=emb.audio
            except Exception as ex:
                records.append({'engine':'V3','source_id':sid,'condition':'positive_clean','message_id':mid,'status':False,'decode_error':'embed_'+type(ex).__name__,'encode_seconds':time.perf_counter()-t}); continue
            v3snr,v3lsd=snr_lsd(marked48.samples,v3raw.samples)
            t=time.perf_counter();
            try: d=v3_detect(marked48); e=None
            except Exception as ex: d=None; e=type(ex).__name__
            records.append({'engine':'V3','source_id':sid,'condition':'positive_clean','message_id':mid,'status':bool(d and d.status=='IDENTIFIED'),'decoded_message':(d.message if d else None),'confidence':(d.presence_score if d else None),'threshold':(d.threshold if d else 0.7855073980199624),'exact_message_recovery':bool(d and d.message==m8),'wrong_message_acceptance_raw_status':bool(d and d.status=='IDENTIFIED' and d.message!=m8),'decode_error':e,'encode_seconds':enc_s,'decode_seconds':time.perf_counter()-t,'embedding_snr_db':v3snr,'embedding_lsd_db':v3lsd,'message_bits':8,'expected_v3_message':m8})
            # MP3 positive from the marked V3 audio.
            rt,codec_s,bytes_=mp3_roundtrip(np.asarray(marked48.samples[:48000*6],dtype=np.float32),OUT,sid+'_v3pos',sr=48000)
            rt48=AudioData(rt[:48000*6],48000)
            t=time.perf_counter()
            try: d=v3_detect(rt48); e=None
            except Exception as ex: d=None; e=type(ex).__name__
            records.append({'engine':'V3','source_id':sid,'condition':'positive_mp3_128k','message_id':mid,'status':bool(d and d.status=='IDENTIFIED'),'decoded_message':(d.message if d else None),'confidence':(d.presence_score if d else None),'threshold':(d.threshold if d else 0.7855073980199624),'exact_message_recovery':bool(d and d.message==m8),'wrong_message_acceptance_raw_status':bool(d and d.status=='IDENTIFIED' and d.message!=m8),'decode_error':e,'encode_seconds':enc_s,'decode_seconds':time.perf_counter()-t,'mp3_codec_seconds':codec_s,'mp3_bytes':bytes_,'embedding_snr_db':v3snr,'embedding_lsd_db':v3lsd,'message_bits':8,'expected_v3_message':m8})
        print(f'V3_SOURCE_DONE {sid}',flush=True)
    # Dev-only exploratory threshold: midpoint between the highest emitted negative
    # confidence and the lowest positive confidence when the development scores separate.
    devids={s['source_id'] for s in sources if s['split']=='dev'}
    dev_pos=[float(r.get('confidence') or 0.0) for r in records if r.get('engine')=='SilentCipher' and r['source_id'] in devids and r['condition'].startswith('positive_')]
    dev_neg=[float(r.get('confidence') or 0.0) for r in records if r.get('engine')=='SilentCipher' and r['source_id'] in devids and r['condition'].startswith('negative_')]
    if dev_pos and dev_neg and max(dev_neg)<min(dev_pos):
        threshold={'threshold':(max(dev_neg)+min(dev_pos))/2.0,'selection':'midpoint_between_dev_negative_max_and_positive_min','dev_min_positive_score':min(dev_pos),'dev_max_negative_score':max(dev_neg),'dev_positive_n':len(dev_pos),'dev_negative_n':len(dev_neg)}
    else:
        candidates=sorted({0.0}|{float(r['confidence']) for r in records if r.get('engine')=='SilentCipher' and r['source_id'] in devids and r.get('confidence') is not None})
        best=None
        for th0 in candidates:
            tp=fp=tn=fn=0
            for r in records:
                if r.get('engine')!='SilentCipher' or r['source_id'] not in devids: continue
                label=r['condition'].startswith('positive_'); score=float(r.get('confidence') or 0.0)
                pred=bool(r.get('status') and score>=th0)
                if label and pred: tp+=1
                elif label: fn+=1
                elif pred: fp+=1
                else: tn+=1
            sens=tp/(tp+fn) if tp+fn else 0; spec=tn/(tn+fp) if tn+fp else 0
            key=((sens+spec)/2, sens+spec, -th0)
            if best is None or key>best[0]: best=(key,{'threshold':th0,'selection':'dev_balanced_accuracy_fallback','dev_tp':tp,'dev_fn':fn,'dev_fp':fp,'dev_tn':tn,'dev_sensitivity':sens,'dev_specificity':spec,'dev_balanced_accuracy':(sens+spec)/2})
        threshold=best[1] if best else None
    if threshold:
        th=threshold['threshold']
        for r in records:
            if r.get('engine')=='SilentCipher':
                r['exploratory_presence_accepted']=bool(r.get('status') and (r.get('confidence') or 0.0)>=th)
                if r['condition'].startswith('positive_'):
                    r['correct_accepted_recovery']=bool(r['exploratory_presence_accepted'] and r.get('exact_message_recovery'))
                    r['wrong_message_acceptance']=bool(r['exploratory_presence_accepted'] and not r.get('exact_message_recovery'))
                else:
                    r['negative_acceptance']=r['exploratory_presence_accepted']
    result={'status':'RUNTIME_PASS' if len(records)>0 else 'FAILED','scope':'12 independent source IDs; two 40-bit messages each; small engineering validation only','random_seed':SEED,'messages_40bit':MSG,'v3_messages_8bit':V3MSG,'model_load_seconds_warm_cache':load_s,'torch_version':torch.__version__,'python_version':sys.version.split()[0],'cpu_threads':torch.get_num_threads(),'model_type':'official 44.1k / 73999_iteration','model_checkpoint_sha256':{'enc_c.ckpt':'ff64f80d2391fdfc888e4103c499be4a2c958e59626587a1eab6db93204814c7','dec_c.ckpt':'c23b57635172b2fbd3a8531d15ba76b5885a10d0fe902ccb823c521c56041b33','dec_m_0.ckpt':'829540c058270d29788f05294894d45bf436e44add0e1099422242ebb94b7088'},'exploratory_presence_threshold_dev_only':threshold,'source_results':source_meta,'records':records,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'RESULTS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    import csv
    keys=sorted(set().union(*(r.keys() for r in records)))
    with (OUT/'RESULTS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(records)
    print(json.dumps({'status':result['status'],'n_records':len(records),'load_s':load_s,'threshold':threshold,'peak_rss_kib':result['peak_rss_kib']},indent=2),flush=True)

if __name__=='__main__': main()
