#!/bin/bash
# Chromebook Visualizer - Full Pipeline Script
# This script runs the complete automation pipeline

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo "Chromebook Visualizer Pipeline" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Step 1: Fetch GAM data
echo "[1/4] Fetching GAM data..." | tee -a "$LOG_FILE"
$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/fetch_gam_data.py 2>&1 | tee -a "$LOG_FILE"
echo "✓ GAM data fetched" | tee -a "$LOG_FILE"

# Step 2: Transform CSVs
echo "[2/4] Transforming CSVs..." | tee -a "$LOG_FILE"
$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/transform_csvs.py 2>&1 | tee -a "$LOG_FILE"
echo "✓ CSVs transformed" | tee -a "$LOG_FILE"

# Step 3: Generate PDFs
echo "[3/4] Generating PDFs..." | tee -a "$LOG_FILE"
$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/generate_pdfs.py 2>&1 | tee -a "$LOG_FILE"
echo "✓ PDFs generated" | tee -a "$LOG_FILE"

# Step 4: Upload to SharePoint
echo "[4/4] Uploading to SharePoint..." | tee -a "$LOG_FILE"
$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/upload_to_sharepoint.py 2>&1 | tee -a "$LOG_FILE"
echo "✓ Uploaded to SharePoint" | tee -a "$LOG_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "Pipeline completed successfully!" | tee -a "$LOG_FILE"
echo "Ended: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE"
