# PAN-OS version tracker

Tracks available Palo Alto Networks PAN-OS releases in a single JSON file,
including whether Palo Alto marks a release as preferred or base.

[![Update endoflife.date PAN-OS](https://github.com/mrjcap/panos-versions/actions/workflows/update-endoflife.yml/badge.svg)](https://github.com/mrjcap/panos-versions/actions/workflows/update-endoflife.yml)

## How it works

An off-repo job queries a live firewall via the PAN-OS XML API, pulls the
current software catalog along with release guidance, and commits the updated
[`PaloAltoVersions.json`](./PaloAltoVersions.json) to this repository.

The updater script runs privately and is not included in this repository.

## Data format

`PaloAltoVersions.json` contains a flat array of release objects:

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
  }
]
```

### Fields

- `version`: Release string (e.g. `11.2.6` or `11.1.13-h3`).
- `released-on`: Release timestamp from the firewall (`YYYY/MM/DD HH:mm:ss`).
- `latest`: `"yes"` if this is the newest release in the feed, otherwise `"no"`.
- `preferred`: `true` if Palo Alto currently recommends this release for production.
- `base`: `true` if this is a baseline image required before installing
  maintenance releases in the feature family.

A release has both flags set to `false` when it is neither a base image nor
currently preferred. Flags update on every run as Palo Alto adjusts guidance.

## Usage examples

### Read local JSON with PowerShell

```powershell
$panosVersions = Get-Content -Raw -Path '.\PaloAltoVersions.json' | ConvertFrom-Json

# Filter preferred releases
$preferred = $panosVersions | Where-Object { $_.preferred -eq $true }
$preferred | Select-Object version, released-on, latest
```

### Fetch directly from GitHub

```powershell
$url = 'https://raw.githubusercontent.com/mrjcap/panos-versions/master/PaloAltoVersions.json'
$panosVersions = Invoke-RestMethod -Uri $url
```

### Select a target release

```powershell
# Pick preferred releases first, fall back to base
$target = $panosVersions | Where-Object { $_.preferred -eq $true }
if (-not $target) {
    $target = $panosVersions | Where-Object { $_.base -eq $true }
}

$target | Select-Object version, preferred, base, latest
```

## Release guidance endpoints

Palo Alto exposes release guidance through operational CLI commands and their
XML API counterparts:

- Preferred releases: `request system software info preferred`

  ```text
  https://<firewall>/api/?type=op&cmd=<request><system><software><info><preferred></preferred></info></software></system></request>
  ```

- Base releases: `request system software info base`

  ```text
  https://<firewall>/api/?type=op&cmd=<request><system><software><info><base></base></info></software></system></request>
  ```

## Automated endoflife.date updates

A GitHub Actions workflow ([`update-endoflife.yml`](.github/workflows/update-endoflife.yml))
keeps [endoflife.date](https://github.com/endoflife-date/endoflife.date) in sync:

1. When `PaloAltoVersions.json` updates on `master`, the workflow runs
   `.github/scripts/update_panos_endoflife.py`.
2. The script compares versions against upstream `products/pan-os.md`.
3. If a newer release exists for any cycle and no open `[pan-os]` PR is pending,
   it opens a pull request on upstream.

### Manual trigger

```bash
gh workflow run update-endoflife.yml --repo mrjcap/panos-versions
```

### Workflow secrets and variables

| Name | Type | Purpose |
| --- | --- | --- |
| `ENDOFLIFE_PAT` | Secret (`public_repo`) | Authenticates to fork and opens PRs against upstream |
| `GIT_NAME` | Variable | Git commit author name |
| `GIT_EMAIL` | Variable | Git commit author email |
