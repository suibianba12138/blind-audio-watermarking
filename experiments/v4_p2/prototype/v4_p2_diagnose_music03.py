"""Reproduce P1 music_03 clean/MP3 cases and trace official parser stages."""
from __future__ import annotations
import json, os, sys, time, tempfile, subprocess
from pathlib import Path
import librosa
import numpy as np
import soundfile as sf
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.silentcipher_diagnostics import trace_official_decoder

MESSAGES=[[0x12,0x34,0x56,0x78,0x9A],[0xED,0xCB,0xA9,0x87,0x65]]

def main():
    official=Path(os.environ['SILENTCIPHER_SOURCE_ROOT']).resolve()
    model_dir=official/'Models/44_1_khz/73999_iteration'
    music_root=Path(os.environ['V4_P1_MUSIC_ROOT']).resolve()
    record=json.load(open(ROOT/'configs/v4_p1_source_manifest.json'))
    source=next(s for s in record['sources'] if s['source_id']=='music_03')
    path=music_root/source['relative_path']
    x,sr=sf.read(path,dtype='float32',always_2d=True)
    x=x.mean(axis=1)
    start=int(source['start_seconds']*sr); n=int(source['duration_seconds']*sr)
    x=x[start:start+n]
    if sr!=44100: x=librosa.resample(x,orig_sr=sr,target_sr=44100)
    x=np.asarray(x,dtype=np.float32)
    if len(x)<44100*12: x=np.pad(x,(0,44100*12-len(x)))
    x=x[:44100*12]
    sys.path.insert(0,str(official/'src'))
    from silentcipher import get_model
    torch.set_num_threads(4)
    t=time.perf_counter(); model=get_model(model_type='44.1k',ckpt_path=str(model_dir),config_path=str(model_dir/'hparams.yaml'),device='cpu')
    load_seconds=time.perf_counter()-t
    reports=[]
    for i,msg in enumerate(MESSAGES):
        marked,_=model.encode_wav(x,44100,msg,calc_sdr=True)
        with tempfile.TemporaryDirectory(prefix='v4-p2-music03-') as td:
            wav=Path(td)/'marked.wav'; mp3=Path(td)/'marked.mp3'; decoded=Path(td)/'decoded.wav'
            sf.write(wav,marked,44100,subtype='PCM_16')
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-ac','1','-ar','44100','-c:a','libmp3lame','-b:a','128k',str(mp3)],check=True,timeout=90)
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mp3),'-ac','1','-ar','44100','-c:a','pcm_f32le','-f','wav',str(decoded)],check=True,timeout=90)
            y,sr2=sf.read(decoded,dtype='float32')
        for condition,a in [('clean',np.asarray(marked,dtype=np.float32)),('mp3_128k',np.asarray(y,dtype=np.float32))]:
            t=time.perf_counter(); official_result=model.decode_wav(a,44100,phase_shift_decoding=False); elapsed=time.perf_counter()-t
            trace=trace_official_decoder(model,a,44100)
            reports.append({'message_id':i,'condition':condition,'expected_message':msg,
                            'official_result':official_result,'official_decode_seconds':elapsed,'trace':trace})
            print(f"message={i} condition={condition} official_status={official_result.get('status')} stage={trace['per_decoder'][0]['stage']} confidence={trace['per_decoder'][0].get('confidence')}",flush=True)
    out={'scope':'P1 frozen music_03 only; original P1 segment/messages; official unchanged 44.1 kHz weights; exploratory diagnosis',
         'model_load_seconds':load_seconds,'records':reports}
    dest=ROOT/'experiments/v4_p2/MUSIC03_DIAGNOSTIC.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'output':str(dest.relative_to(ROOT)),'model_load_seconds':load_seconds,'n_records':len(reports)}))
if __name__=='__main__': main()
