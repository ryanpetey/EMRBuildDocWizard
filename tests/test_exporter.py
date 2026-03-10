from pathlib import Path
from zipfile import ZipFile

from epic_build_doc_helper.exporter import export_outputs
from epic_build_doc_helper.parser import parse_evaluate_export, parse_package_export


def test_export_outputs_creates_expected_artifacts(tmp_path: Path):
    parsed = parse_package_export("tests/fixtures/sample_package_export.txt")
    parsed.evaluate_notes = parse_evaluate_export("tests/fixtures/sample_evaluate_export.txt")

    xlsx = tmp_path / "output.xlsx"
    tree = tmp_path / "tree.txt"
    mermaid = tmp_path / "tree.mmd"

    export_outputs(parsed, xlsx, tree, mermaid)

    assert xlsx.exists()
    assert tree.exists()
    assert mermaid.exists()

    with ZipFile(xlsx) as zf:
        workbook_xml = zf.read("xl/workbook.xml").decode("utf-8")
        summary_xml = zf.read("xl/worksheets/sheet5.xml").decode("utf-8")

    assert "Package Summary" in workbook_xml
    assert "Selected Records" in workbook_xml
    assert "Linked Records" in workbook_xml
    assert "Delivery View" in workbook_xml
    assert "Summary" in workbook_xml

    assert "Total Records" in summary_xml
    assert ">3<" in summary_xml

    linked_text = tree.read_text(encoding="utf-8")
    assert "EAP 1001 — Visit Type - Annual Wellness" in linked_text

    mermaid_text = mermaid.read_text(encoding="utf-8")
    assert mermaid_text.startswith("graph TD")


def test_tree_uses_selected_roots_and_parent_links(tmp_path: Path):
    parsed = parse_package_export("tests/fixtures/cmtest.txt")
    xlsx = tmp_path / "cm.xlsx"
    tree = tmp_path / "cm_tree.txt"
    mermaid = tmp_path / "cm_tree.mmd"

    export_outputs(parsed, xlsx, tree, mermaid)

    tree_text = tree.read_text(encoding="utf-8")

    assert tree_text.splitlines()[0] == "CER 578060 — FMLA IB Column - Type of request"
    assert "HIC 9992021 — KPWA FMLA ACTIVITY" in tree_text
    assert "- E2N 2100156400 — FMLA" in tree_text
    assert tree_text.count("E2N 2100156400 — FMLA") == 1
    assert "- FCT 9001 — In Basket" in tree_text
    assert "- EMP PETERX1 — PETERSON, RYAN" in tree_text
