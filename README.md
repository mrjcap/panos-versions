# PAN-OS Version Tracker

This repository maintains a **JSON file** containing metadata about the latest available **PAN-OS versions** for Palo Alto Networks firewalls.

---

## 📄 Overview

A local script (not included in this repository) performs the following tasks:

1. **Connects** to a Palo Alto Networks firewall via the **PAN-OS XML API**.
2. **Fetches** information about the latest available PAN-OS versions.
3. **Updates** a local JSON file with the version data.
4. **Commits & pushes** the updated file to this GitHub repository.

---

## 📁 Repository Contents

- `panos_versions.json`: Machine-readable metadata of available PAN-OS versions (see below).

> 🔒 **Note:** This repository contains **only** the version metadata file.  
> The automation script that generates and uploads this file is **not included**.

---

## 📐 JSON Schema Definition

Each entry in the `panos_versions.json` file adheres to the following structure:
```json
{
  "version": "string (e.g. '11.2.6')",
  "size-kb": "string (numeric, in kilobytes)",
  "released-on": "string (format: 'YYYY/MM/DD HH:mm:ss')",
  "latest": "string ('yes' or 'no')",
  "sha256": "string | null"
}
```
- `version`: PAN-OS version string.
- `size-kb`: Package size in kilobytes as string.
- `released-on`: Release timestamp from the firewall.
- `latest`: Indicates if this is the most recent release.
- `sha256`: Checksum of the image (nullable if unavailable).

---

## 🧪 JSON Example
```json
[
  {
    "version": "11.2.6",
    "size-kb": "979359",
    "released-on": "2025/05/07 10:12:09",
    "latest": "yes",
    "sha256": null
  },
  {
    "version": "10.1.14-h14",
    "size-kb": "433587",
    "released-on": "2025/05/05 13:41:38",
    "latest": "no",
    "sha256": "f5897a8ca0564ac5843de63dff49157eb8049cab4153128cf1864616385c682c"
  }
]
```
---

## 🛠️ Example Usage

This JSON file can be consumed by external scripts for CI/CD pipelines, monitoring, or reporting.

Example in PowerShell:
```powershell
# Load JSON data
$panosVersions = Get-Content -Raw -Path '.\panos_versions.json' | ConvertFrom-Json

# Get the latest version
$latest = $panosVersions | Where-Object { $_.latest -eq 'yes' }

Write-Host "Latest PAN-OS version is: $($latest.version)"
```
```powershell
Invoke-WebRequest 'https://raw.githubusercontent.com/mrjcap/panos-versions/master/PaloAltoVersions.json' | ConvertFrom-Json
```
---

## ✅ Validation & Integrity

To validate the schema:

- Ensure all required fields are present and properly typed.
- Confirm SHA256 hash matches downloaded image (if provided).
- Use tools like jq, ajv, or PowerShell validation functions.

---

## 🤖 Automated endoflife.date Updates

A GitHub Actions workflow automatically creates pull requests to update [endoflife.date](https://github.com/endoflife-date/endoflife.date) whenever new PAN-OS versions are pushed to this repository.

### How it works

1. On every push to `PaloAltoVersions.json`, the workflow runs `.github/scripts/update_panos_endoflife.py`
2. The script compares versions in the JSON with the current state of [`products/pan-os.md`](https://github.com/endoflife-date/endoflife.date/blob/master/products/pan-os.md) in the upstream repository
3. If a newer version is found for any release cycle, and no open `[pan-os]` PR already exists, it creates a PR with the updated version, release date, and release notes link
4. If an open PR already exists, it skips to avoid duplicates

### Manual trigger

The workflow can also be triggered manually from the Actions tab or via CLI:

```bash
gh workflow run update-endoflife.yml --repo mrjcap/panos-versions
```

### Required secret

| Secret | Scope | Purpose |
|---|---|---|
| `ENDOFLIFE_PAT` | `public_repo` | Push to fork and create PRs against upstream |

---

Maintained for reference, version visibility, and automation integration.
