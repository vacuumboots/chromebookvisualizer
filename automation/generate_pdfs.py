#!/usr/bin/env python3
"""
Headless PDF generation for cb-visual using Playwright.

Loads the local index.html, injects the two CSVs, discovers schools,
and prints one PDF per school using the browser's built-in print-to-PDF
(which respects the existing @media print stylesheet).
"""
import json
import os
import sys
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

from playwright.sync_api import sync_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


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
    pdf_cfg = config["pdf"]
    out_cfg = config["output"]

    devices_csv_path = PROJECT_ROOT / out_cfg["transformed_devices_csv"]
    users_csv_path = PROJECT_ROOT / out_cfg["transformed_users_csv"]
    pdf_output_dir = PROJECT_ROOT / out_cfg["pdf_output_dir"]
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

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
        if chromium_path:
            browser = p.chromium.launch(executable_path=chromium_path, headless=True)
        else:
            browser = p.chromium.launch(headless=True)

        context = browser.new_context()
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
        wait_ms = pdf_cfg.get("wait_ms_after_load", 1200)
        print(f"[BROWSER] Waiting {wait_ms}ms for charts to render...")
        time.sleep(wait_ms / 1000)

        # Discover school names from combinedData
        schools = page.evaluate("() => combinedData.map(s => s.school)")
        if not schools:
            print("[ERROR] No schools found after processing CSVs.")
            return 1

        print(f"[BROWSER] Discovered {len(schools)} school(s): {', '.join(schools[:5])}{'...' if len(schools) > 5 else ''}")

        # Generate one PDF per school
        filter_wait = pdf_cfg.get("wait_ms_after_filter", 800)
        for school in schools:
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in school).strip()
            filename = f"{safe_name}_chromebook_report.pdf"
            pdf_path = pdf_output_dir / filename

            print(f"[PDF] Generating: {filename}")

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

            # Use native print-to-PDF; @media print styles hide controls and paginate figures
            page.pdf(
                path=str(pdf_path),
                format=pdf_cfg.get("format", "A4"),
                print_background=pdf_cfg.get("print_background", True),
                prefer_css_page_size=pdf_cfg.get("prefer_css_page_size", True),
            )
            print(f"[PDF] Saved -> {pdf_path}")

        browser.close()

    print(f"[DONE] All PDFs written to {pdf_output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
