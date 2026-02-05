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


def load_json_versions(json_path):
    """Load PaloAltoVersions.json and find the latest version per release cycle.

    Returns dict: {"12.1": {"version": "12.1.4-h2", "date": "2026-02-04"}, ...}
    """
    with open(json_path, encoding="utf-8") as f:
        entries = json.load(f)

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

        # Keep only the highest version per cycle
        if cycle not in cycles or parsed > parse_version(cycles[cycle]["version"]):
            cycles[cycle] = {"version": version_str, "date": released_date}

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


def apply_updates(content, releases, json_cycles):
    """Apply version updates to the pan-os.md content string.

    Returns (updated_content, list_of_change_descriptions).
    """
    changes = []
    # Process in reverse order so offsets remain valid
    for release in reversed(releases):
        cycle = release["releaseCycle"]
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
