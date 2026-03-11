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


def test_tree_includes_all_selected_roots_and_expected_missing_children(tmp_path: Path):
    parsed = parse_package_export("tests/fixtures/cmtest.txt")
    xlsx = tmp_path / "cm.xlsx"
    tree = tmp_path / "cm_tree.txt"
    mermaid = tmp_path / "cm_tree.mmd"

    export_outputs(parsed, xlsx, tree, mermaid)

    tree_text = tree.read_text(encoding="utf-8")

    for root in [
        "CER 578060 — FMLA IB Column - Type of request",
        "CER 579395 — FMLA Response status",
        "CER 579396 — FMLA IB Sender is Epic User or PAR",
        "ELT 31391 — FMLA_approval",
        "HIC 9992021 — KPWA FMLA ACTIVITY",
        "HLX 1193226 — FMLA TYPE OF LEAVE REQUESTED CATEGORY",
    ]:
        assert root in tree_text

    # Missing examples called out by user should now appear
    assert "- HCX 2 — ENCOUNTER" in tree_text
    assert "- HFP 1550 — PATIENT" in tree_text
    assert "- HFP 42563 — SMARTDATA ELEMENT VALUE" in tree_text
    assert "- HFP 101337 — C_SMARTDATA ELEMENT VALUE" in tree_text
    assert "- HLX 1167866 — FMLA APPROVAL RESPONSE" in tree_text
    assert "- EMP 1 — EPIC, USER" in tree_text
    assert "- HFP 32408 — ATTACHED GENERAL QUESTIONNAIRES" in tree_text
    assert "- HFP 34226 — MESSAGE SENDER" in tree_text
    assert "- HFP 34230 — MYCHART MESSAGE ID" in tree_text
    assert "- HFP 100723 — C_USER_SECURITY_TEMPLATE" in tree_text
    assert "- HFP 101751 — C_USER NAME" in tree_text
    assert "- HLX 1161181 — FMLA TYPE OF REQUEST" in tree_text
    assert "- LQF 10000200 — FMLA FF QUESTIONNAIRE" in tree_text
    assert "- LPP 102504 — ENABLE FOR ALL NON-TYPE-3 ENCOUNTERS (in basket button)" in tree_text
    assert "- HLX 1067799 — FMLA" in tree_text

    # Multi-parent child should appear under each CER parent by INI+ID identity
    assert tree_text.count("- FCT 9001 — In Basket") == 3
