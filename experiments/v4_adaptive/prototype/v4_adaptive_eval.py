from __future__ import annotations
import hashlib, json, os, random, resource, subprocess, sys, time
from pathlib import Path
import librosa
import numpy as np
import soundfile as sf
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.adaptive_watermarking import AdaptiveWatermarkEmbedder, blind_detect, run_v4_channel
from app.silentcipher_adapter import PresencePolicy

MANIFEST=json.loads((ROOT/'configs/v4_adaptive_source_protocol.json').read_text())
EXPECTED_CHECKPOINTS={
 'enc_c.ckpt':'ff64f80d2391fdfc888e4103c499be4a2c958e59626587a1eab6db93204814c7',
 'dec_c.ckpt':'c23b57635172b2fbd3a8531d15ba76b5885a10d0fe902ccb823c521c56041b33',
 'dec_m_0.ckpt':'829540c058270d29788f05294894d45bf436e44add0e1099422242ebb94b7088',
}
SR=44100
CHANNELS=tuple(MANIFEST['target_channels'])
POLICY=PresencePolicy(float(MANIFEST['presence_threshold_frozen']),'PROVISIONAL')


def _sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()


def _load_source(source):
 root=Path(os.environ[source['root_env']])
 rel=source.get('relative_path',source.get('source_file'))
 path=root/rel
 if _sha(path)!=source['sha256']:
  raise RuntimeError('source_hash_mismatch:'+source['source_id'])
 with sf.SoundFile(path) as f:
  if int(f.samplerate)!=int(source['source_sample_rate_hz']):
   raise RuntimeError('source_sample_rate_mismatch:'+source['source_id'])
  start=int(float(source.get('source_crop_start_seconds',source.get('crop_start_seconds',0))) * f.samplerate)
  f.seek(start)
  x=f.read(frames=int(12*f.samplerate),dtype='float32',always_2d=True)
  rate=int(f.samplerate)
 if len(x)<int(12*rate):
  x=np.pad(x,((0,int(12*rate)-len(x)),(0,0)))
 x=x.mean(axis=1)
 if rate!=SR:
  x=librosa.resample(x,orig_sr=rate,target_sr=SR)
 n=12*SR
 if len(x)<n: x=np.pad(x,(0,n-len(x)))
 x=np.asarray(x[:n],dtype=np.float32)
 return x,{'source_sample_rate_hz':rate,'model_sample_rate_hz':SR,
  'sample_count':int(x.size),'duration_seconds':float(x.size/SR),
  'input_rms':float(np.sqrt(np.mean(x.astype(np.float64)**2))),
  'input_peak_abs':float(np.max(np.abs(x))),'resampled_once':rate!=SR}


def _safe_candidate(c):
 if c is None:return None
 try:return bytes(c).hex().upper()
 except Exception:return None


def _strip_audio(candidate):
 return {k:v for k,v in candidate.items() if k!='selected_audio'}


def _run_positive(model,source,partition,source_audio,meta,payload_hex):
 payload=bytes.fromhex(payload_hex)
 def embed_fn(audio,message,sr,strength):
  torch.manual_seed(int(MANIFEST['random_seed']))
  marked,_=model.encode_wav(audio,sr,list(message),message_sdr=strength,calc_sdr=False)
  return marked
 def detect_fn(received,sr):
  return blind_detect(model,received,sr,POLICY)
 engine=AdaptiveWatermarkEmbedder(embed_fn,detect_fn,run_v4_channel,
  min_snr_db=MANIFEST['quality_gate']['minimum_snr_db'],
  max_lsd_db=MANIFEST['quality_gate']['maximum_lsd_db'])
 result=engine.embed(source_audio,payload,SR,CHANNELS)
 candidate_records=result['candidate_results']
 baseline=candidate_records[0]
 selected=next((r for r in candidate_records if r['message_sdr_db']==result['selected_message_sdr_db']),None)
 return {
  'partition':partition,'source_id':source['source_id'],'category':source['category'],
  'source_sha256':source['sha256'],'payload_hex':payload_hex,'input_metadata':meta,
  'fixed_47_baseline':baseline,
  'adaptive_selected_sdr_db':result['selected_message_sdr_db'],
  'adaptive_status':result['status'],'adaptive_total_seconds':result['total_seconds'],
  'adaptive_selected':selected,
  'attempted_candidate_count':result['candidate_count'],
  'attempted_strengths_db':[r['message_sdr_db'] for r in candidate_records],
  'candidate_results':candidate_records,
 }


