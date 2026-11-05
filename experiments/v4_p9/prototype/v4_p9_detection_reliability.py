from __future__ import annotations
import hashlib, json, math, os, resource, shutil, subprocess, sys, tempfile, time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly

ROOT = Path.cwd()
MANIFEST_PATH = ROOT / 'configs' / 'v4_p9_source_manifest.json'
OUTPUT_PATH = ROOT / 'experiments' / 'v4_p9' / 'RESULTS.json'
DATA_ROOT = Path(os.environ['V4_P9_DATA_ROOT'])
COMMONS_ROOT = Path(os.environ['V4_P9_COMMONS_ROOT'])
SOURCE_ROOT = Path(os.environ['SILENTCIPHER_SOURCE_ROOT'])
MODEL_DIR = Path(os.environ['SILENTCIPHER_MODEL_DIR'])
TARGET_SR = 44100
SAMPLES = TARGET_SR * 12
THRESHOLD = 0.6805555373430252


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def source_path(record: dict) -> Path:
    rel = Path(record['relative_path'])
    return (COMMONS_ROOT / rel.name) if rel.parts[0] == 'commons' else (DATA_ROOT / rel)


def read_crop(record: dict) -> np.ndarray:
    path = source_path(record)
    if sha256(path) != record['sha256']:
        raise RuntimeError('SOURCE_HASH_MISMATCH:' + record['source_id'])
    source_rate = int(record['sample_rate_hz'])
    start = int(round(float(record['crop_start_seconds']) * source_rate))
    count = int(round(float(record['crop_duration_seconds']) * source_rate))
    x, sr = sf.read(path, start=start, frames=count, dtype='float32', always_2d=True)
    if sr != source_rate or x.shape[0] != count:
        raise RuntimeError('SOURCE_CROP_INVALID:' + record['source_id'])
    x = x.mean(axis=1, dtype=np.float64).astype(np.float32)
    if sr != TARGET_SR:
        g = math.gcd(sr, TARGET_SR)
        x = resample_poly(x, TARGET_SR // g, sr // g).astype(np.float32)
    if x.shape[0] != SAMPLES or not np.all(np.isfinite(x)):
        raise RuntimeError('MODEL_INPUT_INVALID:' + record['source_id'])
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    if rms < 1e-6:
        raise RuntimeError('SOURCE_CROP_SILENT:' + record['source_id'])
    return x


def ffmpeg_roundtrip(input_wav: Path, codec: str, folder: Path, stem: str) -> tuple[np.ndarray, dict]:
    if codec == 'mp3_128k':
        encoded = folder / f'{stem}.mp3'
        encode = ['-c:a', 'libmp3lame', '-b:a', '128k']
    elif codec == 'aac_m4a_128k':
        encoded = folder / f'{stem}.m4a'
        encode = ['-c:a', 'aac', '-profile:a', 'aac_low', '-b:a', '128k', '-movflags', '+faststart']
    else:
        raise ValueError(codec)
    decoded = folder / f'{stem}_decoded.wav'
    t0 = time.perf_counter()
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(input_wav),'-ac','1','-ar',str(TARGET_SR),*encode,str(encoded)],check=True,capture_output=True,timeout=60)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(encoded),'-ac','1','-ar',str(TARGET_SR),'-c:a','pcm_f32le','-f','wav',str(decoded)],check=True,capture_output=True,timeout=60)
    elapsed=time.perf_counter()-t0
    y,sr=sf.read(decoded,dtype='float32')
    if sr != TARGET_SR or y.ndim != 1:
        raise RuntimeError('CODEC_DECODE_INVALID')
    before=len(y)
    if before < SAMPLES: y=np.pad(y,(0,SAMPLES-before))
    else: y=y[:SAMPLES]
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_name,profile,sample_rate,channels,bit_rate:format=duration','-of','json',str(encoded)],text=True))
    stream=probe['streams'][0]
    info={'codec':stream.get('codec_name'),'profile':stream.get('profile'),'sample_rate_hz':int(stream['sample_rate']),'channels':int(stream['channels']),'bit_rate':stream.get('bit_rate'),'container_duration_seconds':float(probe['format']['duration']),'decoded_sample_count_before_fit':before,'effective_sample_count':int(len(y)),'tail_samples_trimmed':max(0,before-SAMPLES),'samples_zero_padded':max(0,SAMPLES-before),'roundtrip_seconds':elapsed,'file_sha256':sha256(encoded)}
    return np.asarray(y,dtype=np.float32), info


