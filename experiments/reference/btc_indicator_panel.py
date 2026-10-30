"""Causal 20-indicator BTC expansion probability panel (research only)."""

from __future__ import annotations

import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

WINDOWS=(32,64,128)
NAMES=('NSE-v1','NSW-v1','Bollinger bandwidth','Normalized ATR','Realized volatility',
       'Parkinson volatility','Garman-Klass volatility','Rogers-Satchell volatility',
       'Donchian width','Keltner width','RSI','Normalized MACD histogram','ADX',
       'Kaufman efficiency ratio','Rate of change','Stochastic %K','OBV slope',
       'Chaikin money flow','Money flow index','Relative volume')

def _spectral_width(values,w,use_gpu):
    out=np.full(len(values),np.nan); r=np.diff(np.log(values))
    if len(r)<w:return out
    xp=np
    if use_gpu:
        import cupy as cp; xp=cp
    batch=8192
    for start in range(0,len(r)-w+1,batch):
        stop=min(start+batch,len(r)-w+1)
        idx=np.arange(start,stop)[:,None]+np.arange(w)[None,:]
        x=xp.asarray(r[idx]); x=x-x.mean(axis=1,keepdims=True)
        p=xp.abs(xp.fft.rfft(x,axis=1))**2; p=p[:,1:]
        f=xp.fft.rfftfreq(w)[1:]; total=p.sum(axis=1)
        cen=(p*f).sum(axis=1)/total
        width=xp.sqrt((p*(f-cen[:,None])**2).sum(axis=1)/total)/0.5
        width=xp.asnumpy(width) if use_gpu else width
        out[np.arange(start,stop)+w]=width
    return out

def features(df,w,use_gpu=False):
    o,h,l,c,v=[df[x].astype(float) for x in ('open','high','low','close','volume')]
    ret=np.log(c).diff(); prev=c.shift(1)
    tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    atr=tr.rolling(w).mean(); mean=c.rolling(w).mean(); std=c.rolling(w).std(ddof=0)
    par=np.sqrt((np.log(h/l)**2).rolling(w).mean()/(4*np.log(2)))
    gk=np.sqrt((0.5*np.log(h/l)**2-(2*np.log(2)-1)*np.log(c/o)**2).rolling(w).mean().clip(lower=0))
    rs=np.sqrt((np.log(h/c)*np.log(h/o)+np.log(l/c)*np.log(l/o)).rolling(w).mean().clip(lower=0))
    ema=c.ewm(span=w,adjust=False).mean(); fast=c.ewm(span=12,adjust=False).mean(); slow=c.ewm(span=26,adjust=False).mean()
    macd=fast-slow; hist=macd-macd.ewm(span=9,adjust=False).mean()
    delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/w,adjust=False).mean(); dn=(-delta.clip(upper=0)).ewm(alpha=1/w,adjust=False).mean()
    rsi=100-100/(1+up/dn)
    plus=(h.diff().where((h.diff()>-l.diff())&(h.diff()>0),0.0)); minus=(-l.diff().where((-l.diff()>h.diff())&(-l.diff()>0),0.0))
    plus_di=100*plus.ewm(alpha=1/w,adjust=False).mean()/atr; minus_di=100*minus.ewm(alpha=1/w,adjust=False).mean()/atr
    adx=(100*(plus_di-minus_di).abs()/(plus_di+minus_di)).ewm(alpha=1/w,adjust=False).mean()
    er=(c-c.shift(w)).abs()/c.diff().abs().rolling(w).sum()
    low=l.rolling(w).min(); high=h.rolling(w).max(); stoch=100*(c-low)/(high-low)
    obv=(np.sign(c.diff()).fillna(0)*v).cumsum(); x=np.arange(w); sx=((x-x.mean())**2).sum()
    obv_slope=obv.rolling(w).apply(lambda a: float(np.dot(x-x.mean(),a-a.mean())/sx),raw=True)
    mfm=((c-l)-(h-c))/(h-l).replace(0,np.nan); cmf=(mfm*v).rolling(w).sum()/v.rolling(w).sum()
    tp=(h+l+c)/3; flow=tp*v; pos=flow.where(tp.diff()>0,0).rolling(w).sum(); neg=flow.where(tp.diff()<0,0).rolling(w).sum(); mfi=100-100/(1+pos/neg)
    result={
      'NSE-v1':ret.rolling(w).var(ddof=0).to_numpy(),
      'NSW-v1':_spectral_width(c.to_numpy(),w,use_gpu),
      'Bollinger bandwidth':(4*std/mean).to_numpy(),'Normalized ATR':(atr/c).to_numpy(),
      'Realized volatility':ret.rolling(w).std(ddof=0).to_numpy(),'Parkinson volatility':par.to_numpy(),
      'Garman-Klass volatility':gk.to_numpy(),'Rogers-Satchell volatility':rs.to_numpy(),
      'Donchian width':((high-low)/c).to_numpy(),'Keltner width':(4*atr/ema).to_numpy(),
      'RSI':rsi.to_numpy(),'Normalized MACD histogram':(hist/c).to_numpy(),'ADX':adx.to_numpy(),
      'Kaufman efficiency ratio':er.to_numpy(),'Rate of change':(c/c.shift(w)-1).to_numpy(),
      'Stochastic %K':stoch.to_numpy(),'OBV slope':obv_slope.to_numpy(),'Chaikin money flow':cmf.to_numpy(),
      'Money flow index':mfi.to_numpy(),'Relative volume':(v/v.shift(1).rolling(w).mean()).to_numpy()}
    return result

