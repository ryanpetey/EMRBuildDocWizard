from __future__ import annotations

import re
from pathlib import Path

from .models import ParsedPackage, Record

SECTION_SELECTED = "RECORDS"
SECTION_LINKED = "DEPENDENCIES - RECORDS"

META_PATTERNS = {
    "package_title": re.compile(r"^\s*package\s+title\s*[:=]\s*(.+)$", re.IGNORECASE),
    "package_comment": re.compile(r"^\s*package\s+comment\s*[:=]\s*(.+)$", re.IGNORECASE),
    "ini": re.compile(r"^\s*ini\s*[:=]\s*(.+)$", re.IGNORECASE),
}

KEY_PATTERNS = {
    "group": re.compile(r"^\s*group\s*[:=]\s*(.+)$", re.IGNORECASE),
    "ini": re.compile(r"^\s*ini\s*[:=]\s*(.+)$", re.IGNORECASE),
    "record_id": re.compile(r"^\s*(?:record\s*)?(?:id|ien)\s*[:=]\s*(.+)$", re.IGNORECASE),
    "record_name": re.compile(r"^\s*(?:record\s*)?name\s*[:=]\s*(.+)$", re.IGNORECASE),
    "dat": re.compile(r"^\s*dat\s*[:=]\s*(.+)$", re.IGNORECASE),
    "item": re.compile(r"^\s*item\s*[:=]\s*(.+)$", re.IGNORECASE),
    "line": re.compile(r"^\s*line\s*[:=]\s*(.+)$", re.IGNORECASE),
    "special_handling": re.compile(r"^\s*special\s+handling\s*[:=]\s*(.+)$", re.IGNORECASE),
}

DIRECT_PARENT_PATTERN = re.compile(
    r"^\s*direct\s+parent\s*[:=]\s*(?P<parent_ini>[^|,;]+?)\s+"
    r"(?P<parent_id>\S+)\s+(?P<parent_name>.+)$",
    re.IGNORECASE,
)

INLINE_PATTERN = re.compile(r"(INI|ID|IEN|NAME|GROUP|DAT|ITEM|LINE)\s*[:=]\s*([^;|,]+)", re.IGNORECASE)


def _section_from_line(line: str) -> str | None:
    normalized = line.strip().upper()
    if normalized == SECTION_SELECTED:
        return SECTION_SELECTED
    if normalized == SECTION_LINKED:
        return SECTION_LINKED
    return None


def _new_record(section: str) -> Record:
    return Record(
        section=section,
        selected_flag=section == SECTION_SELECTED,
        linked_flag=section == SECTION_LINKED,
    )


def parse_package_export(path: str | Path) -> ParsedPackage:
    text = Path(path).read_text(encoding="utf-8")
    result = ParsedPackage()

    section: str | None = None
    current_record: Record | None = None

    def flush_record() -> None:
        nonlocal current_record
        if current_record and any(
            [
                current_record.ini,
                current_record.record_id,
                current_record.record_name,
                current_record.group,
                current_record.dat,
            ]
        ):
            result.add_or_merge_record(current_record)
        current_record = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        for meta_key, pattern in META_PATTERNS.items():
            m = pattern.match(line)
            if m:
                setattr(result, meta_key, m.group(1).strip())
                break

        detected = _section_from_line(line)
        if detected:
            flush_record()
            section = detected
            continue

        if section is None:
            continue

        if re.match(r"^\s*[-=]{3,}\s*$", line):
            flush_record()
            continue

        if re.match(r"^\s*record\b", line, re.IGNORECASE):
            flush_record()
            current_record = _new_record(section)

        if current_record is None:
            current_record = _new_record(section)

        parent_match = DIRECT_PARENT_PATTERN.match(line)
        if parent_match:
            current_record.parent_ini = parent_match.group("parent_ini").strip()
            current_record.parent_id = parent_match.group("parent_id").strip()
            current_record.parent_name = parent_match.group("parent_name").strip()
            continue

        matched = False
        for attr, pattern in KEY_PATTERNS.items():
            m = pattern.match(line)
            if m:
                setattr(current_record, attr, m.group(1).strip())
                matched = True
                break
        if matched:
            continue

        inline_hits = list(INLINE_PATTERN.finditer(line))
        if inline_hits:
            for hit in inline_hits:
                key = hit.group(1).strip().lower()
                value = hit.group(2).strip()
                if key == "ini":
                    current_record.ini = current_record.ini or value
                elif key in {"id", "ien"}:
                    current_record.record_id = current_record.record_id or value
                elif key == "name":
                    current_record.record_name = current_record.record_name or value
                elif key == "group":
                    current_record.group = current_record.group or value
                elif key == "dat":
                    current_record.dat = current_record.dat or value
                elif key == "item":
                    current_record.item = current_record.item or value
                elif key == "line":
                    current_record.line = current_record.line or value
            continue

        if line.strip().startswith("#"):
            continue

        if not current_record.special_handling:
            current_record.special_handling = line.strip()
        else:
            current_record.special_handling = f"{current_record.special_handling}; {line.strip()}"

    flush_record()
    return result


def parse_evaluate_export(path: str | Path) -> dict[tuple[str, str, str], str]:
    notes: dict[tuple[str, str, str], str] = {}
    text = Path(path).read_text(encoding="utf-8")

    current_key: tuple[str, str, str] | None = None
    current_note: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_note
        if current_key and current_note:
            notes[current_key] = "; ".join(current_note)
        current_key = None
        current_note = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        key_match = re.search(
            r"INI\s*[:=]\s*(?P<ini>[^;|,]+).*?(?:ID|IEN)\s*[:=]\s*(?P<id>[^;|,]+).*?NAME\s*[:=]\s*(?P<name>.+)$",
            line,
            re.IGNORECASE,
        )
        if key_match:
            flush()
            current_key = (
                key_match.group("ini").strip(),
                key_match.group("id").strip(),
                key_match.group("name").strip(),
            )
            continue

        if current_key is None:
            continue

        if re.search(r"(different|changed|missing|extra|mismatch)", line, re.IGNORECASE):
            current_note.append(line)

    flush()
    return notes
