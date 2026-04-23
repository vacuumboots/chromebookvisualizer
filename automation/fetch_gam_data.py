#!/usr/bin/env python3
"""
Fetch Chromebook and user data via GAM, then transform CSV headers
to match what cb-visual expects.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Locate project root (one level up from this script)
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


def transform_csv(input_path: Path, output_path: Path, header_map: dict):
    """
    Read a CSV, map its headers via header_map (case-insensitive lookup),
    and write the transformed CSV.
    """
    print(f"[XFORM] {input_path} -> {output_path}")
    with open(input_path, "r", newline="", encoding="utf-8") as fin:
        reader = csv.reader(fin)
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError(f"Empty CSV: {input_path}")

        # Build mapping: original header -> target header
        new_headers = []
        for h in raw_headers:
            key = h.strip().lower()
            new_headers.append(header_map.get(key, h))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout)
            writer.writerow(new_headers)
            for row in reader:
                writer.writerow(row)


def main():
    config = load_config()
    out = config["output"]
    gam = config["gam"]
    hmap = config.get("header_map", {})

    # 1. Fetch raw device CSV
    raw_devices = PROJECT_ROOT / out["raw_devices_csv"]
    run_gam(gam["devices_command"], raw_devices)

    # 2. Fetch raw user CSV
    raw_users = PROJECT_ROOT / out["raw_users_csv"]
    run_gam(gam["users_command"], raw_users)

    # 3. Transform headers to match cb-visual expectations
    transformed_devices = PROJECT_ROOT / out["transformed_devices_csv"]
    transform_csv(raw_devices, transformed_devices, hmap.get("devices", {}))

    transformed_users = PROJECT_ROOT / out["transformed_users_csv"]
    transform_csv(raw_users, transformed_users, hmap.get("users", {}))

    print("[DONE] CSV fetch and transform complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
