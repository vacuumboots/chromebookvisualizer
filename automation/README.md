# cb-visual Raspberry Pi Automation

Automated pipeline that runs on a Raspberry Pi (or any Linux host):

1. **Exports** Chromebook device and user CSVs via GAM.
2. **Transforms** GAM CSV headers to match `cb-visual` expectations.
3. **Generates** one PDF per school using a headless browser (Playwright).
4. **Copies** PDFs to a Windows file share (or any mounted directory).

---

## Prerequisites

### 1. GAM (Google Apps Manager)
Install and authorize GAM with a service account:

```bash
# Follow https://github.com/GAM-team/GAM/wiki
# Verify it works:
gam info domain
```

### 2. Python dependencies

```bash
cd automation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

> **Raspberry Pi note:** If `playwright install chromium` fails on ARM, install the system Chromium package and point Playwright to it:
> ```bash
> sudo apt update && sudo apt install chromium-browser
> export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser
> ```

### 3. Create your local config

Copy the example and edit it for your org (all scripts read `config.json`; the example stays clean for GitHub):

```bash
cp automation/config.example.json automation/config.json
```

### 4. Mount the destination file share (optional)

If you want PDFs copied automatically to a Windows/SMB share:

```bash
sudo mkdir -p /mnt/sharepoint-drop
sudo mount -t cifs //your-server/share /mnt/sharepoint-drop \
  -o username=YOUR_USER,uid=$(id -u),gid=$(id -g)
```

Add the mount to `/etc/fstab` if you want it persistent.

---

## Configuration

Edit `automation/config.json`:

| Section | What to change |
|---|---|
| `gam.devices_command` | GAM command for your Chromebook export. Default uses `gam print cros`. |
| `gam.users_command` | GAM command for your user export. Default uses `gam print users`. |
| `visualizer` | Same settings you use in the web UI: `ou_prefix`, `grouping_depth`, excluded patterns, ratio thresholds. |
| `output.network_share_dir` | Where finished PDFs are copied. Leave as-is if you want to copy manually. |
| `header_map` | Maps GAM column names to the names `cb-visual` expects. Adjust if your GAM version uses different headers. |

---

## Run manually

```bash
cd /path/to/chromebookvisualizer
source automation/venv/bin/activate
python3 automation/run.py
```

PDFs appear in `data/pdfs/` and are copied to your network share if mounted.

---

## Schedule with cron

```bash
crontab -e
```

Add a line for a weekly Monday-morning run at 06:00:

```cron
0 6 * * 1 cd /path/to/chromebookvisualizer && /path/to/chromebookvisualizer/automation/venv/bin/python /path/to/chromebookvisualizer/automation/run.py >> /tmp/cb-visual.log 2>&1
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `gam: command not found` | Add GAM to your `$PATH` or use the full path to the `gam` binary in `config.json`. |
| Playwright fails to launch Chromium on Pi | Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser` before running. |
| No schools found in PDFs | Check `data/devices.csv` and `data/users.csv` manually. Verify `ou_prefix` in `config.json`. |
| PDFs look wrong / missing charts | Increase `pdf.wait_ms_after_load` in `config.json` (slower Pi = longer render time). |
| Network share copy skipped | Ensure the share is mounted before the script runs. |
