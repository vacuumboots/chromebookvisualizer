#!/usr/bin/env python3
"""
Headless screenshot-to-PDF generation for cb-visual using Playwright.

Loads the local index.html via HTTP, injects CSVs, discovers schools,
and captures a full-page screenshot per school. Each screenshot is
converted to a single-page PDF (page size = image size) so charts
are never clipped or scaled to A4.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

from playwright.sync_api import sync_playwright
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

# Get current date in YYYY-MM-DD format
REPORT_DATE = datetime.now().strftime("%Y-%m-%d")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def start_http_server(port=0):
    """Start a background HTTP server in the project root. Returns (thread, port)."""
    handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=str(PROJECT_ROOT), **kwargs)
    server = HTTPServer(("127.0.0.1", port), handler)
    if port == 0:
        port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[HTTP] Serving {PROJECT_ROOT} on http://127.0.0.1:{port}")
    return thread, port


def read_csv(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    config = load_config()
    viz = config["visualizer"]
    pdf_cfg = config.get("pdf", {})
    out_cfg = config["output"]

    devices_csv_path = PROJECT_ROOT / out_cfg["transformed_devices_csv"]
    users_csv_path = PROJECT_ROOT / out_cfg["transformed_users_csv"]
    pdf_output_dir = PROJECT_ROOT / out_cfg["pdf_output_dir"]
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = PROJECT_ROOT / "data" / "tmp_screenshots"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if not devices_csv_path.exists():
        print(f"[ERROR] Devices CSV not found: {devices_csv_path}")
        return 1
    if not users_csv_path.exists():
        print(f"[ERROR] Users CSV not found: {users_csv_path}")
        return 1

    # Start local HTTP server so Playwright can fetch index.html and data/config.json
    _, port = start_http_server()
    url = f"http://127.0.0.1:{port}/index.html"

    devices_csv_text = read_csv(devices_csv_path)
    users_csv_text = read_csv(users_csv_path)

    with sync_playwright() as p:
        # Raspberry Pi / ARM: prefer system chromium if available
        chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
        launch_opts = {"headless": True, "args": ["--no-sandbox", "--disable-setuid-sandbox"]}
        if chromium_path:
            launch_opts["executable_path"] = chromium_path
        browser = p.chromium.launch(**launch_opts)

        # Use a generous desktop viewport so charts render wide and crisp
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
        )
        page = context.new_page()

        print(f"[BROWSER] Navigating to {url}")
        page.goto(url, wait_until="networkidle")

        # Inject visualizer config via localStorage so Settings are applied
        viz_config = {
            "ouPrefix": viz.get("ou_prefix", ""),
            "groupingDepth": viz.get("grouping_depth", 1),
            "excludedPathPatterns": viz.get("excluded_patterns", []),
            "ratioThresholds": {
                "good": viz.get("ratio_good", 1.2),
                "acceptable": viz.get("ratio_acceptable", 1.5),
            },
            "dashboardTitle": viz.get("dashboard_title", "Chromebook Ratio Report"),
        }
        page.evaluate(
            f"""() => {{
                localStorage.setItem('chromebookViz.config', JSON.stringify({json.dumps(viz_config)}));
            }}"""
        )

        # Reload so the page picks up the injected config
        page.goto(url, wait_until="networkidle")

        # Inject CSV text and trigger parsing
        print("[BROWSER] Injecting CSV data...")
        page.evaluate(
            f"""() => {{
                window.lastDevicesCsvText = {json.dumps(devices_csv_text)};
                window.lastUsersCsvText = {json.dumps(users_csv_text)};
                parseDevicesCSV(window.lastDevicesCsvText);
                parseUsersCSV(window.lastUsersCsvText);
                if (devicesData.length > 0 && studentsData.length > 0) {{
                    processCombinedData();
                    updateStats();
                    updateCharts();
                    document.getElementById('content').classList.remove('hidden');
                }}
            }}"""
        )

        # Wait for Chart.js to render
        wait_ms = pdf_cfg.get("wait_ms_after_load", 3000)
        print(f"[BROWSER] Waiting {wait_ms}ms for charts to render...")
        time.sleep(wait_ms / 1000)

        # Discover school names from combinedData
        schools = page.evaluate("() => combinedData.map(s => s.school)")
        if not schools:
            print("[ERROR] No schools found after processing CSVs.")
            return 1

        print(f"[BROWSER] Discovered {len(schools)} school(s): {', '.join(schools[:5])}{'...' if len(schools) > 5 else ''}")

        # Generate one PDF per school via screenshot
        filter_wait = pdf_cfg.get("wait_ms_after_filter", 1500)
        for school in schools:
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in school).strip()
            filename = f"{safe_name}_chromebook_report_{REPORT_DATE}"
            png_path = tmp_dir / f"{filename}.png"
            pdf_path = pdf_output_dir / f"{filename}.pdf"

            print(f"[PDF] Generating: {filename}.pdf")

            # Filter to this school via the search box
            page.evaluate(
                f"""() => {{
                    const el = document.getElementById('searchSchool');
                    if (el) {{
                        el.value = {json.dumps(school)};
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}"""
            )
            time.sleep(filter_wait / 1000)

            # Switch to light theme, hide UI chrome, and repaint charts
            page.evaluate("""() => {
                // Light theme so text renders dark-on-white
                document.documentElement.classList.add('theme-light');
                try { localStorage.setItem('returnspace-theme', 'light'); } catch (e) {}
                if (typeof applyChartDefaults === 'function') applyChartDefaults();
                if (typeof updateCharts === 'function' && devicesData.length && studentsData.length) {
                    updateCharts();
                }

                // Hide elements that are not useful in a PDF report
                const hideSelectors = [
                    '.uploads',
                    '.howto',
                    '.controls',
                    '.settings',
                    '#deviceTable',
                    '.site-controls',
                    'footer',
                    '.btn-group',
                    '#exportPdfBtn',
                    '#exportDashboardBtn'
                ];
                hideSelectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.style.display = 'none');
                });

                // Hide the entire <figure> block that contains the device detail table (Tab. 02)
                const deviceTable = document.getElementById('deviceTable');
                if (deviceTable) {
                    let el = deviceTable.parentElement;
                    while (el && el.tagName !== 'FIGURE') { el = deviceTable.parentElement; }
                    if (el) el.style.display = 'none';
                }
            }""")
            # Allow charts to repaint with light-theme palette
            time.sleep(1.0)

            # Capture full-page screenshot
            page.screenshot(path=str(png_path), full_page=True, type="png")

            # Convert PNG -> PDF (page size equals image dimensions)
            img = Image.open(png_path)
            if img.mode in ("RGBA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1])
                img = background
            else:
                img = img.convert("RGB")

            img.save(str(pdf_path), "PDF", resolution=100.0)
            print(f"[PDF] Saved -> {pdf_path}")

            # Remove temp PNG to save space
            png_path.unlink()

        browser.close()

    # Clean up temp dir if empty
    if tmp_dir.exists() and not any(tmp_dir.iterdir()):
        tmp_dir.rmdir()

    print(f"[DONE] All PDFs written to {pdf_output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
