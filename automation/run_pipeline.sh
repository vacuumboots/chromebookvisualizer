#!/bin/bash
# Chromebook Visualizer - Full Pipeline Script
# This script runs the complete automation pipeline
# Cron: 0 6 * * 1 /home/pi/chromebookvisualizer/automation/run_pipeline.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/pipeline_${TIMESTAMP}.log"

# Notify start (optional — uncomment if you have mail configured)
# echo "Pipeline starting at $(date)" | mail -s "Chromebook Visualizer: START" you@example.com

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

# Step 2: Generate PDFs
echo "[2/3] Generating PDFs..." | tee -a "$LOG_FILE"
if $SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/generate_pdfs.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "✓ PDFs generated" | tee -a "$LOG_FILE"
else
    echo "✗ PDF generation FAILED" | tee -a "$LOG_FILE"
    exit 1
fi

# Step 3: Upload to SharePoint
echo "[3/3] Uploading to SharePoint..." | tee -a "$LOG_FILE"
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

# Notify completion (optional)
# echo "Pipeline completed successfully at $(date)" | mail -s "Chromebook Visualizer: OK" you@example.com

exit 0
