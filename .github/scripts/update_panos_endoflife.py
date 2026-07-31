#!/usr/bin/env python3
"""Check PaloAltoVersions.json for new versions and update pan-os.md accordingly.

Compares versions from the JSON source with the current state of pan-os.md
in the endoflife-date/endoflife.date repository. Outputs an updated file
when newer versions are found.
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime



def parse_version(version_str):
    """Parse a PAN-OS version string into a comparable tuple.

    Examples:
        "12.1.4-h2" -> (12, 1, 4, 2)
        "12.1.4"    -> (12, 1, 4, 0)
        "10.2.10-h31" -> (10, 2, 10, 31)
    """
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-h(\d+))?$", version_str)
    if not match:
        return None
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    hotfix = int(match.group(4)) if match.group(4) else 0
    return (major, minor, patch, hotfix)


def get_release_cycle(version_str):
    """Extract release cycle from version string.

    "12.1.4-h2" -> "12.1"
    """
    match = re.match(r"(\d+\.\d+)", version_str)
    return match.group(1) if match else None


def build_release_notes_url(version_str):
    """Construct the Palo Alto release notes URL for a given version.

    Returns None for versions <= 8.0 (PDF links, not auto-updatable).
    """
    cycle = get_release_cycle(version_str)
    if not cycle:
        return None

    major, minor = map(int, cycle.split("."))
    cycle_dashed = f"{major}-{minor}"

    # Split version into base and optional hotfix
    parts = version_str.split("-")
    base_version = parts[0]  # e.g. "12.1.4"
    hotfix = parts[1] if len(parts) > 1 else None  # e.g. "h2"

    base_dashed = base_version.replace(".", "-")  # "12-1-4"
    full_dashed = f"{base_dashed}-{hotfix}" if hotfix else base_dashed  # "12-1-4-h2"

    if (major, minor) >= (12, 1):
        return (
            f"https://docs.paloaltonetworks.com/ngfw/release-notes/{cycle_dashed}"
            f"/pan-os-{base_dashed}-known-and-addressed-issues"
            f"/pan-os-{full_dashed}-addressed-issues"
        )
    elif (major, minor) >= (10, 1):
        return (
            f"https://docs.paloaltonetworks.com/pan-os/{cycle_dashed}"
            f"/pan-os-release-notes"
            f"/pan-os-{base_dashed}-known-and-addressed-issues"
            f"/pan-os-{full_dashed}-addressed-issues"
        )
    elif (major, minor) >= (8, 1):
        return (
            f"https://docs.paloaltonetworks.com/pan-os/{cycle_dashed}"
            f"/pan-os-release-notes"
            f"/pan-os-{cycle_dashed}-addressed-issues"
            f"/pan-os-{full_dashed}-addressed-issues"
        )
    return None


def _normalize_key(key):
    """Convert PascalCase to kebab-case lowercase.

    Examples: "Version" -> "version", "ReleasedOn" -> "released-on"
    """
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "-", key).lower()


def load_json_versions(json_path):
    """Load PaloAltoVersions.json and find the latest version per release cycle.

    Returns dict: {
        "12.1": {"version": "12.1.8", "date": "2026-07-07", "min_date": "2025-08-28"}, ...
    }
    Accepts both PascalCase keys (from PowerShell) and kebab-case keys.
    """
    raw = open(json_path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    entries = json.loads(text)

    # Normalize keys: PascalCase ("Version") -> kebab-case ("version")
    entries = [{_normalize_key(k): v for k, v in e.items()} for e in entries]

    cycles = {}
    for entry in entries:
        version_str = entry["version"]
        parsed = parse_version(version_str)
        if not parsed:
            continue

        cycle = get_release_cycle(version_str)
        if not cycle:
            continue

        # Parse release date: "2026/02/04 11:11:55" -> "2026-02-04"
        released_date = datetime.strptime(
            entry["released-on"], "%Y/%m/%d %H:%M:%S"
        ).strftime("%Y-%m-%d")

        if cycle not in cycles:
            cycles[cycle] = {
                "version": version_str,
                "date": released_date,
                "min_date": released_date,
            }
        else:
            if parsed > parse_version(cycles[cycle]["version"]):
                cycles[cycle]["version"] = version_str
                cycles[cycle]["date"] = released_date
            if released_date < cycles[cycle]["min_date"]:
                cycles[cycle]["min_date"] = released_date

    return cycles


def parse_md_releases(content):
    """Parse release blocks from pan-os.md content using regex.

    Returns list of dicts with keys: releaseCycle, latest, latestReleaseDate, link,
    plus _start and _end offsets into the original content.
    """
    releases = []
    # Match each release cycle block: starts with "  - releaseCycle:" and extends
    # until the next "  - releaseCycle:" or end of the releases section ("---").
    pattern = re.compile(
        r"^  - releaseCycle: \"([^\"]+)\".*?(?=\n  - releaseCycle:|\n---)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(content):
        block = match.group(0)
        cycle = match.group(1)

        def extract(field, text):
            m = re.search(rf"    {field}: (.+)", text)
            if not m:
                return None
            val = m.group(1).strip()
            return val.strip('"')

        releases.append(
            {
                "releaseCycle": cycle,
                "latest": extract("latest", block),
                "latestReleaseDate": extract("latestReleaseDate", block),
                "link": extract("link", block),
                "_start": match.start(),
                "_end": match.end(),
                "_text": block,
            }
        )
    return releases


def fetch_paloalto_eol_dates():
    """Fetch releaseDate and eol date mapping per cycle from Palo Alto EOL summary page.

    Returns dict: {"12.1": {"releaseDate": "2025-08-28", "eol": "2028-08-28"}, ...}
    """
    url = "https://www.paloaltonetworks.com/services/support/end-of-life-announcements/end-of-life-summary"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Warning: Failed to fetch Palo Alto EOL page: {e}", file=sys.stderr)
        return {}

    eol_map = {}
    tables = re.findall(r"<table.*?>(.*?)</table>", html, re.DOTALL)
    for t in tables:
        if "PAN-OS" not in t:
            continue
        rows = re.findall(r"<tr.*?>(.*?)</tr>", t, re.DOTALL)
        for r in rows:
            cols = [
                re.sub(r"\s+", " ", re.sub(r"<.*?>", "", c)).strip()
                for c in re.findall(r"<t[dh].*?>(.*?)</t[dh]>", r, re.DOTALL)
            ]
            if len(cols) >= 3:
                cycle_str = cols[0]
                rel_date_str = cols[1]
                eol_date_str = cols[2]

                m_cycle = re.match(r"^(\d+\.\d+)", cycle_str)
                if not m_cycle:
                    continue
                cycle = m_cycle.group(1)

                def parse_date(d_str):
                    clean_d = re.sub(r"[^a-zA-Z0-9,\s]", "", d_str).strip()
                    try:
                        dt = datetime.strptime(clean_d, "%B %d, %Y")
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        return None

                rel_date = parse_date(rel_date_str)
                eol_date = parse_date(eol_date_str)
                if rel_date:
                    eol_map[cycle] = {
                        "releaseDate": rel_date,
                        "eol": eol_date if eol_date else "false",
                    }
    return eol_map


def apply_updates(content, releases, json_cycles, eol_map=None):
    """Apply version updates to the pan-os.md content string.

    Returns (updated_content, list_of_change_descriptions).
    """
    changes = []

    # 1. Update existing release cycles in pan-os.md
    existing_cycles = set()
    for release in reversed(releases):
        cycle = release["releaseCycle"]
        existing_cycles.add(cycle)
        if cycle not in json_cycles:
            continue

        current_version = release["latest"] or ""
        new_version = json_cycles[cycle]["version"]
        new_date = json_cycles[cycle]["date"]

        current_parsed = parse_version(current_version) if current_version else (0, 0, 0, 0)
        new_parsed = parse_version(new_version)
        if not new_parsed or not (new_parsed > current_parsed):
            continue

        new_url = build_release_notes_url(new_version)
        block = release["_text"]
        updated_block = block

        # Update latest
        updated_block = re.sub(
            r'(    latest: )"[^"]*"',
            rf'\g<1>"{new_version}"',
            updated_block,
        )
        # Update latestReleaseDate
        updated_block = re.sub(
            r"(    latestReleaseDate: )\S+",
            rf"\g<1>{new_date}",
            updated_block,
        )
        # Update link (only if we can construct a valid URL)
        if new_url and "    link:" in updated_block:
            updated_block = re.sub(
                r"(    link: )\S+",
                rf"\g<1>{new_url}",
                updated_block,
            )

        content = content[: release["_start"]] + updated_block + content[release["_end"] :]
        changes.append(f"{cycle}: {current_version} -> {new_version}")

    # 2. Check for new release cycles in json_cycles missing from pan-os.md
    missing_cycles = [c for c in json_cycles if c not in existing_cycles]
    if missing_cycles:
        if eol_map is None:
            eol_map = fetch_paloalto_eol_dates()

        def cycle_key(c):
            return list(map(int, c.split(".")))

        # Sort missing cycles in descending numeric order
        missing_cycles.sort(key=cycle_key, reverse=True)

        for cycle in missing_cycles:
            version_str = json_cycles[cycle]["version"]
            latest_date = json_cycles[cycle]["date"]
            url = build_release_notes_url(version_str)

            # Determine releaseDate:
            # 1) Official scraped releaseDate from Palo Alto EOL summary page if available
            # 2) Fallback to earliest released-on date in PaloAltoVersions.json for this cycle
            if cycle in eol_map and eol_map[cycle].get("releaseDate"):
                rel_date = eol_map[cycle]["releaseDate"]
            else:
                rel_date = json_cycles[cycle].get("min_date", latest_date)

            # Determine eol:
            # 1) Official scraped eol date from Palo Alto EOL summary page if available
            # 2) Fallback to false (no guessing or extrapolating EOL date without official proof)
            if cycle in eol_map and eol_map[cycle].get("eol") and eol_map[cycle]["eol"] != "false":
                eol_date = eol_map[cycle]["eol"]
            else:
                eol_date = "false"

            new_block_lines = [
                f'  - releaseCycle: "{cycle}"',
                f"    releaseDate: {rel_date}",
                f"    eol: {eol_date}",
                f'    latest: "{version_str}"',
                f"    latestReleaseDate: {latest_date}",
            ]
            if url:
                new_block_lines.append(f"    link: {url}")
            new_block = "\n".join(new_block_lines) + "\n\n"

            # Re-parse releases from the updated content to obtain accurate offsets
            current_releases = parse_md_releases(content)

            insert_pos = None
            for r in current_releases:
                r_cycle = r["releaseCycle"]
                if cycle_key(cycle) > cycle_key(r_cycle):
                    insert_pos = r["_start"]
                    break

            if insert_pos is not None:
                content = content[:insert_pos] + new_block + content[insert_pos:]
            else:
                if current_releases:
                    last_end = current_releases[-1]["_end"]
                    content = content[:last_end] + "\n" + new_block + content[last_end:]
                else:
                    content = content + "\n" + new_block

            changes.append(f"Added new release cycle {cycle}: {version_str}")

    return content, changes



def main():
    parser = argparse.ArgumentParser(description="Update pan-os.md with new PAN-OS versions")
    parser.add_argument("--json", required=True, help="Path to PaloAltoVersions.json")
    parser.add_argument("--md", required=True, help="Path to current pan-os.md")
    parser.add_argument("--output", required=True, help="Path to write updated pan-os.md")
    args = parser.parse_args()

    json_cycles = load_json_versions(args.json)
    with open(args.md, encoding="utf-8") as f:
        content = f.read()

    releases = parse_md_releases(content)
    updated_content, changes = apply_updates(content, releases, json_cycles)

    if not changes:
        print("NO_UPDATES")
        sys.exit(0)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print("UPDATES_FOUND")
    for change in changes:
        print(change)


if __name__ == "__main__":
    main()
