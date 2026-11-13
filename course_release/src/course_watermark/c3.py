"""C3 exploratory capacity candidate derived from the frozen C2 mechanism.

This module is isolated from the frozen C2 implementation.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import numpy as np
from numpy.typing import ArrayLike,NDArray
from scipy.signal import correlate,correlation_lags

@dataclass(frozen=True)
class Config:
 key:str
 sample_rate_hz:int=48000
 duration_seconds:float=6.0
 payload_bits:int=16
 n_fft:int=2048
 band_pairs_hz:tuple=((900.0,2200.0,2200.0,3500.0),(3500.0,5000.0,5000.0,6500.0),(6500.0,8000.0,8000.0,9500.0))
 target_snr_db:float=48.0
 max_alignment_ms:float=150.0

@dataclass(frozen=True)
class Detection:
 message:int
 bit_scores:tuple[float,...]
 presence_stat:float
 alignment_lag_samples:int
 residual_rms:float
 reference_similarity:float
 bit_coherence:tuple[float,...]

def _audio(v,n):
 x=np.asarray(v,dtype=np.float64)
 if x.ndim!=1 or not x.size or not np.isfinite(x).all():raise ValueError(f'{n} must be finite mono')
 return x
def _frames(x,cfg):
 n=cfg.n_fft;k=int(np.ceil(len(x)/n));return np.pad(x,(0,k*n-len(x))).reshape(k,n)
def _seed(cfg,*parts):return int.from_bytes(hashlib.sha256((cfg.key+'|'+'|'.join(map(str,parts))).encode()).digest()[:8],'little')
def _plan(x,cfg):
 fr=_frames(x,cfg);z=np.fft.rfft(fr,axis=1);f=np.fft.rfftfreq(cfg.n_fft,1/cfg.sample_rate_hz);pairs=[]
 for lo1,hi1,lo2,hi2 in cfg.band_pairs_hz:
  a=np.flatnonzero((f>=lo1)&(f<hi1));b=np.flatnonzero((f>=lo2)&(f<=hi2))
  if not len(a) or not len(b):raise ValueError('configured band pair contains no bins')
  pairs.append((a,b))
 rng=np.random.default_rng(_seed(cfg,'assign'));order=rng.permutation(len(fr));ass=np.empty(len(fr),dtype=int);ass[order]=np.arange(len(fr))%cfg.payload_bits
 chips=np.array([np.random.default_rng(_seed(cfg,'chip',t)).choice([-1.0,1.0]) for t in range(len(fr))])
 return fr,z,pairs,ass,chips
def _render(x,msg,cfg):
 fr,z,pairs,ass,chips=_plan(x,cfg);bits=np.array([(int(msg)>>(cfg.payload_bits-1-i))&1 for i in range(cfg.payload_bits)]);sym=2*bits-1;out=z.copy()
 for t in range(len(fr)):
  q=chips[t]*sym[ass[t]]
  for a,b in pairs:
   out[t,a]+=np.abs(z[t,a])*np.exp(1j*np.angle(z[t,a]))*q
   out[t,b]-=np.abs(z[t,b])*np.exp(1j*np.angle(z[t,b]))*q
 return np.fft.irfft(out,n=cfg.n_fft,axis=1).reshape(-1)[:len(x)]-x
def embed(reference:ArrayLike,message:int,cfg:Config)->NDArray[np.float64]:
 x=_audio(reference,'reference')
 if isinstance(message,bool) or not isinstance(message,(int,np.integer)) or not 0<=int(message)<(1<<cfg.payload_bits):raise ValueError(f'message must fit {cfg.payload_bits} bits')
 w=_render(x,int(message),cfg);wr=float(np.sqrt(np.mean(w*w)));xr=float(np.sqrt(np.mean(x*x)))
 if wr<=1e-15 or xr<=1e-15:raise ValueError('insufficient signal energy')
 return x+w*(xr*10**(-cfg.target_snr_db/20)/wr)
def _ratios(x,cfg):
 fr,z,pairs,ass,chips=_plan(x,cfg);out=[];tiny=1e-20
 for a,b in pairs:out.append(10*np.log10((np.mean(np.abs(z[:,a])**2,axis=1)+tiny)/(np.mean(np.abs(z[:,b])**2,axis=1)+tiny)))
 return ass,chips,np.mean(out,axis=0)
def _align(x,y,cfg):
 m=round(cfg.max_alignment_ms*cfg.sample_rate_hz/1000);c=correlate(y,x,mode='full',method='fft');ls=correlation_lags(y.size,x.size,mode='full');k=np.abs(ls)<=m;i=int(np.argmax(np.abs(c[k])));lag=int(ls[k][i])
 if lag>=0:yy=y[lag:];xx=x[:len(yy)]
 else:xx=x[-lag:];yy=y[:len(xx)]
 n=min(len(xx),len(yy));return xx[:n],yy[:n],lag
def detect(received:ArrayLike,reference:ArrayLike,cfg:Config)->Detection:
 y=_audio(received,'received');x0=_audio(reference,'reference');x,y,lag=_align(x0,y,cfg);n=round(cfg.duration_seconds*cfg.sample_rate_hz)
 if len(x)<int(.8*n):raise ValueError('aligned overlap too short')
 x=x[:n];y=y[:n];ass,chips,ry=_ratios(y,cfg);_,_,rx=_ratios(x,cfg);e=(ry-rx)*chips
 scores=np.zeros(cfg.payload_bits);counts=np.zeros(cfg.payload_bits);by=[[] for _ in range(cfg.payload_bits)]
 for t,v in enumerate(e):scores[ass[t]]+=v;counts[ass[t]]+=1;by[ass[t]].append(float(v))
 scores/=np.maximum(counts,1);coh=np.array([abs(sum(v))/max(sum(abs(q) for q in v),1e-15) for v in by]);msg=0
 for q in scores:msg=(msg<<1)|int(q>=0)
 xc=x-np.mean(x);yc=y-np.mean(y);sim=float(np.dot(xc,yc)/max(np.linalg.norm(xc)*np.linalg.norm(yc),1e-15))
 return Detection(msg,tuple(map(float,scores)),float(np.mean(coh)),lag,float(np.sqrt(np.mean((y-x)**2))),sim,tuple(map(float,coh)))
def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
