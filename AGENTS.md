# AGENTS.md

Project: Epic Build Documentation Helper

Purpose:
Parse Epic Content Management package exports and generate:
- Excel workbook
- record linkage tree
- Mermaid diagram

Development rules:

When making code changes:

1. Run tests:
python -m pytest -q

2. Validate CLI against the cmtest fixture:
python -m epic_build_doc_helper.cli tests/fixtures/cmtest.txt --xlsx cmtest_output.xlsx --tree cmtest_tree.txt --mermaid cmtest_tree.mmd

3. The CLI must complete without errors.

4. The generated tree must contain these root records:
CER 578060
CER 579395
CER 579396
ELT 31391
HIC 9992021
HLX 1193226

5. Do not introduce unused imports or undefined constants.

6. Parser logic must tolerate missing DAT / Item / Line fields.

7. Prefer fixing the parser model rather than patching output code.

8. Ensure parser.py, models.py, exporter.py, and cli.py remain consistent.
