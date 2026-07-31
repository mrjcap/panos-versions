# PAN-OS Version Automation & EOL Rules

1. **New Release Cycle Insertion**:
   - When `PaloAltoVersions.json` contains a new release cycle (e.g., `12.2`) missing from `pan-os.md`, insert the new cycle block into `pan-os.md` preserving descending numerical cycle order (e.g., `12.2` above `12.1`).

2. **Empirical Date Proof Invariant**:
   - `releaseDate`: Must be sourced from the scraped official Palo Alto EOL summary page, or fall back to the earliest `released-on` date in `PaloAltoVersions.json` for that cycle (`min_date`).
   - `eol`: Must be sourced from the scraped official Palo Alto EOL summary page. If the cycle is not yet listed on the EOL summary page, `eol` MUST be set to `false`. NEVER calculate, guess, or extrapolate EOL dates without explicit vendor proof.

3. **Incremental Graph Verification**:
   - After creating or editing Python scripts in `panos-versions`, run `python .github/scripts/test_update_panos_endoflife.py` and sync the knowledge graph via `/graphify update .`.
