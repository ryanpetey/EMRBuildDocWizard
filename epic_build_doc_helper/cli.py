from __future__ import annotations

import argparse

from .exporter import export_outputs
from .parser import parse_evaluate_export, parse_package_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Epic Build Documentation Helper (local prototype)")
    parser.add_argument("package_export", help="Path to Epic CM package export text file")
    parser.add_argument("--evaluate-export", help="Optional path to Epic Evaluate Records diff export")
    parser.add_argument("--xlsx", default="epic_build_documentation.xlsx", help="Output workbook path")
    parser.add_argument("--tree", default="record_linkage_tree.txt", help="Output text tree path")
    parser.add_argument("--mermaid", default="record_linkage_tree.mmd", help="Output Mermaid diagram path")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    parsed = parse_package_export(args.package_export)
    if args.evaluate_export:
        parsed.evaluate_notes = parse_evaluate_export(args.evaluate_export)

    export_outputs(parsed, args.xlsx, args.tree, args.mermaid)


if __name__ == "__main__":
    main()
