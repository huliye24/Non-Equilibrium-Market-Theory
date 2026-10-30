"""Run, publish, and coordinate an exact Stage-C walk-forward shard."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path


def run(command, check=True):
    return subprocess.run(command, check=check, text=True)


def upload(cli, source, bucket, key):
    run([str(cli), "s3", "cp", str(source), f"s3://{bucket}/{key}",
         "--region", "cn-northwest-1", "--only-show-errors"])


def notify(text, key, host, known):
    subprocess.run(["ssh", "-i", str(key), "-o", "BatchMode=yes",
                    "-o", f"UserKnownHostsFile={known}", "-o", "StrictHostKeyChecking=yes", host],
                   input=text, text=True, check=True, timeout=60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--stage-b", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shard", required=True)
    parser.add_argument("--timeframes", nargs="+", required=True)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--aws-cli", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--coordinator", action="store_true")
    parser.add_argument("--wait-for-shard")
    parser.add_argument("--relay-key", type=Path)
    parser.add_argument("--relay-host")
    parser.add_argument("--known-hosts", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    failed, error = False, ""
    try:
        command = [sys.executable, str(Path(__file__).with_name("neb_stage_c_walkforward.py")),
                   "--input", str(args.input), "--stage-b", str(args.stage_b),
                   "--output-dir", str(args.output_dir), "--timeframes", *args.timeframes]
        if args.gpu:
            command.append("--gpu")
        run(command)
    except Exception as exc:
        failed, error = True, f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    marker = {"schema": "neb-stage-c-shard/1.0", "shard": args.shard,
              "status": "FAILED" if failed else "COMPLETE", "timeframes": args.timeframes,
              "error": error, "updated_at": time.time()}
    if not failed:
        summary = json.loads((args.output_dir / "summary.json").read_text())
        if summary.get("status") != "STAGE_C_WALK_FORWARD_COMPLETE" or not summary.get("candidate_evaluations"):
            failed, marker["status"], marker["error"] = True, "FAILED", "completion gate rejected summary"
        else:
            marker["summary"] = summary
            for name in ("summary.json", "stage-c-walk-forward.jsonl", "heartbeat.json"):
                upload(args.aws_cli, args.output_dir / name, args.bucket, f"{args.prefix}/{args.shard}/{name}")
    marker_path = args.output_dir / "shard-marker.json"
    marker_path.write_text(json.dumps(marker, sort_keys=True))
    upload(args.aws_cli, marker_path, args.bucket, f"{args.prefix}/{args.shard}/shard-marker.json")
    if args.coordinator:
        peer_path = args.output_dir / "peer-marker.json"
        deadline = time.time() + 7 * 24 * 3600
        while time.time() < deadline:
            result = subprocess.run([str(args.aws_cli), "s3", "cp",
                                     f"s3://{args.bucket}/{args.prefix}/{args.wait_for_shard}/shard-marker.json",
                                     str(peer_path), "--region", "cn-northwest-1", "--only-show-errors"])
            if result.returncode == 0:
                break
            time.sleep(60)
        if not peer_path.exists():
            failed, error = True, "peer shard timeout"
        else:
            peer = json.loads(peer_path.read_text())
            failed = failed or peer.get("status") != "COMPLETE"
            if not failed:
                mine, other = marker["summary"], peer["summary"]
                evaluated = mine["candidate_evaluations"] + other["candidate_evaluations"]
                folds = mine["fold_results"] + other["fold_results"]
                positive = mine["positive_delta_folds"] + other["positive_delta_folds"]
                text = ("✅ NEB阶段C真实滚动实验完成\n"
                        "GPU分片：BTC 15m；CPU分片：BTC 1h、4h\n"
                        f"18+3+3测试结果：{folds:,}个标签窗口\n"
                        f"真实候选-窗口评估：{evaluated:,}\n"
                        f"NSW样本外PR-AUC增量为正：{positive:,}/{folds:,}\n"
                        "产物和校验摘要已写入S3。历史研究，不构成任何交易许可。")
            else:
                text = f"❌ NEB阶段C真实滚动实验失败\n{error or '至少一个分片失败'}\n未产生任何交易许可。"
        try:
            notify(text, args.relay_key, args.relay_host, args.known_hosts)
        except Exception:
            traceback.print_exc()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
