#!/usr/bin/env python3
"""
Orchestration script for the cb-visual Raspberry Pi automation pipeline.

Steps:
  1. fetch_gam_data.py  – export devices & users via GAM, transform CSV headers
  2. generate_pdfs.py   – headless browser prints one PDF per school
  3. (optional) copy PDFs to a network share / mounted directory

Run this from a cron job for fully scheduled reports.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def run_step(name, script_name):
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    script = SCRIPT_DIR / script_name
    result = subprocess.run([sys.executable, str(script)], cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"[FAIL] {name} exited with code {result.returncode}")
        return False
    print(f"[OK]   {name} complete")
    return True


def copy_to_network_share(config):
    out_cfg = config["output"]
    pdf_dir = PROJECT_ROOT / out_cfg["pdf_output_dir"]
    share_dir = Path(out_cfg.get("network_share_dir", "/mnt/sharepoint-drop"))

    if not share_dir.exists():
        print(f"[SHARE] Network share not mounted or missing: {share_dir}")
        print("[SHARE] Skipping copy. You can mount it with:")
        print(f"        sudo mount -t cifs //server/share {share_dir} -o username=...")
        return False

    share_dir.mkdir(parents=True, exist_ok=True)

    # Optional: create a dated subfolder
    today = datetime.now().strftime("%Y-%m-%d")
    dated_dir = share_dir / today
    dated_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        dest = dated_dir / pdf.name
        shutil.copy2(pdf, dest)
        copied += 1
        print(f"[SHARE] Copied {pdf.name} -> {dest}")

    print(f"[SHARE] {copied} PDF(s) copied to {dated_dir}")
    return True


def main():
    config = load_config()

    success = True
    success = run_step("Fetch GAM data", "fetch_gam_data.py") and success
    success = run_step("Generate PDFs", "generate_pdfs.py") and success

    if success:
        copy_to_network_share(config)
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("PIPELINE FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
