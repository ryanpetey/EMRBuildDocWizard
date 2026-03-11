from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import MAIN_COLUMNS, ParsedPackage
from .xlsx_writer import write_xlsx


def _node_label(record_key: tuple[str, str, str]) -> str:
    ini, rid, name = record_key
    return f"{ini} {rid} — {name}".strip()


def build_tree(parsed: ParsedPackage) -> tuple[str, str]:
    records = parsed.records
    identity_to_key: dict[tuple[str, str], tuple[str, str, str]] = {}
    selected_root_identities: list[tuple[str, str]] = []
    edges: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)

    for record in records:
        key = record.key()
        identity = record.identity_key()
        if identity == ("", ""):
            continue
        if identity not in identity_to_key or (not identity_to_key[identity][2] and key[2]):
            identity_to_key[identity] = key
        if record.selected_flag:
            selected_root_identities.append(identity)

    for record in records:
        child_identity = record.identity_key()
        if child_identity == ("", ""):
            continue
        for parent in record.parent_links:
            parent_identity = parent.identity_key()
            if parent_identity == ("", ""):
                continue
            if parent_identity not in identity_to_key:
                identity_to_key[parent_identity] = (parent.parent_ini, parent.parent_id, parent.parent_name)
            edges[parent_identity].add(child_identity)

    if not selected_root_identities:
        selected_root_identities = [identity for identity in identity_to_key]

    lines: list[str] = []

    def walk(node_identity: tuple[str, str], depth: int, seen: set[tuple[str, str]]) -> None:
        node_key = identity_to_key[node_identity]
        prefix = "  " * depth + ("- " if depth else "")
        lines.append(f"{prefix}{_node_label(node_key)}")
        if node_identity in seen:
            lines.append("  " * (depth + 1) + "- [cycle detected]")
            return
        children = sorted(edges.get(node_identity, set()), key=lambda i: _node_label(identity_to_key[i]))
        next_seen = set(seen)
        next_seen.add(node_identity)
        for child_identity in children:
            walk(child_identity, depth + 1, next_seen)

    for root_identity in sorted(dict.fromkeys(selected_root_identities), key=lambda i: _node_label(identity_to_key[i])):
        walk(root_identity, 0, set())

    mermaid = ["graph TD"]
    for parent_identity, children in sorted(edges.items(), key=lambda kv: _node_label(identity_to_key[kv[0]])):
        parent_key = identity_to_key[parent_identity]
        parent_id = abs(hash(("p",) + parent_identity))
        mermaid.append(f'  p{parent_id}["{_node_label(parent_key)}"]')
        for child_identity in sorted(children, key=lambda i: _node_label(identity_to_key[i])):
            child_key = identity_to_key[child_identity]
            child_id = abs(hash(("c",) + child_identity))
            mermaid.append(f'  c{child_id}["{_node_label(child_key)}"]')
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
