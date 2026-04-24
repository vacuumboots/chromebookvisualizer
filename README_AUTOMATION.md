# Chromebook Visualizer - Automation Setup

## Overview
This automation runs the complete Chromebook Visualizer pipeline on a Raspberry Pi:
1. Fetches device and user data from Google Workspace via GAM
2. Transforms CSVs to match the visualizer format
3. Generates PDF reports for each school
4. Uploads PDFs to SharePoint

## Schedule
- **Runs**: Every Monday at 6:00 AM
- **Cron job**: `0 6 * * 1 /home/pi/chromebookvisualizer/automation/run_pipeline.sh`

## File Locations
- **Project**: `/home/pi/chromebookvisualizer/`
- **Scripts**: `/home/pi/chromebookvisualizer/automation/`
- **Data**: `/home/pi/chromebookvisualizer/data/`
- **PDFs**: `/home/pi/chromebookvisualizer/data/pdfs/`
- **Logs**: `/home/pi/chromebookvisualizer/logs/`

## Scripts
- `run_pipeline.sh` - Main wrapper script (runs all steps)
- `fetch_gam_data.py` - Fetches GAM data
- `transform_csvs.py` - Transforms CSVs
- `generate_pdfs.py` - Generates PDFs
- `upload_to_sharepoint.py` - Uploads to SharePoint

## Manual Run
To run the pipeline manually:
```bash
/home/pi/chromebookvisualizer/automation/run_pipeline.sh
```

## View Logs
```bash
# View latest log
tail -f /home/pi/chromebookvisualizer/logs/pipeline_*.log

# View cron log
tail -f /home/pi/chromebookvisualizer/logs/cron.log
```

## PDF Naming Convention
PDFs are named with the date: `{School}_chromebook_report_{YYYY-MM-DD}.pdf`

Example: `FCHS_chromebook_report_2025-04-24.pdf`

## SharePoint Location
PDFs are uploaded to: `https://fsd365.sharepoint.com/TechnologyServices/chromebook%20reports/`

## Troubleshooting
1. Check logs in `/home/pi/chromebookvisualizer/logs/`
2. Verify GAM credentials are valid
3. Ensure network connectivity to Google Workspace and SharePoint
4. Check disk space: `df -h`

## Cron Job Management
```bash
# View cron job
crontab -l

# Edit cron job
crontab -e

# Remove cron job
crontab -r
```
