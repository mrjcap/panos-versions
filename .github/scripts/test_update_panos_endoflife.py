#!/usr/bin/env python3
import json
import os
import sys
import unittest
from pathlib import Path

# Add script directory to sys.path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from update_panos_endoflife import (
    parse_version,
    get_release_cycle,
    build_release_notes_url,
    _normalize_key,
    load_json_versions,
    parse_md_releases,
    apply_updates,
    fetch_paloalto_eol_dates,
)


class TestUpdatePanOsEndOfLife(unittest.TestCase):

    def test_parse_version(self):
        self.assertEqual(parse_version("12.2.2"), (12, 2, 2, 0))
        self.assertEqual(parse_version("12.1.4-h2"), (12, 1, 4, 2))
        self.assertEqual(parse_version("10.2.10-h31"), (10, 2, 10, 31))
        self.assertIsNone(parse_version("invalid"))

    def test_get_release_cycle(self):
        self.assertEqual(get_release_cycle("12.2.2"), "12.2")
        self.assertEqual(get_release_cycle("12.1.4-h2"), "12.1")
        self.assertEqual(get_release_cycle("10.2.10"), "10.2")

    def test_build_release_notes_url(self):
        # Test 12.2 release
        url_12_2 = build_release_notes_url("12.2.2")
        self.assertEqual(
            url_12_2,
            "https://docs.paloaltonetworks.com/ngfw/release-notes/12-2/pan-os-12-2-2-known-and-addressed-issues/pan-os-12-2-2-addressed-issues",
        )

        # Test 12.1 release
        url_12_1 = build_release_notes_url("12.1.8")
        self.assertEqual(
            url_12_1,
            "https://docs.paloaltonetworks.com/ngfw/release-notes/12-1/pan-os-12-1-8-known-and-addressed-issues/pan-os-12-1-8-addressed-issues",
        )

        # Test 10.2 release
        url_10_2 = build_release_notes_url("10.2.10-h2")
        self.assertEqual(
            url_10_2,
            "https://docs.paloaltonetworks.com/pan-os/10-2/pan-os-release-notes/pan-os-10-2-10-known-and-addressed-issues/pan-os-10-2-10-h2-addressed-issues",
        )

    def test_apply_updates_existing_cycle(self):
        md_content = """# PAN-OS

releases:
  - releaseCycle: "12.1"
    releaseDate: 2025-08-28
    eol: 2028-08-28
    latest: "12.1.4"
    latestReleaseDate: 2026-02-04
    link: https://docs.paloaltonetworks.com/ngfw/release-notes/12-1/pan-os-12-1-4-known-and-addressed-issues/pan-os-12-1-4-addressed-issues
---
"""
        json_cycles = {
            "12.1": {"version": "12.1.8", "date": "2026-07-07"}
        }
        releases = parse_md_releases(md_content)
        updated, changes = apply_updates(md_content, releases, json_cycles, eol_map={})

        self.assertIn('latest: "12.1.8"', updated)
        self.assertIn("latestReleaseDate: 2026-07-07", updated)
        self.assertIn("pan-os-12-1-8-addressed-issues", updated)
        self.assertEqual(changes, ["12.1: 12.1.4 -> 12.1.8"])

    def test_apply_updates_new_release_cycle(self):
        md_content = """# PAN-OS

releases:
  - releaseCycle: "12.1"
    releaseDate: 2025-08-28
    eol: 2028-08-28
    latest: "12.1.8"
    latestReleaseDate: 2026-07-07
    link: https://docs.paloaltonetworks.com/ngfw/release-notes/12-1/pan-os-12-1-8-known-and-addressed-issues/pan-os-12-1-8-addressed-issues

  - releaseCycle: "11.2"
    releaseDate: 2024-05-02
    eol: 2027-05-02
    latest: "11.2.3"
    latestReleaseDate: 2026-06-01
    link: https://docs.paloaltonetworks.com/pan-os/11-2/pan-os-release-notes/pan-os-11-2-addressed-issues/pan-os-11-2-3-addressed-issues
---
"""
        json_cycles = {
            "12.2": {"version": "12.2.2", "date": "2026-07-07"},
            "12.1": {"version": "12.1.8", "date": "2026-07-07"},
            "11.2": {"version": "11.2.3", "date": "2026-06-01"},
        }
        eol_map = {
            "12.2": {"releaseDate": "2026-07-01", "eol": "2029-07-01"}
        }

        releases = parse_md_releases(md_content)
        updated, changes = apply_updates(md_content, releases, json_cycles, eol_map=eol_map)

        self.assertIn('Added new release cycle 12.2: 12.2.2', changes)
        self.assertIn('  - releaseCycle: "12.2"', updated)
        self.assertIn('    releaseDate: 2026-07-01', updated)
        self.assertIn('    eol: 2029-07-01', updated)
        self.assertIn('    latest: "12.2.2"', updated)
        self.assertIn('    latestReleaseDate: 2026-07-07', updated)
        self.assertIn('    link: https://docs.paloaltonetworks.com/ngfw/release-notes/12-2/pan-os-12-2-2-known-and-addressed-issues/pan-os-12-2-2-addressed-issues', updated)

        # Verify ordering: 12.2 should appear before 12.1
        idx_12_2 = updated.find('releaseCycle: "12.2"')
        idx_12_1 = updated.find('releaseCycle: "12.1"')
        self.assertTrue(idx_12_2 < idx_12_1, "New release cycle 12.2 should be inserted before 12.1")

    def test_apply_updates_unannounced_eol(self):
        md_content = """# PAN-OS

releases:
  - releaseCycle: "12.1"
    releaseDate: 2025-08-28
    eol: 2028-08-28
    latest: "12.1.8"
    latestReleaseDate: 2026-07-07
    link: https://docs.paloaltonetworks.com/ngfw/release-notes/12-1/pan-os-12-1-8-known-and-addressed-issues/pan-os-12-1-8-addressed-issues
---
"""
        json_cycles = {
            "12.2": {"version": "12.2.2", "date": "2026-07-30", "min_date": "2026-07-01"},
            "12.1": {"version": "12.1.8", "date": "2026-07-07", "min_date": "2025-08-28"},
        }
        # eol_map has no entry for 12.2 (Palo Alto EOL page has not been updated with 12.2)
        eol_map = {}

        releases = parse_md_releases(md_content)
        updated, changes = apply_updates(md_content, releases, json_cycles, eol_map=eol_map)

        self.assertIn('  - releaseCycle: "12.2"', updated)
        self.assertIn('    releaseDate: 2026-07-01', updated)
        self.assertIn('    eol: false', updated)
        self.assertIn('    latest: "12.2.2"', updated)
        self.assertIn('    latestReleaseDate: 2026-07-30', updated)


if __name__ == "__main__":
    unittest.main()