def result_record(adapter, audio: np.ndarray, source_id: str, condition: str, message_id: str | None, expected_hex: str | None) -> dict:
    started=time.perf_counter()
    decoded=adapter.detect(audio,TARGET_SR)
    elapsed=time.perf_counter()-started
    candidate=decoded.get('candidate')
    candidate_hex=''.join(f'{int(b):02X}' for b in candidate) if candidate is not None else None
    exact=(candidate_hex==expected_hex) if expected_hex is not None and candidate_hex is not None else False
    state=decoded.get('state','UNKNOWN')
    accepted=state=='IDENTIFIED'
    return {'source_id':source_id,'message_id':message_id,'condition':condition,'official_status':decoded.get('official_status',False),'candidate_hex':candidate_hex,'confidence':decoded.get('confidence'),'state':state,'error_category':decoded.get('error_category'),'exception_type':decoded.get('exception_type'),'exact_message_recovery':exact if expected_hex is not None else None,'correct_accepted_recovery':bool(accepted and exact) if expected_hex is not None else None,'wrong_message_acceptance':bool(accepted and not exact) if expected_hex is not None else None,'negative_acceptance':bool(accepted) if expected_hex is None else None,'detect_seconds':elapsed,'adapter_detect_seconds':decoded.get('seconds')}


def external_m4a_blind_detect(path: Path, adapter) -> dict:
    # Deliberately receives only a file path and frozen detector. It has no original,
    # expected payload, source crop size, or embedding/session metadata.
    from app.v4_audio_processing import load_audio_file, prepare_audio
    data, meta=load_audio_file(path)
    prepared=prepare_audio(data,target_sample_rate=TARGET_SR,duration_seconds=12)
    record=result_record(adapter,prepared.samples.astype(np.float32),'external_m4a_sample','external_file_upload_blind',None,None)
    record['negative_acceptance']=None
    record['negative_acceptance_applicable']=False
    record['file_reader_input_sample_rate_hz']=int(meta['sample_rate_hz'])
    record['file_reader_decoded_sample_rate_hz']=int(data.sample_rate)
    record['prepared_sample_count']=int(prepared.samples.size)
    record['file_reader_container']=path.suffix.lower().lstrip('.')
    return record


