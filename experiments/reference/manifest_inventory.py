"""Read-only inventory of immutable BTC 15m manifests."""

from __future__ import annotations

import argparse
import json

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="market-data/v2/manifests/")
    args = parser.parse_args()
    client = boto3.client("s3", region_name="cn-northwest-1")
    rows = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=args.bucket, Prefix=args.prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if not key.endswith("manifest.json"):
                continue
            manifest = json.loads(client.get_object(Bucket=args.bucket, Key=key)["Body"].read())
            objects = [
                value for value in manifest.get("objects", [])
                if value.get("timeframe") == "15m" and "symbol=btcusdt" in value.get("key", "").lower()
            ]
            if not objects:
                continue
            first = min(value["first_at"] for value in objects)
            last = max(value["last_at"] for value in objects)
            rows.append({"snapshot_id": manifest.get("snapshot_id"), "manifest_key": key,
                         "first_at": first, "last_at": last, "objects": len(objects)})
    print(json.dumps(sorted(rows, key=lambda value: value["last_at"]), indent=2))


if __name__ == "__main__":
    main()
