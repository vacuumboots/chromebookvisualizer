# Chromebook Fleet Ratio Visualizer

A single-file, zero-install HTML tool for visualizing student-to-Chromebook ratios across schools, using the standard user and device CSV exports from the Google Workspace Admin Console.

Designed to work for any Google Workspace tenant. All organization-specific behavior (OU prefix, excluded OUs, ratio thresholds, dashboard title) is configured through a **Settings** panel in the UI — no code edits required.

## What it does

- Groups users and devices by organizational unit (OU) to produce per-school counts.
- Computes a student-to-device ratio for each school with configurable health-banded coloring (green / yellow / red).
- Keeps only users whose Google Workspace `Status` is `Active`.
- Lets you exclude any OU substrings you don't want counted (e.g. `/staff`, `exam`, `/test`).
- Interactive: search schools, filter by device model / manufacturing year / Chrome OS version, switch between device counts, student counts, and ratios.
- 100% client-side — no server, no account, no uploads. CSVs are parsed in the browser and never leave the machine.

## Quick start

1. Open `index.html` in any modern browser (double-click the file), or visit the hosted site if deployed to GitHub Pages.
2. Expand the **Settings** panel and enter values appropriate for your org (see [Configuration](#configuration)).
3. Export your two CSVs from the Google Workspace Admin Console (see [Exporting your data](#exporting-your-data)).
4. Upload the devices CSV, then the users CSV.
5. The dashboard renders automatically.

No build step, no dependencies to install. Chart.js is loaded from a CDN inside the HTML.

## Configuration

The tool exposes a **Settings** panel with the following fields:

| Field | What it does | Example |
| --- | --- | --- |
| **OU prefix** | Only rows whose OU path starts with this string are kept. Leave empty to include every OU. | `/your/ou/prefix/` |
| **Group-name depth after prefix** | How many path segments after the prefix form the "school" label. `1` = first segment; `0` = the full remaining path. | `1` → `NorthHigh` from `/your/ou/prefix/NorthHigh/Students` |
| **Exclude OU paths containing** | Comma- or newline-separated substrings. Any row whose full OU path contains any of these (case-insensitive) is dropped. Applies to both CSVs. | `/staff, exam, administration, maint` |
| **Ratio thresholds** | `Good` is the green upper bound; `Acceptable` is the yellow upper bound; anything above is red. | `1.2` / `1.5` |
| **Dashboard title** | Sets the browser tab title and the page header, for self-branding. | `Acme ISD Chromebook Ratios` |

### Where settings come from

At page load, settings are resolved in this order:

1. **`localStorage`** (key `chromebookViz.config`) — whatever you last clicked **Save** with, in this browser. Takes precedence.
2. **`data/config.json`** — a git-ignored file you can commit to your local filesystem. Auto-loaded via `fetch()` when localStorage is empty. Useful if you want a portable config that doesn't live in a single browser's storage.
3. **Neutral defaults** — if neither of the above is available.

`example.config.json` is checked into the repo and documents the JSON schema. Copy it to `data/config.json`, adjust for your org, and it will auto-load on next page open.

### Working around `file://` fetch restrictions

Most browsers (Chrome, Edge) refuse to `fetch()` a local file from a page opened via `file://`. If auto-load silently does nothing, you have three options:

- Click **Load from file...** in the Settings panel and pick your `data/config.json` (or any valid JSON). This uses the browser's file-picker API, which has no origin restriction.
- Serve the folder with a tiny local HTTP server, e.g. `python3 -m http.server 8000`, then open `http://localhost:8000/`. Auto-fetch works over HTTP.
- Just type the values into the Settings panel and click **Save** — the values persist in `localStorage` for that browser.

### Buttons

- **Save** — persists current form values to `localStorage`. Re-runs the pipeline if CSVs are already loaded.
- **Reset to defaults** — clears `localStorage` and re-loads from `data/config.json` (if present) or neutral defaults.
- **Load from file...** — opens a file picker, loads JSON into the form (does not auto-save; click **Save** to persist).

## Exporting your data

### Devices CSV

1. Google Workspace Admin Console → **Devices** → **Chrome devices**.
2. Use the filter panel to narrow the fleet if desired (optional).
3. Click the download / export icon. Google generates a UUID-named file.
4. Upload as-is. The tool reads `orgUnitPath`, `model`, `lastPolicySync`, `manufacturingDate`, and `osVersion` — no preprocessing needed.

### Users CSV

1. Google Workspace Admin Console → **Directory** → **Users**.
2. Click **Download users** → choose **All user info**.
3. Google generates `User_Download_<date>_<time>.csv`.
4. Upload as-is. The tool reads `Org Unit Path [Required]` and `Status [READ ONLY]`, and filters to `Active` users automatically.

## CSV format reference

### Devices CSV

| Column | Required? | How it's located | Use |
| --- | --- | --- | --- |
| `orgUnitPath` | yes | case-insensitive name match | group by school |
| `model` | no | case-insensitive name match | model filter |
| `lastPolicySync` | no | case-insensitive name match | recency display |
| `manufacturingDate` | no | case-insensitive name match | year filter |
| `osVersion` | no | case-insensitive name match | Chrome OS filter |
| `autoUpdateExpiration` | no | case-insensitive name match | expiration display & chart |

Column **order** does not matter. Extra columns are ignored.

### Users CSV

| Column | Required? | How it's located | Use |
| --- | --- | --- | --- |
| `Org Unit Path [Required]` | yes | exact header match | group by school |
| `Status [READ ONLY]` | no | exact header match | filter to `Active` |

If the `Status` column is absent (e.g. a hand-trimmed legacy CSV), all rows are assumed Active for backward compatibility.

### Row-level filtering

A row is kept only if **all** of the following hold:

- Its OU path starts with the configured prefix (or the prefix is empty).
- Its OU path does not contain any of the configured exclude substrings.
- For users: its `Status` is `Active` (when the Status column is present).

## Privacy

- All parsing is client-side. No data is sent to any server; Chart.js from the CDN is the only outbound request and does not receive any of your data.
- The source CSVs contain PII (email addresses, device serial numbers, IP addresses, last sign-in times). **Do not commit them.** The included `.gitignore` keeps anything in `data/` out of the repo, along with `CLAUDE.md` and `.claude/`.

## Project structure

```
index.html                    The tool. Pure HTML + inline JS + Chart.js.
example.config.json           Worked example of the Settings-panel config.
README.md                     This file.
.gitignore                    Keeps data/, CLAUDE.md, .claude/ out of git.
data/                         (Local only, git-ignored.)
  config.json                 Your real config; auto-loaded when localStorage is empty.
  *.csv                       Your Google Workspace exports.
```

No build system, no package manager, no tests. Open the HTML, edit, reload.

## Development

- Chart rendering uses Chart.js (loaded from CDN in `<head>`).
- The CSV parser handles quoted fields and newlines embedded inside quoted fields (needed for Google's device exports, which put multi-line notes in `annotatedNotes`).
- Config is persisted to `localStorage` under the key `chromebookViz.config` and hydrated at page load; raw CSV text is retained in memory so the pipeline can be re-run when settings change.
- Chart cleanup uses a canvas-replacement strategy to avoid memory growth on repeated updates; chart updates are debounced by 300 ms.
- Only the top 20 schools (by current sort) are shown in charts, for readability.

## License

_Choose a license before publishing (MIT is the usual default for tools like this)._

## Contributing

_Issues and PRs welcome once the project is public. Please anonymize any CSV attachments._
