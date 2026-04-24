#!/usr/bin/env python3
"""
Orchestrator for the Chromebook Visualizer automation pipeline.

Runs the full end-to-end workflow:
1. Fetch and transform data from GAM7
2. Generate PDFs for each school
3. Upload all PDFs to SharePoint
"""
import json
import os
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def run_command(cmd, cwd=None, env=None):
    """Run a command and return True if successful, False otherwise."""
    print(f"[RUN] Executing: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd or SCRIPT_DIR,
        env=env or os.environ.copy(),
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main():
    config = load_config()
    out_cfg = config["output"]

    pdf_output_dir = PROJECT_ROOT / out_cfg["pdf_output_dir"]

    print("=" * 60)
    print("Chromebook Visualizer Automation Pipeline")
    print("=" * 60)

    # Step 1: Fetch and transform GAM data
    print("\n[STEP 1/3] Fetching and transforming GAM data...")
    fetch_script = SCRIPT_DIR / "fetch_gam_data.py"
    if not run_command([sys.executable, str(fetch_script)]):
        print("[ERROR] Failed to fetch GAM data")
        return 1
    print("[OK] GAM data fetched and transformed")

    # Step 2: Generate PDFs
    print("\n[STEP 2/3] Generating PDFs for each school...")
    pdf_script = SCRIPT_DIR / "generate_pdfs.py"
    if not run_command([sys.executable, str(pdf_script)]):
        print("[ERROR] Failed to generate PDFs")
        return 1
    print("[OK] PDFs generated")

    # Step 3: Upload to SharePoint
    print("\n[STEP 3/3] Uploading PDFs to SharePoint...")
    upload_script = SCRIPT_DIR / "upload_to_sharepoint.py"
    if not upload_script.exists():
        print(f"[ERROR] Upload script not found: {upload_script}")
        return 1

    pdf_files = sorted(pdf_output_dir.glob("*.pdf"))
    if not pdf_files:
        print("[ERROR] No PDFs found to upload")
        return 1

    print(f"[INFO] Found {len(pdf_files)} PDF(s) to upload")
    success_count = 0
    for pdf_path in pdf_files:
        if run_command([sys.executable, str(upload_script), str(pdf_path)]):
            success_count += 1
        else:
            print(f"[WARN] Failed to upload: {pdf_path.name}")

    print(f"\n[OK] Uploaded {success_count}/{len(pdf_files)} PDF(s) to SharePoint")

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)

    return 0 if success_count == len(pdf_files) else 1


if __name__ == "__main__":
    sys.exit(main())
