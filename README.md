# PAN-OS Version Tracker

This repository maintains a **JSON file** containing metadata about available **PAN-OS versions** for Palo Alto Networks firewalls, including whether a release is marked by PAN as **preferred** or **base**.

[![Update endoflife.date PAN-OS](https://github.com/mrjcap/panos-versions/actions/workflows/update-endoflife.yml/badge.svg)](https://github.com/mrjcap/panos-versions/actions/workflows/update-endoflife.yml)

---

## 📄 Overview

A local script (not included in this repository) performs the following tasks:

1. **Connects** to a Palo Alto Networks firewall via the **PAN-OS XML API**.
2. **Fetches** information about available PAN-OS versions.
3. **Retrieves** PAN-provided release guidance using:

- `request system software info preferred`
- `request system software info base`

1. **Updates** a local JSON file with the version data.
2. **Commits & pushes** the updated file to this GitHub repository.

The JSON output is intended to provide a machine-readable source of truth for:

- Available PAN-OS releases.
- PAN-designated **preferred** releases.
- PAN-designated **base** releases.
- Automation and reporting workflows that depend on version metadata.

---

## 📁 Repository Contents

- `PaloAltoVersions.json`: Machine-readable metadata of available PAN-OS versions.

> 🔒 **Note:** This repository contains **only** the version metadata file.
> The automation script that generates and uploads this file is **not included**.

---

## 📐 JSON Schema Definition

Each entry in the `PaloAltoVersions.json` file adheres to the following structure:

```json
{
  "version": "string (e.g. '11.2.6')",
  "released-on": "string (format: 'YYYY/MM/DD HH:mm:ss')",
  "latest": "string ('yes' or 'no')",
  "preferred": "boolean",
  "base": "boolean"
}
```

### Field descriptions

- `version`: PAN-OS version string.
- `released-on`: Release timestamp reported by the firewall.
- `latest`: Indicates whether the version is marked as the most recent available release.
- `preferred`: Indicates whether PAN marks the release as a **preferred** version.
- `base`: Indicates whether PAN marks the release as a **base** version.

### Notes

- A release can be:
- `preferred: true`
- `base: true`
- both `false`
- A release with both `preferred: false` and `base: false` is simply **not currently designated** as preferred or base.
- The `preferred` and `base` flags are refreshed on each run so existing entries can be updated when PAN changes release guidance.

---

## 🧪 JSON Example

```json
[
  {
    "version": "11.1.13-h3",
    "released-on": "2026/03/18 13:43:07",
    "latest": "no",
    "preferred": true,
    "base": false
  },
  {
    "version": "11.1.0",
    "released-on": "2023/11/02 12:02:50",
    "latest": "no",
    "preferred": false,
    "base": true
  },
  {
    "version": "11.1.14",
    "released-on": "2026/04/15 15:10:57",
    "latest": "yes",
    "preferred": false,
    "base": false
  }
]
```

---

## 🛠️ Example Usage

This JSON file can be consumed by external scripts for CI/CD pipelines, monitoring, reporting, or release selection logic.

### PowerShell example

Example in PowerShell:

```powershell
# Load JSON data
$panosVersions = Get-Content -Raw -Path '.\PaloAltoVersions.json' | ConvertFrom-Json

# Get the latest version
$latest = $panosVersions | Where-Object { $_.latest -eq 'yes' }

# Get preferred versions
$preferred = $panosVersions | Where-Object { $_.preferred -eq $true }

# Get base versions
$base = $panosVersions | Where-Object { $_.base -eq $true }

Write-Host "Latest PAN-OS version(s): $($latest.version -join ', ')"
Write-Host "Preferred PAN-OS version(s): $($preferred.version -join ', ')"
Write-Host "Base PAN-OS version(s): $($base.version -join ', ')"
```

### Fetch directly from GitHub

```powershell
Invoke-WebRequest 'https://raw.githubusercontent.com/mrjcap/panos-versions/master/PaloAltoVersions.json' | ConvertFrom-Json
```

### Example selection logic

```powershell
# Example: choose preferred releases first
$recommended = $panosVersions | Where-Object { $_.preferred -eq $true }

if (-not $recommended) {
$recommended = $panosVersions | Where-Object { $_.base -eq $true }
}

$recommended | Select-Object version, preferred, base, latest
```

---

## 🔄 How release guidance works

PAN-OS now exposes release guidance through dedicated commands that distinguish between:

- **Preferred** releases, versions PAN currently recommends.
- **Base** releases, baseline versions typically required before upgrading within a major release family.

The automation uses these API equivalents:

### Preferred releases

```text
https://<firewall>/api/?type=op&cmd=<request><system><software><info><preferred></preferred></info></software></system></request>
```

### Base releases

```text
https://<firewall>/api/?type=op&cmd=<request><system><software><info><base></base></info></software></system></request>
```

These are evaluated alongside the standard software check response so the JSON file reflects both:

- version availability metadata, and
- PAN support guidance metadata.

---

## ✅ Validation & Integrity

To validate the data:

- Ensure all required fields are present and correctly typed.
- Confirm `preferred` and `base` are booleans.
- Confirm `released-on` matches the expected `YYYY/MM/DD HH:mm:ss` format.
- Confirm `latest` is either `yes` or `no`.
- Use tools such as `jq`, `ajv`, or PowerShell validation functions.

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

| Secret          | Scope         | Purpose                                      |
| --------------- | ------------- | -------------------------------------------- |
| `ENDOFLIFE_PAT` | `public_repo` | Push to fork and create PRs against upstream |

---

## ℹ️ Notes

- This repository is intended for **reference**, **version visibility**, and **automation integration**.
- The source firewall may update release guidance over time, so `preferred` and `base` values are not static and may change between runs.
- Existing JSON entries are updated when PAN changes release designation, not only when new versions appear.

---

Maintained for reference, version visibility, and automation integration.
