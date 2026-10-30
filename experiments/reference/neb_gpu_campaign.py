"""Resumable multi-million NEB grid campaign for one immutable BTC snapshot.

Research-only: no private exchange API, order, position, or execution imports.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time
from pathlib import Path
import numpy as np
import pandas as pd

NS=(8,12,16,24,32,48,64,96,128,192,256); MS=(64,96,128,192,256,384,512,768,1024)
QL=(.05,.10,.15,.20,.25,.30); QT=(.35,.40,.45,.50,.55,.60)
KS=(4,8,12,16,24,32,48); SLOPES=(1,2,3,4,6,8,12,16); RHOS=(1.15,1.25,1.50,2.00)
TFS={'15m':('15min',1,96),'1h':('1h',4,24),'4h':('4h',16,6)}

def atomic_write(path,payload):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(payload,sort_keys=True)); tmp.replace(path)
def aggregate(raw,rule,count):
    x=raw.resample(rule,label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
    n=raw.close.resample(rule,label='left',closed='left').count(); return x[n==count].dropna()
def months(ts,n): return ts+pd.DateOffset(months=n)
def folds(index):
    out=[]; start=pd.Timestamp('2017-09-01',tz='UTC'); end=index.max()
    while months(start,24)<=end:
        a,b,c,d=start,months(start,18),months(start,21),months(start,24)
        out.append(((index>=a)&(index<b),(index>=b)&(index<c),(index>=c)&(index<d)))
        start=months(start,3)
    return out
def labels(df,h,rho):
    ph=df.high.rolling(h).max(); pl=df.low.rolling(h).min()
    fh=df.high.shift(-1)[::-1].rolling(h).max()[::-1]; fl=df.low.shift(-1)[::-1].rolling(h).min()[::-1]
    return (((fh-fl)>=rho*(ph-pl)).astype(float).where(ph.notna()&fh.notna())).to_numpy()
def energy_z(close,n,m):
    r=np.log(close).diff(); e=r.rolling(n).var(ddof=0); x=np.log(e+1e-12)
    med=x.rolling(m).median(); mad=(x-med).abs().rolling(m).median()
    return ((x-med)/(1.4826*mad).clip(lower=1e-12)).to_numpy(dtype=np.float32)
def ap_binary(tp,fp,pos):
    precision=tp/np.maximum(1,tp+fp); recall=tp/np.maximum(1,pos)
    base=(pos-tp)/np.maximum(1,(pos-tp)+(0))
    return precision*recall + (1-recall)*0.0

def stage_a(df,tf,h,use_gpu,heartbeat,max_blocks=0):
    xp=np
    if use_gpu:
        import cupy as cp; xp=cp
    fs=folds(df.index); truths={rho:labels(df,h,rho) for rho in RHOS}; rows=[]; blocks=0
    total_blocks=len(NS)*len(MS)*len(KS)*len(SLOPES)
    for n in NS:
      for m in MS:
        z=energy_z(df.close,n,m)
        mins={k:pd.Series(z).shift(1).rolling(k).min().to_numpy(dtype=np.float32) for k in KS}
        for k in KS:
          lowbase=mins[k]
          for slope_k in SLOPES:
            slope=(z-np.roll(z,slope_k))/slope_k; slope[:slope_k]=np.nan
            acc={rho:{'tp':np.zeros(36,np.int64),'fp':np.zeros(36,np.int64),'fn':np.zeros(36,np.int64),'tests':0} for rho in RHOS}
            for train,select,_test in fs:
              train_valid=train&np.isfinite(z); sel=select&np.isfinite(z)&np.isfinite(lowbase)&np.isfinite(slope)
              if train_valid.sum()<100 or sel.sum()<30: continue
              lows=np.quantile(z[train_valid],QL); triggers=np.quantile(z[train_valid],QT)
              zz=xp.asarray(z[sel]); ll=xp.asarray(lowbase[sel]); ss=xp.asarray(slope[sel])
              lo=xp.asarray(np.repeat(lows,len(QT)))[:,None]; tr=xp.asarray(np.tile(triggers,len(QL)))[:,None]
              signal=(ll[None,:]<=lo)&(zz[None,:]>=tr)&(ss[None,:]>0)
              for rho in RHOS:
                y=truths[rho][sel]; valid=np.isfinite(y); yy=xp.asarray(y[valid]>0.5); sg=signal[:,valid]
                tp=xp.sum(sg&yy[None,:],axis=1); fp=xp.sum(sg&~yy[None,:],axis=1); pos=xp.sum(yy)
                tp=xp.asnumpy(tp) if use_gpu else tp; fp=xp.asnumpy(fp) if use_gpu else fp; pos=int(pos.get()) if use_gpu else int(pos)
                acc[rho]['tp']+=tp.astype(np.int64); acc[rho]['fp']+=fp.astype(np.int64); acc[rho]['fn']+=pos-tp.astype(np.int64); acc[rho]['tests']+=int(valid.sum())
            for rho in RHOS:
              a=acc[rho]; tp,fp,fn=a['tp'],a['fp'],a['fn']; prec=tp/np.maximum(1,tp+fp); rec=tp/np.maximum(1,tp+fn)
              f1=2*prec*rec/np.maximum(1e-12,prec+rec); base=(tp+fn)/max(1,a['tests']); lift=prec-base
              objective=0.45*lift+0.35*f1+0.20*rec-(tp+fp<30)*1.0
              for idx,(ql,qt) in enumerate((x,y) for x in QL for y in QT):
                rows.append((tf,rho,n,m,ql,qt,k,slope_k,int(tp[idx]),int(fp[idx]),int(fn[idx]),float(prec[idx]),float(rec[idx]),float(f1[idx]),float(lift[idx]),float(objective[idx])))
            blocks+=1
            if blocks%25==0:
                atomic_write(heartbeat,{'stage':'A','timeframe':tf,'blocks':blocks,'total_blocks':total_blocks,'evaluations':len(rows),'updated_at':time.time()})
            if max_blocks and blocks>=max_blocks:
                return rows
    return rows

def stabilize(rows):
    cols=['timeframe','rho','n','m','ql','qt','k','slope_k','tp','fp','fn','precision','recall','f1','lift','objective']
    frame=pd.DataFrame(rows,columns=cols); kept=[]
    for (_tf,_rho),g in frame.groupby(['timeframe','rho']):
        cutoff=g.objective.quantile(.90); top=g[g.objective>=cutoff].copy()
        med=top.groupby(['n','m']).objective.transform('median'); std=top.groupby(['n','m']).objective.transform('std').fillna(0)
        top['stability']=med-.5*std; top['stable_objective']=top.objective+.25*top.stability; kept.append(top)
    return pd.concat(kept,ignore_index=True).sort_values('stable_objective',ascending=False)

def stage_c(stable):
    # NSW incremental grid is registered here and materialized for the next exact scorer.
    windows=(32,48,64,96,128,192,256); baselines=(128,256,512,1024); weights=(0,.05,.10,.15,.20,.30,.40,.50)
    seeds=stable.groupby(['timeframe','rho']).head(100)
    out=[]
    for _,r in seeds.iterrows():
      for nw in windows:
       for bm in baselines:
        for method in ('variance_bandwidth','spectral_entropy','low_frequency_concentration'):
         for window_fn in ('hann','rectangular'):
          for weight in weights:
           out.append({'timeframe':r.timeframe,'rho':r.rho,'neb_n':int(r.n),'neb_m':int(r.m),'neb_ql':r.ql,'neb_qt':r.qt,
                       'neb_k':int(r.k),'neb_slope_k':int(r.slope_k),'neb_stability':r.stability,'nsw_window':nw,
                       'nsw_baseline':bm,'spectral_method':method,'window_function':window_fn,'nsw_weight':weight})
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output-dir',type=Path,required=True); p.add_argument('--gpu',action='store_true'); p.add_argument('--max-blocks',type=int,default=0); p.add_argument('--timeframes',nargs='+',choices=tuple(TFS),default=list(TFS)); a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True); heartbeat=a.output_dir/'heartbeat.json'; z=np.load(a.input,allow_pickle=False)
    raw=pd.DataFrame({k:z[k] for k in ('open','high','low','close','volume')},index=pd.to_datetime(z['timestamp_ns'],utc=True))
    all_rows=[]
    for tf in a.timeframes:
        rule,count,h=TFS[tf]
        df=raw if count==1 else aggregate(raw,rule,count); all_rows.extend(stage_a(df,tf,h,a.gpu,heartbeat,a.max_blocks))
        pd.DataFrame(all_rows).to_csv(a.output_dir/'stage-a-checkpoint.csv.gz',index=False,compression='gzip')
    stable=stabilize(all_rows); stable.to_csv(a.output_dir/'stage-b-stable-top10.csv.gz',index=False,compression='gzip')
    c=stage_c(stable); (a.output_dir/'stage-c-grid.json').write_text(json.dumps(c,separators=(',',':')))
    summary={'schema':'neb-million-grid/1.0','status':'STAGE_A_B_COMPLETE_STAGE_C_GRID_MATERIALIZED','execution_mode':'RESEARCH_ONLY','live_enabled':False,
             'snapshot':json.loads(str(z['metadata']))['snapshot_id'],'source_rows':len(raw),'stage_a_evaluations':len(all_rows),
             'stage_b_rows':len(stable),'stage_c_candidates':len(c),'best':stable.head(30).to_dict('records')}
    canonical=json.dumps(summary,sort_keys=True,separators=(',',':')); summary['sha256']=hashlib.sha256(canonical.encode()).hexdigest()
    atomic_write(a.output_dir/'summary.json',summary); atomic_write(heartbeat,{'stage':'COMPLETE','updated_at':time.time(),**{k:summary[k] for k in ('stage_a_evaluations','stage_b_rows','stage_c_candidates','sha256')}})
    print(json.dumps({k:summary[k] for k in ('status','stage_a_evaluations','stage_b_rows','stage_c_candidates','sha256')}))
if __name__=='__main__': main()