def main():
    manifest=json.loads(MANIFEST_PATH.read_text())
    manifest_hash=sha256(MANIFEST_PATH)
    for varpath in [SOURCE_ROOT/'src',MODEL_DIR]:
        if not varpath.exists(): raise RuntimeError('MODEL_FILES_MISSING')
    torch.set_num_threads(4)
    try: torch.set_num_interop_threads(4)
    except RuntimeError: pass
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(SOURCE_ROOT/'src'))
    from silentcipher import get_model
    from app.silentcipher_adapter import SilentCipherAdapter, PresencePolicy
    model_weight_names=('enc_c.ckpt','dec_c.ckpt','dec_m_0.ckpt')
    weight_hashes={name:sha256(MODEL_DIR/name) for name in model_weight_names}
    non_model_checkpoint_hashes={p.name:sha256(p) for p in sorted(MODEL_DIR.glob('*.ckpt')) if p.name not in model_weight_names}
    model_started=time.perf_counter()
    model=get_model(model_type='44.1k',ckpt_path=str(MODEL_DIR),config_path=str(MODEL_DIR/'hparams.yaml'),device='cpu')
    load_s=time.perf_counter()-model_started
    adapter=SilentCipherAdapter(model=model,presence_policy=PresencePolicy(threshold=THRESHOLD,calibration='P1_FROZEN_PROVISIONAL'),cpu_threads=4)
    messages=manifest['messages_40bit_hex']
    records=[]; embeds=[]; codec_records=[]; ext_records=[]
    OUTPUT_PATH.parent.mkdir(parents=True,exist_ok=True)
    tmp_root=Path(tempfile.mkdtemp(prefix='v4-p9-run-'))
    try:
        positives=manifest['positive_sources']
        for si,source in enumerate(positives):
            clean=read_crop(source)
            for mi,msg_hex in enumerate(messages):
                msg=list(bytes.fromhex(msg_hex))
                work=tmp_root/f'pos_{si:02d}_{mi}'; work.mkdir()
                t0=time.perf_counter()
                marked,sdr=model.encode_wav(clean,TARGET_SR,msg,calc_sdr=True)
                embed_s=time.perf_counter()-t0
                marked=np.asarray(marked,dtype=np.float32)
                if marked.shape!=clean.shape or not np.all(np.isfinite(marked)): raise RuntimeError('EMBED_OUTPUT_INVALID')
                mark_path=work/'marked.wav'; sf.write(mark_path,marked,TARGET_SR,subtype='PCM_16')
                marked_pcm,sr=sf.read(mark_path,dtype='float32')
                if sr!=TARGET_SR or marked_pcm.size!=SAMPLES: raise RuntimeError('MARKED_WAV_INVALID')
                err=clean.astype(np.float64)-marked.astype(np.float64)
                snr=10*math.log10((float(np.mean(clean.astype(np.float64)**2))+1e-30)/(float(np.mean(err**2))+1e-30))
                emb={'source_id':source['source_id'],'message_id':f'M{mi+1}','message_hex':msg_hex,'embed_seconds':embed_s,'reported_sdr_db':float(sdr),'embedding_snr_db':snr,'one_embedding_shared_across_channels':True,'marked_pcm16_sha256':sha256(mark_path)}
                embeds.append(emb)
                clean_record=result_record(adapter,marked_pcm,source['source_id'],'clean_wav',f'M{mi+1}',msg_hex); records.append(clean_record)
                for codec in ('mp3_128k','aac_m4a_128k'):
                    recv,meta=ffmpeg_roundtrip(mark_path,codec,work,f'marked_{codec}')
                    codec_records.append({'source_id':source['source_id'],'message_id':f'M{mi+1}','positive':True,'condition':codec,**meta})
                    r=result_record(adapter,recv,source['source_id'],codec,f'M{mi+1}',msg_hex); r['channel_metadata']=meta; records.append(r)
                    if source['source_id']=='music_commons_01' and mi==0 and codec=='aac_m4a_128k':
                        ext=external_m4a_blind_detect(work/'marked_aac_m4a_128k.m4a',adapter)
                        ext['source_id']=source['source_id']; ext['message_id']='M1'; ext['expected_message_hex_offline_scoring_only']=msg_hex
                        ext['exact_message_recovery_offline_scored']=ext.get('candidate_hex')==msg_hex
                        ext['correct_accepted_recovery_offline_scored']=bool(ext['state']=='IDENTIFIED' and ext.get('candidate_hex')==msg_hex)
                        ext_records.append(ext)
                print(f"POS {source['source_id']} M{mi+1} complete",flush=True)
        for ni,source in enumerate(manifest['negative_sources']):
            clean=read_crop(source)
            work=tmp_root/f'neg_{ni:02d}'; work.mkdir()
            source_path_wav=work/'negative_source.wav'; sf.write(source_path_wav,clean,TARGET_SR,subtype='PCM_16')
            wav,sr=sf.read(source_path_wav,dtype='float32')
            if sr!=TARGET_SR or wav.size!=SAMPLES: raise RuntimeError('NEGATIVE_WAV_INVALID')
            records.append(result_record(adapter,wav,source['source_id'],'unwatermarked_clean_wav',None,None))
            for codec in ('mp3_128k','aac_m4a_128k'):
                recv,meta=ffmpeg_roundtrip(source_path_wav,codec,work,f'negative_{codec}')
                codec_records.append({'source_id':source['source_id'],'positive':False,'condition':codec,**meta})
                r=result_record(adapter,recv,source['source_id'],'unwatermarked_'+codec,None,None); r['channel_metadata']=meta; records.append(r)
            print(f"NEG {source['source_id']} complete",flush=True)
        result={
          'protocol_id':manifest['protocol_id'],'manifest_sha256':manifest_hash,'model':manifest['model']['name'],'model_sample_rate_hz':TARGET_SR,'duration_seconds':12,'message_sdr_db':47,'messages_40bit_hex':messages,'presence_threshold_frozen':THRESHOLD,'presence_threshold_source':'P1 development-only calibration, unchanged','presence_calibration':'PROVISIONAL','phase_shift_decoding':False,'model_load_seconds':load_s,'checkpoint_sha256':weight_hashes,'non_model_checkpoint_file_sha256':non_model_checkpoint_hashes,'checkpoint_loading_note':'Official loader loads enc_c.ckpt, dec_c.ckpt, dec_m_0.ckpt; optimizer checkpoint is not loaded by get_model.','torch_version':torch.__version__,'cpu_threads':4,'ffmpeg_version':manifest['codecs']['ffmpeg_version'],'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_count':len(positives),'negative_source_count':len(manifest['negative_sources']),'embedding_records':embeds,'codec_records':codec_records,'records':records,'external_file_blind_check':ext_records,'status':'COMPLETED'
        }
        OUTPUT_PATH.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print('RESULTS_WRITTEN',OUTPUT_PATH.name,'positive records',sum(r['expected_message_hex_offline_scoring_only'] if False else 1 for r in []),'detections',len(records),'external',len(ext_records),'peak_rss_kib',result['peak_rss_kib'],flush=True)
    finally:
        shutil.rmtree(tmp_root,ignore_errors=True)

if __name__=='__main__': main()
