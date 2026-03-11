# Epic Build Documentation Helper (v1 Prototype)

Local Python CLI prototype for transforming Epic export text files into:

1. An Excel workbook with tabs:
   - Package Summary
   - Selected Records
   - Linked Records
   - Delivery View
   - Summary
2. Record linkage outputs:
   - Text tree
   - Mermaid diagram

## Features

- Parses Epic CM package export text file
- Optionally parses Epic Evaluate Records differences export
- Extracts fields where present:
  - package title/comment
  - INI
  - record ID/name
  - group
  - direct parent fields (INI/ID/name)
  - DAT, item, line
  - special handling
- Produces main columns:
  - Section, Group, INI, Record ID, Record Name, Parent INI, Parent ID, Parent Name,
    DAT, Item, Line, Special Handling, Selected Flag, Linked Flag

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Usage

```bash
epic-doc-helper tests/fixtures/sample_package_export.txt \
  --evaluate-export tests/fixtures/sample_evaluate_export.txt \
  --xlsx out.xlsx \
  --tree linkage.txt \
  --mermaid linkage.mmd
```

## Architecture

- `epic_build_doc_helper/parser.py`: parsing only
- `epic_build_doc_helper/exporter.py`: workbook + tree/mermaid output only
- `epic_build_doc_helper/cli.py`: CLI wiring layer

This separation is intended to make a future Excel add-in wrapper straightforward.

## Tests

```bash
pytest
```
