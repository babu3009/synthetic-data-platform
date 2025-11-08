#!/usr/bin/env python3
"""Generate a Markdown coverage summary from Cobertura XML (coverage.xml).

Writes to stdout so GitHub Actions can append to $GITHUB_STEP_SUMMARY.

Expected file: coverage.xml produced by pytest --cov-report=xml
"""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def main() -> int:
    path = Path("coverage.xml")
    print("## Backend coverage summary")
    if not path.exists():
        print("coverage.xml not found. Was pytest run with --cov-report=xml?")
        return 0
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"Failed to parse coverage.xml: {e}")
        return 1
    root = tree.getroot()
    line_rate = root.attrib.get("line-rate")
    branch_rate = root.attrib.get("branch-rate")
    # Cobertura might not include function rate; treat packages/classes aggregate
    lines_valid = root.attrib.get("lines-valid")
    lines_covered = root.attrib.get("lines-covered")
    branches_valid = root.attrib.get("branches-valid")
    branches_covered = root.attrib.get("branches-covered")

    def pct_str(rate: str | None) -> str:
        if rate is None:
            return "n/a"
        try:
            return f"{float(rate) * 100:.2f}%"
        except ValueError:
            return "n/a"

    print(f"- Lines: {pct_str(line_rate)} ({lines_covered}/{lines_valid})")
    print(f"- Branches: {pct_str(branch_rate)} ({branches_covered}/{branches_valid})")

    # List 5 lowest coverage classes by line-rate
    classes = []
    for pkg in root.findall("packages/package"):
        for cls in pkg.findall("classes/class"):
            rate = cls.attrib.get("line-rate")
            name = cls.attrib.get("filename") or cls.attrib.get("name")
            if rate and name:
                try:
                    classes.append((float(rate), name))
                except ValueError:
                    continue
    classes.sort(key=lambda x: x[0])
    if classes:
        print("\n### Least-covered files (by lines)")
        for rate, name in classes[:5]:
            print(f"- {name}: {rate * 100:.2f}%")
    return 0

if __name__ == "__main__":
    sys.exit(main())