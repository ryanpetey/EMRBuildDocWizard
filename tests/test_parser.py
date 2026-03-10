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


def test_parse_cm_style_records_and_direct_parent_fields():
    parsed = parse_package_export("tests/fixtures/cmtest.txt")

    assert parsed.package_title == "FMLA smartlist update"
    assert parsed.package_comment.startswith("T752-20029")

    selected = [r for r in parsed.records if r.selected_flag]
    linked = [r for r in parsed.records if r.linked_flag]
    assert len(selected) == 3
    assert len(linked) == 3

    e2n = next(r for r in parsed.records if r.ini == "E2N")
    assert e2n.record_name == "FMLA"
    assert len(e2n.parent_links) == 2
    assert e2n.parent_links[0].parent_ini == "HIC"
    assert e2n.parent_links[0].parent_id == "9992021"
    assert e2n.parent_links[0].parent_name == "KPWA FMLA ACTIVITY"
    assert e2n.parent_links[0].item == "830"
    assert e2n.parent_links[0].special_handling == "Item"

    emp = next(r for r in parsed.records if r.ini == "EMP")
    assert len(emp.parent_links) == 2
    assert emp.parent_links[0].dat == "99999"
    assert emp.parent_links[0].line == "1"
