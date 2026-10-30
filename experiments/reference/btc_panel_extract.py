"""Hash-verified extraction of a fixed BTCUSDT 15m S3 manifest to NPZ."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import boto3
import numpy as np
import pyarrow.parquet as pq


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bucket", required=True)
    p.add_argument("--manifest-key", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start", default="2017-08-17")
    p.add_argument("--end", default="2027-01-01")
    args = p.parse_args()
    s3 = boto3.client("s3", region_name="cn-northwest-1")
    raw = s3.get_object(Bucket=args.bucket, Key=args.manifest_key)["Body"].read()
    manifest = json.loads(raw)
    rows, used = [], []
    for item in manifest["objects"]:
        key = item.get("key", "")
        if item.get("timeframe") != "15m" or "symbol=btcusdt" not in key.lower():
            continue
        if item["last_at"] < args.start or item["first_at"] >= args.end:
            continue
        payload = s3.get_object(Bucket=args.bucket, Key=key)["Body"].read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"hash mismatch: {key}")
        for row in pq.read_table(io.BytesIO(payload)).to_pylist():
            ts = row.get("open_time") or row.get("timestamp")
            if hasattr(ts, "timestamp"):
                ts_ns = int(ts.timestamp() * 1_000_000_000)
            else:
                ts_ns = np.datetime64(str(ts)).astype("datetime64[ns]").astype(np.int64)
            if row.get("is_closed", True) and not row.get("is_imputed", False):
                volume = row.get("base_volume", row.get("volume", np.nan))
                rows.append((ts_ns, row["open"], row["high"], row["low"], row["close"], volume))
        used.append({"key": key, "sha256": digest})
    rows.sort(key=lambda x: x[0])
    timestamp_ns = np.asarray([row[0] for row in rows], dtype=np.int64)
    values = np.asarray([row[1:] for row in rows], dtype=np.float64)
    if len(np.unique(timestamp_ns)) != len(timestamp_ns):
        raise ValueError("duplicate timestamps")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = json.dumps({"snapshot_id": manifest["snapshot_id"], "manifest_key": args.manifest_key,
                           "objects": used}, sort_keys=True)
    np.savez_compressed(args.output, timestamp_ns=timestamp_ns, open=values[:, 0],
                        high=values[:, 1], low=values[:, 2], close=values[:, 3], volume=values[:, 4],
                        metadata=np.asarray(metadata))
    print(json.dumps({"rows": len(values), "objects": len(used), "snapshot_id": manifest["snapshot_id"]}))


if __name__ == "__main__":
    main()