def expansion_label(df,horizon):
    past_high=df.high.rolling(horizon).max(); past_low=df.low.rolling(horizon).min()
    fh=df.high.shift(-1)[::-1].rolling(horizon).max()[::-1]; fl=df.low.shift(-1)[::-1].rolling(horizon).min()[::-1]
    return ((fh-fl)>=1.25*(past_high-past_low)).astype(float).where(past_high.notna()&fh.notna()).to_numpy()

def ranks(train,x):
    s=np.sort(train[np.isfinite(train)])
    return np.searchsorted(s,x,side='right')/max(1,len(s))
def ap(y,s):
    order=np.argsort(-s); yy=y[order]; p=np.cumsum(yy)/(np.arange(len(yy))+1); return float((p*yy).sum()/max(1,yy.sum()))
def auc(y,s):
    pos=s[y==1]; neg=s[y==0]
    return float(np.mean(pos[:,None]>neg[None,:])+0.5*np.mean(pos[:,None]==neg[None,:])) if len(pos) and len(neg) else np.nan
def calibrate(train_score,train_y,test_score):
    edges=np.quantile(train_score,np.linspace(0,1,11)); edges[0]-=1e-12; edges[-1]+=1e-12
    bi=np.clip(np.digitize(train_score,edges)-1,0,9); bj=np.clip(np.digitize(test_score,edges)-1,0,9)
    base=train_y.mean(); rates=np.array([train_y[bi==k].mean() if np.any(bi==k) else base for k in range(10)])
    return rates[bj]
def metric(y,score,prob):
    top=score>=np.quantile(score,.9); base=y.mean(); pred=prob>=.5
    return {'eligible':int(len(y)),'events':int(y.sum()),'base_rate':float(base),'pr_auc':ap(y,score),'roc_auc':auc(y,score),
            'brier':float(np.mean((prob-y)**2)),'top10_precision':float(y[top].mean()),
            'top10_lift':float(y[top].mean()-base),'false_positive_rate':float(np.mean(pred[y==0])) if np.any(y==0) else None}

def aggregate(raw,rule,count):
    agg=raw.resample(rule,label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
    n=raw.close.resample(rule,label='left',closed='left').count(); return agg[n==count].dropna()

def run(path,use_gpu):
    z=np.load(path,allow_pickle=False); idx=pd.to_datetime(z['timestamp_ns'],utc=True)
    raw=pd.DataFrame({k:z[k] for k in ('open','high','low','close','volume')},index=idx)
    groups={'A: 2017-2018':('2017-08-17 04:00','2018-07-01','2019-01-01'), 'B: 2019':('2019-01-01','2019-07-01','2020-01-01')}
    frames={'15m':(raw,96),'1h':(aggregate(raw,'1h',4),24),'4h':(aggregate(raw,'4h',16),6)}; rows=[]
    for tf,(df,hor) in frames.items():
      caches={w:features(df,w,use_gpu) for w in WINDOWS}; truth=expansion_label(df,hor)
      for group,(start,split,end) in groups.items():
        fit=(df.index>=start)&(df.index<split); test=(df.index>=split)&(df.index<end); fit_idx=np.where(fit)[0]; cut=fit_idx[int(len(fit_idx)*.7)]
        inner=fit & (np.arange(len(df))<cut); val=fit & (np.arange(len(df))>=cut)
        for name in NAMES:
          candidates=[]
          for w in WINDOWS:
            x=caches[w][name]; base=x[inner & np.isfinite(x) & np.isfinite(truth)]
            for direction in ('high','low','two-sided'):
              valid=val&np.isfinite(x)&np.isfinite(truth); r=ranks(base,x[valid]); s={'high':r,'low':1-r,'two-sided':np.abs(r-.5)*2}[direction]
              candidates.append((ap(truth[valid],s),-w,direction,w))
          _,_,direction,w=max(candidates); x=caches[w][name]
          fv=fit&np.isfinite(x)&np.isfinite(truth); tv=test&np.isfinite(x)&np.isfinite(truth); rfit=ranks(x[fv],x[fv]); rtest=ranks(x[fv],x[tv])
          transform=lambda r:{'high':r,'low':1-r,'two-sided':np.abs(r-.5)*2}[direction]
          sf,st=transform(rfit),transform(rtest); prob=calibrate(sf,truth[fv],st); m=metric(truth[tv],st,prob)
          rows.append({'group':group,'timeframe':tf,'indicator':name,'window':w,'direction':direction,**m})
    report={'experiment':'BTC-EXPANSION-20-INDICATOR-PANEL','status':'EXPLORATORY','execution_mode':'RESEARCH_ONLY','live_enabled':False,
            'engine':'cupy-a10g' if use_gpu else 'numpy-cpu','metadata':json.loads(str(z['metadata'])),'results':rows}
    canonical=json.dumps(report,sort_keys=True,separators=(',',':')); report['report_sha256']=hashlib.sha256(canonical.encode()).hexdigest(); return report

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--gpu',action='store_true'); a=p.parse_args()
    report=run(a.input,a.gpu); a.output.write_text(json.dumps(report,indent=2,sort_keys=True)); print(json.dumps({'rows':len(report['results']),'sha256':report['report_sha256'],'engine':report['engine']}))
if __name__=='__main__':main()
