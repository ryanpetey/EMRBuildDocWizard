from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import MAIN_COLUMNS, ParsedPackage, Record
from .xlsx_writer import write_xlsx


def build_tree(records: list[Record]) -> tuple[str, str]:
    parent_map: dict[tuple[str, str, str], list[tuple[str, str, str]]] = defaultdict(list)
    all_keys: dict[tuple[str, str, str], Record] = {}

    for record in records:
        key = record.key()
        if key == ("", "", ""):
            continue
        all_keys[key] = record
        if record.parent_ini or record.parent_id or record.parent_name:
            parent = (record.parent_ini.strip(), record.parent_id.strip(), record.parent_name.strip())
            parent_map[parent].append(key)

    child_nodes = {child for children in parent_map.values() for child in children}
    roots = [key for key in all_keys if key not in child_nodes]
    if not roots:
        roots = list(all_keys.keys())

    def display(key: tuple[str, str, str]) -> str:
        ini, rid, name = key
        return f"{ini} {rid} {name}".strip()

    lines: list[str] = []

    def walk(node: tuple[str, str, str], depth: int = 0, seen: set[tuple[str, str, str]] | None = None) -> None:
        local_seen = set() if seen is None else set(seen)
        prefix = "  " * depth + ("- " if depth else "")
        lines.append(f"{prefix}{display(node)}")
        if node in local_seen:
            lines.append("  " * (depth + 1) + "- [cycle detected]")
            return
        local_seen.add(node)
        for child in sorted(parent_map.get(node, []), key=lambda x: display(x)):
            walk(child, depth + 1, local_seen)

    for root in sorted(roots, key=lambda x: display(x)):
        walk(root)

    mermaid = ["graph TD"]
    for parent, children in parent_map.items():
        parent_id = abs(hash(parent))
        mermaid.append(f'  p{parent_id}["{display(parent)}"]')
        for child in children:
            child_id = abs(hash(child))
            mermaid.append(f'  c{child_id}["{display(child)}"]')
            mermaid.append(f"  p{parent_id} --> c{child_id}")

    return "\n".join(lines) + "\n", "\n".join(dict.fromkeys(mermaid)) + "\n"


def export_outputs(parsed: ParsedPackage, xlsx_path: str | Path, tree_path: str | Path, mermaid_path: str | Path) -> None:
    parsed.apply_evaluate_notes()

    selected = [record for record in parsed.records if record.selected_flag]
    linked = [record for record in parsed.records if record.linked_flag]
    delivery = sorted(parsed.records, key=lambda r: (r.section, r.group, r.ini, r.record_id, r.record_name))

    sheets: list[tuple[str, list[list[object]]]] = [
        (
            "Package Summary",
            [
                ["Field", "Value"],
                ["Package Title", parsed.package_title],
                ["Package Comment", parsed.package_comment],
                ["INI", parsed.ini],
            ],
        ),
        ("Selected Records", [MAIN_COLUMNS] + [r.as_row() for r in selected]),
        ("Linked Records", [MAIN_COLUMNS] + [r.as_row() for r in linked]),
        ("Delivery View", [MAIN_COLUMNS] + [r.as_row() for r in delivery]),
        (
            "Summary",
            [
                ["Metric", "Value"],
                ["Total Records", len(parsed.records)],
                ["Selected Records", len(selected)],
                ["Linked Records", len(linked)],
                ["Records with Direct Parent", sum(1 for r in parsed.records if r.parent_id or r.parent_name)],
                ["Records with Special Handling", sum(1 for r in parsed.records if r.special_handling)],
            ],
        ),
    ]

    write_xlsx(xlsx_path, sheets)

    tree_text, mermaid = build_tree(parsed.records)
    Path(tree_path).write_text(tree_text, encoding="utf-8")
    Path(mermaid_path).write_text(mermaid, encoding="utf-8")
