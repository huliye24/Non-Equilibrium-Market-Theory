"""Compare independent Python and MATLAB NSW phase-A golden reports."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


FIELDS = ("nse_v1", "nscen_v1", "nsw_v1", "parseval_error")


def _observations(value: Any, prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    result = []
    for name, item in value.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(item, list):
            result.extend((f"{path}[{index}]", row) for index, row in enumerate(item))
        else:
            result.append((path, item))
    return result


def compare(python_report: dict[str, Any], matlab_report: dict[str, Any],
            tolerance: float = 1e-11) -> dict[str, Any]:
    python_rows = dict(_observations(python_report["observations"]))
    matlab_rows = dict(_observations(matlab_report["observations"]))
    if python_rows.keys() != matlab_rows.keys():
        raise ValueError("Python and MATLAB observation sets differ")
    differences = []
    for name in python_rows:
        for field in FIELDS:
            left, right = python_rows[name][field], matlab_rows[name][field]
            if left is None and (right is None or (isinstance(right, float) and math.isnan(right))):
                difference = 0.0
            elif right is None and (left is None or (isinstance(left, float) and math.isnan(left))):
                difference = 0.0
            else:
                difference = abs(float(left) - float(right))
            differences.append({"observation": name, "field": field, "absolute_difference": difference})
    maximum = max(item["absolute_difference"] for item in differences)
    return {"status": "PASS" if maximum <= tolerance else "FAIL",
            "tolerance": tolerance, "maximum_absolute_difference": maximum,
            "differences": differences}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("python_report", type=Path)
    parser.add_argument("matlab_report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(json.loads(args.python_report.read_text()),
                     json.loads(args.matlab_report.read_text()))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "tolerance", "maximum_absolute_difference")}))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

