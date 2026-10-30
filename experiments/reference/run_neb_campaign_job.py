"""Run the frozen NEB campaign and notify through the existing HK relay."""
from __future__ import annotations
import argparse, json, subprocess, sys, traceback
from pathlib import Path

def notify(text,key,host,known):
    subprocess.run(['ssh','-i',str(key),'-o','BatchMode=yes','-o',f'UserKnownHostsFile={known}',
                    '-o','StrictHostKeyChecking=yes',host],input=text,text=True,check=True,timeout=60)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--relay-key',type=Path,required=True); p.add_argument('--relay-host',required=True); p.add_argument('--known-hosts',type=Path,required=True); a=p.parse_args()
    engine=Path(__file__).with_name('neb_gpu_campaign.py'); failed=False
    try:
        subprocess.run([sys.executable,str(engine),'--input',str(a.input),'--output-dir',str(a.output_dir),'--gpu'],check=True)
    except Exception:
        failed=True; traceback.print_exc()
    if failed:
        text='❌ NEB百万网格GPU实验失败\n请检查GPU任务日志和检查点。未产生任何交易许可。'
    else:
        s=json.loads((a.output_dir/'summary.json').read_text())
        text=(f"✅ NEB百万网格GPU实验完成\n阶段A评估：{s['stage_a_evaluations']:,}\n"
              f"阶段B稳定候选：{s['stage_b_rows']:,}\n阶段C增量候选网格：{s['stage_c_candidates']:,}\n"
              f"结果SHA256：{s['sha256']}\n历史研究，不构成PAPER/TESTNET/LIVE许可。")
    try: notify(text,a.relay_key,a.relay_host,a.known_hosts)
    except Exception: traceback.print_exc()
    if failed: raise SystemExit(1)
if __name__=='__main__': main()
