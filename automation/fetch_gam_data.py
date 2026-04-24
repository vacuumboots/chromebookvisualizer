#!/usr/bin/env python3
"""
Fetch Chromebook and user data via GAM, then transform CSV headers
and values to match what cb-visual expects.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def run_gam(command: str, output_path: Path):
    """Run a GAM command and capture stdout to a file."""
    print(f"[GAM] Running: {command}")
    print(f"[GAM] Output -> {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            result = subprocess.run(
                command,
                shell=True,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
        if result.stderr:
            print(f"[GAM] stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"[GAM] FAILED with exit code {e.returncode}")
        print(f"[GAM] stderr: {e.stderr}")
        raise


def transform_devices_csv(input_path: Path, output_path: Path, header_map: dict):
    """Read GAM device CSV, map headers, synthesize diskSpaceUsageByte, write transformed."""
    print(f"[XFORM] {input_path} -> {output_path}")
    with open(input_path, "r", newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise ValueError(f"Empty CSV: {input_path}")

        fields_lower = {f.lower(): f for f in reader.fieldnames}

        # GAM7 may emit diskSpaceUsage.capacityBytes and .usedBytes
        cap_key = "diskspaceusage.capacitybytes"
        used_key = "diskspaceusage.usedbytes"
        has_cap = cap_key in fields_lower
        has_used = used_key in fields_lower

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fout:
            out_fields = []
            for f in reader.fieldnames:
                key = f.lower()
                if key in (cap_key, used_key, "diskspaceusage"):
                    continue  # skip raw disk-space columns; we synthesize below
                target = header_map.get(key, f)
                out_fields.append(target)
            if has_cap and has_used:
                out_fields.append("diskSpaceUsageByte")

            writer = csv.DictWriter(fout, fieldnames=out_fields)
            writer.writeheader()

            for row in reader:
                out_row = {}
                for f in reader.fieldnames:
                    key = f.lower()
                    if key in (cap_key, used_key, "diskspaceusage"):
                        continue
                    target = header_map.get(key, f)
                    out_row[target] = row.get(f, "")
                if has_cap and has_used:
                    cap = row.get(fields_lower.get(cap_key, cap_key), "")
                    used = row.get(fields_lower.get(used_key, used_key), "")
                    if cap and used:
                        out_row["diskSpaceUsageByte"] = f"{used} / {cap}"
                    else:
                        out_row["diskSpaceUsageByte"] = ""
                writer.writerow(out_row)


def transform_users_csv(input_path: Path, output_path: Path, header_map: dict):
    """Read GAM user CSV, map headers, convert suspended TRUE/FALSE -> Status [READ ONLY]."""
    print(f"[XFORM] {input_path} -> {output_path}")
    with open(input_path, "r", newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise ValueError(f"Empty CSV: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fout:
            out_fields = []
            for f in reader.fieldnames:
                key = f.lower()
                target = header_map.get(key, f)
                out_fields.append(target)

            writer = csv.DictWriter(fout, fieldnames=out_fields)
            writer.writeheader()

            for row in reader:
                out_row = {}
                for f in reader.fieldnames:
                    key = f.lower()
                    target = header_map.get(key, f)
                    val = row.get(f, "")
                    if target == "Status [READ ONLY]":
                        val = val.strip().upper()
                        if val == "TRUE":
                            val = "Suspended"
                        else:
                            val = "Active"
                    out_row[target] = val
                writer.writerow(out_row)


def main():
    config = load_config()
    out = config["output"]
    gam = config["gam"]
    hmap = config.get("header_map", {})

    raw_devices = PROJECT_ROOT / out["raw_devices_csv"]
    run_gam(gam["devices_command"], raw_devices)

    raw_users = PROJECT_ROOT / out["raw_users_csv"]
    run_gam(gam["users_command"], raw_users)

    transformed_devices = PROJECT_ROOT / out["transformed_devices_csv"]
    transform_devices_csv(raw_devices, transformed_devices, hmap.get("devices", {}))

    transformed_users = PROJECT_ROOT / out["transformed_users_csv"]
    transform_users_csv(raw_users, transformed_users, hmap.get("users", {}))

    print("[DONE] CSV fetch and transform complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
