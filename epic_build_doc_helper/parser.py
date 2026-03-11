from __future__ import annotations

import re
from pathlib import Path

from .models import ParentLink, ParsedPackage, Record

SECTION_SELECTED = "RECORDS"
SECTION_LINKED = "DEPENDENCIES - RECORDS"

META_PATTERNS = {
    "package_title": re.compile(r"^\s*(?:CM\s*Title|package\s+title)\s*[:=]\s*(.+)$", re.IGNORECASE),
    "package_comment": re.compile(r"^\s*(?:CM\s*Comment|package\s+comment)\s*[:=]\s*(.+)$", re.IGNORECASE),
    "ini": re.compile(r"^\s*ini\s*[:=]\s*(.+)$", re.IGNORECASE),
}

DIRECT_PARENT_INI = re.compile(r"INI\s*:\s*(\S+)", re.IGNORECASE)
DIRECT_PARENT_ID = re.compile(r"(?:ID|IEN)\s*:\s*(\S+)", re.IGNORECASE)
DIRECT_PARENT_NAME = re.compile(r"Name\s*:\s*(.+?)(?=\s+(?:DAT|Item|Line|Special\s+Handling)\s*:|$)", re.IGNORECASE)
DIRECT_PARENT_DAT = re.compile(r"DAT\s*:\s*(\S+)", re.IGNORECASE)
DIRECT_PARENT_ITEM = re.compile(r"Item\s*:\s*(\S+)", re.IGNORECASE)
DIRECT_PARENT_LINE = re.compile(r"Line\s*:\s*(\S+)", re.IGNORECASE)
DIRECT_PARENT_SPECIAL = re.compile(r"Special\s+Handling\s*:\s*(.+)$", re.IGNORECASE)
DIRECT_PARENT_PATTERN = re.compile(r"^\s*direct\s+parent\s*:", re.IGNORECASE)
INLINE_PATTERN = re.compile(r"(INI|ID|IEN|NAME|GROUP|DAT|ITEM|LINE)\s*[:=]\s*([^;|,]+)", re.IGNORECASE)
RECORD_LINE_PATTERN = re.compile(r"^\s*([A-Z0-9]+)\s*,\s*(.+?)\s*$")


def _section_from_line(line: str) -> str | None:
    normalized = line.strip().upper()
    if normalized == SECTION_SELECTED:
        return SECTION_SELECTED
    if normalized == SECTION_LINKED:
        return SECTION_LINKED
    return None


def _clean_comment_prefix(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("#"):
        stripped = stripped[1:].strip()
    return stripped


def _new_record(section: str) -> Record:
    return Record(section=section, selected_flag=section == SECTION_SELECTED, linked_flag=section == SECTION_LINKED)


def _parse_direct_parent(payload: str) -> ParentLink:
    text = _clean_comment_prefix(payload)
    if text.lower().startswith("direct parent"):
        _, text = text.split(":", 1)
    text = text.strip()

    def get(pattern: re.Pattern[str]) -> str:
        m = pattern.search(text)
        return m.group(1).strip() if m else ""

    parent_ini = get(DIRECT_PARENT_INI)
    parent_id = get(DIRECT_PARENT_ID)
    parent_name = get(DIRECT_PARENT_NAME)
    parsed = ParentLink(
        parent_ini=parent_ini,
        parent_id=parent_id,
        parent_name=parent_name,
        dat=get(DIRECT_PARENT_DAT),
        item=get(DIRECT_PARENT_ITEM),
        line=get(DIRECT_PARENT_LINE),
        special_handling=get(DIRECT_PARENT_SPECIAL),
    )

    if not any([parent_ini, parent_id, parent_name]):
        compact = re.match(r"^(?P<ini>\S+)\s+(?P<id>\S+)\s+(?P<name>.+)$", text)
        if compact:
            return ParentLink(parent_ini=compact.group("ini"), parent_id=compact.group("id"), parent_name=compact.group("name").strip())

    return parsed


def parse_package_export(path: str | Path) -> ParsedPackage:
    text = Path(path).read_text(encoding="utf-8")
    result = ParsedPackage()

    section: str | None = None
    current_record: Record | None = None

    def flush_record() -> None:
        nonlocal current_record
        if current_record and (current_record.ini or current_record.record_id or current_record.record_name):
            result.add_or_merge_record(current_record)
        current_record = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue

        commentless = _clean_comment_prefix(line)
        for meta_key, pattern in META_PATTERNS.items():
            m = pattern.match(commentless)
            if m:
                setattr(result, meta_key, m.group(1).strip())
                break

        detected = _section_from_line(commentless)
        if detected:
            flush_record()
            section = detected
            continue

        if section is None:
            continue

        if re.match(r"^\s*[-=]{3,}\s*$", commentless):
            flush_record()
            continue

        record_match = RECORD_LINE_PATTERN.match(commentless)
        if (
            not line.lstrip().startswith("#")
            and record_match
            and record_match.group(1).upper() not in {"INI", "ID", "IEN", "NAME", "GROUP", "DAT", "ITEM", "LINE"}
        ):
            flush_record()
            current_record = _new_record(section)
            current_record.ini = record_match.group(1).strip()
            current_record.record_id = record_match.group(2).strip()
            continue

        if re.match(r"^\s*record\b", commentless, re.IGNORECASE):
            flush_record()
            current_record = _new_record(section)
            continue

        if current_record is None:
            current_record = _new_record(section)

        if DIRECT_PARENT_PATTERN.match(commentless):
            parent = _parse_direct_parent(commentless)
            current_record.add_parent_link(parent)
            continue

        group_match = re.match(r"^\s*Group\s*:\s*(.+)$", commentless, re.IGNORECASE)
        if group_match:
            current_record.group = group_match.group(1).strip()
            continue

        matched = False
        for hit in INLINE_PATTERN.finditer(commentless):
            key = hit.group(1).strip().lower()
            value = hit.group(2).strip()
            matched = True
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
        if matched:
            continue

        if line.strip().startswith("#") and commentless and not re.search(r":", commentless):
            if not current_record.record_name:
                current_record.record_name = commentless
            else:
                current_record.special_handling = (
                    f"{current_record.special_handling}; {commentless}" if current_record.special_handling else commentless
                )
            continue

        current_record.special_handling = (
            f"{current_record.special_handling}; {commentless}" if current_record.special_handling else commentless
        )

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
            current_key = (key_match.group("ini").strip(), key_match.group("id").strip(), key_match.group("name").strip())
            continue

        if current_key is None:
            continue

        if re.search(r"(different|changed|missing|extra|mismatch)", line, re.IGNORECASE):
            current_note.append(line)

    flush()
    return notes
