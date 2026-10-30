"""Run one NEB shard, publish immutable artifacts to S3, and coordinate notice."""
from __future__ import annotations
import argparse, json, subprocess, sys, time, traceback
from pathlib import Path

def run(command,check=True): return subprocess.run(command,check=check,text=True,capture_output=False)
def aws(cli,*args,check=True): return run([str(cli),*args,'--region','cn-northwest-1'],check)
def upload(cli,source,bucket,key): aws(cli,'s3','cp',str(source),f's3://{bucket}/{key}','--only-show-errors')
def notify(text,key,host,known):
    subprocess.run(['ssh','-i',str(key),'-o','BatchMode=yes','-o',f'UserKnownHostsFile={known}',
                    '-o','StrictHostKeyChecking=yes',host],input=text,text=True,check=True,timeout=60)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--shard',required=True); p.add_argument('--timeframes',nargs='+',required=True); p.add_argument('--gpu',action='store_true')
    p.add_argument('--aws-cli',type=Path,required=True); p.add_argument('--bucket',required=True); p.add_argument('--prefix',required=True)
    p.add_argument('--coordinator',action='store_true'); p.add_argument('--wait-for-shard'); p.add_argument('--relay-key',type=Path)
    p.add_argument('--relay-host'); p.add_argument('--known-hosts',type=Path); a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    engine=Path(__file__).with_name('neb_gpu_campaign.py'); failed=False; error=''
    try:
        cmd=[sys.executable,str(engine),'--input',str(a.input),'--output-dir',str(a.output_dir),'--timeframes',*a.timeframes]
        if a.gpu: cmd.append('--gpu')
        run(cmd)
    except Exception as exc:
        failed=True; error=f'{type(exc).__name__}: {exc}'; traceback.print_exc()
    marker={'shard':a.shard,'status':'FAILED' if failed else 'COMPLETE','timeframes':a.timeframes,'error':error,'updated_at':time.time()}
    if not failed:
        summary=json.loads((a.output_dir/'summary.json').read_text()); marker['summary']=summary
        for name in ('summary.json','stage-a-checkpoint.csv.gz','stage-b-stable-top10.csv.gz','stage-c-grid.json','heartbeat.json'):
            upload(a.aws_cli,a.output_dir/name,a.bucket,f'{a.prefix}/{a.shard}/{name}')
    marker_path=a.output_dir/'shard-marker.json'; marker_path.write_text(json.dumps(marker,sort_keys=True)); upload(a.aws_cli,marker_path,a.bucket,f'{a.prefix}/{a.shard}/shard-marker.json')
    if a.coordinator:
        peer=a.output_dir/'peer-marker.json'; deadline=time.time()+7*24*3600
        while time.time()<deadline:
            result=subprocess.run([str(a.aws_cli),'s3','cp',f's3://{a.bucket}/{a.prefix}/{a.wait_for_shard}/shard-marker.json',str(peer),'--region','cn-northwest-1','--only-show-errors'])
            if result.returncode==0: break
            time.sleep(60)
        if not peer.exists(): failed=True; error='peer shard timeout'
        else:
            other=json.loads(peer.read_text()); failed=failed or other.get('status')!='COMPLETE'
            if not failed:
                mine=marker['summary']; theirs=other['summary']; total=mine['stage_a_evaluations']+theirs['stage_a_evaluations']
                text=(f"✅ NEB双服务器百万网格实验完成\nGPU分片：15m\nMATLAB/CPU分片：1h、4h\n"
                      f"阶段A总评估：{total:,}\n阶段B稳定候选：{mine['stage_b_rows']+theirs['stage_b_rows']:,}\n"
                      f"阶段C候选：{mine['stage_c_candidates']+theirs['stage_c_candidates']:,}\n"
                      "结果已写入S3。历史研究，不构成PAPER/TESTNET/LIVE许可。")
            else: text=f'❌ NEB双服务器实验失败\n{error or "至少一个分片失败"}\n未产生任何交易许可。'
        try: notify(text,a.relay_key,a.relay_host,a.known_hosts)
        except Exception: traceback.print_exc()
    if failed: raise SystemExit(1)
if __name__=='__main__': main()
