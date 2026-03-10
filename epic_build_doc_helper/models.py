from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


MAIN_COLUMNS = [
    "Section",
    "Group",
    "INI",
    "Record ID",
    "Record Name",
    "Parent INI",
    "Parent ID",
    "Parent Name",
    "DAT",
    "Item",
    "Line",
    "Special Handling",
    "Selected Flag",
    "Linked Flag",
]


@dataclass(slots=True)
class Record:
    section: str
    group: str = ""
    ini: str = ""
    record_id: str = ""
    record_name: str = ""
    parent_ini: str = ""
    parent_id: str = ""
    parent_name: str = ""
    dat: str = ""
    item: str = ""
    line: str = ""
    special_handling: str = ""
    selected_flag: bool = False
    linked_flag: bool = False

    def key(self) -> tuple[str, str, str]:
        return self.ini.strip(), self.record_id.strip(), self.record_name.strip()

    def as_row(self) -> list[str]:
        return [
            self.section,
            self.group,
            self.ini,
            self.record_id,
            self.record_name,
            self.parent_ini,
            self.parent_id,
            self.parent_name,
            self.dat,
            self.item,
            self.line,
            self.special_handling,
            "Y" if self.selected_flag else "",
            "Y" if self.linked_flag else "",
        ]


@dataclass(slots=True)
class ParsedPackage:
    package_title: str = ""
    package_comment: str = ""
    ini: str = ""
    records: list[Record] = field(default_factory=list)
    evaluate_notes: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def add_or_merge_record(self, candidate: Record) -> None:
        key = candidate.key()
        for existing in self.records:
            if existing.key() == key and key != ("", "", ""):
                existing.selected_flag = existing.selected_flag or candidate.selected_flag
                existing.linked_flag = existing.linked_flag or candidate.linked_flag
                for attr in (
                    "group",
                    "section",
                    "record_name",
                    "parent_ini",
                    "parent_id",
                    "parent_name",
                    "dat",
                    "item",
                    "line",
                ):
                    current = getattr(existing, attr)
                    incoming = getattr(candidate, attr)
                    if not current and incoming:
                        setattr(existing, attr, incoming)
                if candidate.special_handling:
                    if existing.special_handling:
                        existing.special_handling = f"{existing.special_handling}; {candidate.special_handling}"
                    else:
                        existing.special_handling = candidate.special_handling
                return
        self.records.append(candidate)

    def apply_evaluate_notes(self) -> None:
        for record in self.records:
            note = self.evaluate_notes.get(record.key())
            if note:
                if record.special_handling:
                    record.special_handling = f"{record.special_handling}; {note}"
                else:
                    record.special_handling = note