def _run_negative(model,source,source_audio,meta):
 channels={}
 for ch in CHANNELS:
  transformed=run_v4_channel(source_audio,SR,ch)
  started=time.perf_counter()
  decoded=blind_detect(model,transformed['audio'],transformed['sample_rate'],POLICY)
  det_s=time.perf_counter()-started
  channels[ch]={
   'state':decoded['state'],'candidate_hex':_safe_candidate(decoded.get('candidate')),
   'confidence':decoded.get('confidence'),'official_status':decoded.get('official_status'),
   'negative_acceptance':decoded.get('state')=='IDENTIFIED',
   'detection_seconds':det_s,'channel_seconds':transformed.get('channel_seconds',0),
   'channel_metadata':transformed.get('metadata',{}),
  }
 return {'source_id':source['source_id'],'category':source['category'],'source_sha256':source['sha256'],
  'input_metadata':meta,'channels':channels}


def main():
 random.seed(MANIFEST['random_seed']); np.random.seed(MANIFEST['random_seed'])
 torch.set_num_threads(4)
 try: torch.set_num_interop_threads(1)
 except RuntimeError: pass
 model_root=Path(os.environ['SILENTCIPHER_MODEL_DIR'])
 source_root=Path(os.environ['SILENTCIPHER_SOURCE_ROOT'])
 checkpoint_hashes={n:_sha(model_root/n) for n in EXPECTED_CHECKPOINTS}
 if checkpoint_hashes!=EXPECTED_CHECKPOINTS: raise RuntimeError('checkpoint_hash_mismatch')
 sys.path.insert(0,str(source_root/'src'))
 from silentcipher import get_model
 load_started=time.perf_counter()
 model=get_model('44.1k',str(model_root),str(model_root/'hparams.yaml'),'cpu')
 model_load_seconds=time.perf_counter()-load_started
 ffmpeg=subprocess.run(['ffmpeg','-version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
 all_sources=(MANIFEST['historical_development_sources']+MANIFEST['new_source_evaluation'])
 loaded={}
 source_meta={}
 for s in all_sources:
  loaded[s['source_id']],source_meta[s['source_id']]=_load_source(s)
 positive=[]
 negatives=[]
 start_all=time.perf_counter()
 dest_value=os.environ.get('V4_ADAPTIVE_RESULTS_PATH')
 dest=Path(dest_value) if dest_value else ROOT/'experiments/v4_adaptive/RESULTS.json'
 if not dest.is_absolute(): dest=ROOT/dest
 dest.parent.mkdir(parents=True,exist_ok=True)
 output={
  'status':'RUNNING','protocol_id':MANIFEST['protocol_id'],
  'manifest_sha256':_sha(ROOT/'configs/v4_adaptive_source_protocol.json'),
  'model':'Sony SilentCipher official 44.1 kHz 73999_iteration','checkpoint_sha256':checkpoint_hashes,
  'presence_threshold_frozen':POLICY.threshold,'presence_calibration':POLICY.calibration,
  'candidate_strengths_db':list(MANIFEST['message_sdr_candidates_db']),'channels':list(CHANNELS),
  'cpu_threads':4,'torch_version':torch.__version__,'ffmpeg_version':ffmpeg,
  'model_load_seconds':model_load_seconds,'positive_records':positive,'negative_records':negatives,
 }
 def save_progress(status='RUNNING'):
  output['status']=status
  output['peak_rss_kib']=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
  output['experiment_seconds']=time.perf_counter()-start_all
  temp=dest.with_suffix(dest.suffix+'.tmp')
  temp.write_text(json.dumps(output,indent=2,sort_keys=True,allow_nan=False)+'\n')
  temp.replace(dest)
 for s in all_sources:
  partition='historical_development' if s in MANIFEST['historical_development_sources'] else 'source_disjoint_evaluation'
  for payload_hex in s['payload_hex']:
   row=_run_positive(model,s,partition,loaded[s['source_id']],source_meta[s['source_id']],payload_hex)
   positive.append(row)
   save_progress()
   print(f"positive {s['source_id']} {payload_hex}: {row['adaptive_status']} selected={row['adaptive_selected_sdr_db']} tried={row['attempted_strengths_db']}",flush=True)
 for s in MANIFEST['new_source_evaluation']:
  row=_run_negative(model,s,loaded[s['source_id']],source_meta[s['source_id']])
  negatives.append(row)
  save_progress()
  print(f"negative {s['source_id']}: "+','.join(f"{k}={v['state']}" for k,v in row['channels'].items()),flush=True)
 save_progress('COMPLETE')
 print(json.dumps({'output':'configured result artifact','status':output['status'],
  'positive_records':len(positive),'negative_sources':len(negatives),
  'peak_rss_kib':output['peak_rss_kib'],'model_load_seconds':model_load_seconds,
  'experiment_seconds':output['experiment_seconds']},indent=2))

if __name__=='__main__': main()
