from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import MAIN_COLUMNS, ParsedPackage, Record
from .xlsx_writer import write_xlsx


def _node_label(record_key: tuple[str, str, str]) -> str:
    ini, rid, name = record_key
    return f"{ini} {rid} — {name}".strip()


def build_tree(parsed: ParsedPackage) -> tuple[str, str]:
    records = parsed.records
    key_to_record: dict[tuple[str, str, str], Record] = {}
    selected_roots: list[tuple[str, str, str]] = []
    edges: dict[tuple[str, str, str], set[tuple[str, str, str]]] = defaultdict(set)

    for record in records:
        key = record.key()
        if key == ("", "", ""):
            continue
        key_to_record[key] = record
        if record.selected_flag:
            selected_roots.append(key)

    for record in records:
        child_key = record.key()
        if child_key == ("", "", ""):
            continue
        for parent in record.parent_links:
            parent_key = parent.key()
            if parent_key == ("", "", ""):
                continue
            if parent_key not in key_to_record:
                key_to_record[parent_key] = Record(
                    section="PARENT-ONLY",
                    ini=parent.parent_ini,
                    record_id=parent.parent_id,
                    record_name=parent.parent_name,
                )
            edges[parent_key].add(child_key)

    if not selected_roots:
        selected_roots = [k for k, r in key_to_record.items() if r.selected_flag]
    if not selected_roots:
        selected_roots = sorted(key_to_record)

    lines: list[str] = []

    def walk(node: tuple[str, str, str], depth: int, seen: set[tuple[str, str, str]]) -> None:
        prefix = "  " * depth + ("- " if depth else "")
        lines.append(f"{prefix}{_node_label(node)}")
        if node in seen:
            lines.append("  " * (depth + 1) + "- [cycle detected]")
            return
        children = sorted(edges.get(node, set()), key=_node_label)
        next_seen = set(seen)
        next_seen.add(node)
        for child in children:
            walk(child, depth + 1, next_seen)

    for root in sorted(dict.fromkeys(selected_roots), key=_node_label):
        walk(root, 0, set())

    mermaid = ["graph TD"]
    for parent, children in sorted(edges.items(), key=lambda kv: _node_label(kv[0])):
        parent_id = abs(hash(("p",) + parent))
        mermaid.append(f'  p{parent_id}["{_node_label(parent)}"]')
        for child in sorted(children, key=_node_label):
            child_id = abs(hash(("c",) + child))
            mermaid.append(f'  c{child_id}["{_node_label(child)}"]')
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
                ["Records with Direct Parent", sum(1 for r in parsed.records if r.parent_links)],
                ["Records with Special Handling", sum(1 for r in parsed.records if r.special_handling)],
            ],
        ),
    ]

    write_xlsx(xlsx_path, sheets)

    tree_text, mermaid = build_tree(parsed)
    Path(tree_path).write_text(tree_text, encoding="utf-8")
    Path(mermaid_path).write_text(mermaid, encoding="utf-8")
