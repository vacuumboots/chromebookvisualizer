#!/bin/bash
# Chromebook Visualizer - Full Pipeline Script
# Cron: 0 6 * * 1 /home/pi/chromebookvisualizer/automation/run_pipeline.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/pipeline_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

echo "==========================================" | tee -a "$LOG_FILE"
echo "Chromebook Visualizer Pipeline" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Step 1: Fetch GAM data (includes CSV transform)
echo "[1/3] Fetching and transforming GAM data..." | tee -a "$LOG_FILE"
if $SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/fetch_gam_data.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "✓ GAM data fetched and transformed" | tee -a "$LOG_FILE"
else
    echo "✗ GAM fetch/transform FAILED" | tee -a "$LOG_FILE"
    exit 1
fi

# Prepare frontend config for HTTP server
echo "[2/3] Preparing frontend config..." | tee -a "$LOG_FILE"
mkdir -p "$PROJECT_DIR/data"
cp "$SCRIPT_DIR/config.json" "$PROJECT_DIR/data/config.json"
echo "✓ Config copied to data/config.json" | tee -a "$LOG_FILE"

# Step 3: Generate PDFs
echo "[3/3] Generating PDFs..." | tee -a "$LOG_FILE"
if $SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/generate_pdfs.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "✓ PDFs generated" | tee -a "$LOG_FILE"
else
    echo "✗ PDF generation FAILED" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 4: Upload to SharePoint
echo "[4/4] Uploading to SharePoint..." | tee -a "$LOG_FILE"
if $SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/upload_to_sharepoint.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "✓ Uploaded to SharePoint" | tee -a "$LOG_FILE"
else
    echo "✗ SharePoint upload FAILED" | tee -a "$LOG_FILE"
    exit 1
fi

echo "==========================================" | tee -a "$LOG_FILE"
echo "Pipeline completed successfully!" | tee -a "$LOG_FILE"
echo "Ended: $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE"

exit 0
