from epic_build_doc_helper.parser import parse_evaluate_export, parse_package_export


def test_parse_package_export_sections_and_fields():
    parsed = parse_package_export("tests/fixtures/sample_package_export.txt")

    assert parsed.package_title == "Ambulatory Build Pack"
    assert parsed.package_comment.startswith("Includes scheduling")
    assert len(parsed.records) == 3

    selected = [r for r in parsed.records if r.selected_flag]
    linked = [r for r in parsed.records if r.linked_flag]

    assert len(selected) == 2
    assert len(linked) == 1

    child = next(r for r in parsed.records if r.record_id == "2001")
    assert child.parent_ini == "EAP"
    assert child.parent_id == "1001"
    assert child.parent_name == "Visit Type - Annual Wellness"


def test_parse_evaluate_export_notes():
    notes = parse_evaluate_export("tests/fixtures/sample_evaluate_export.txt")

    assert notes[("EAP", "1001", "Visit Type - Annual Wellness")].startswith("Changed")
    assert notes[("LQD", "3001", "Wellness Labs Panel")].startswith("Missing")
