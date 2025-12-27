# tests/unit/loom_io/test_typst_handler.py
# Unit tests for Typst handler utilities & template metadata integration

from pathlib import Path
import json

from src.loom_io.typst_handler import (
    analyze_typst,
    filter_typst_edits,
    detect_template,
    sections_to_payload,
    find_frozen_ranges,
    is_in_frozen_range,
    validate_basic_typst_syntax,
    build_typst_context,
)
from src.loom_io.documents import read_typst


# * Verify generic Typst analysis detects expected sections
def test_analyze_typst_detects_core_sections():
    root = Path(__file__).resolve().parents[3]
    fixtures_dir = root / "tests" / "fixtures" / "documents"
    sample_path = fixtures_dir / "basic_formatted_resume.typ"
    lines = read_typst(sample_path)

    analysis = analyze_typst(lines, descriptor=None)
    section_keys = {section.key for section in analysis.sections}

    assert "experience" in section_keys
    assert "skills" in section_keys
    assert "education" in section_keys


# * Ensure Typst edit filter drops structural changes
def test_filter_typst_edits_enforces_structural_preservation():
    resume_lines = {
        1: "#set page(margin: 1in)",
        2: "#let entry(title) = { ... }",
        3: "= Experience",
        4: "- Old bullet",
        5: "Plain content line",
    }
    edits = {
        "version": 1,
        "meta": {},
        "ops": [
            {"op": "replace_line", "line": 1, "text": "#set page(margin: 0.5in)"},
            {"op": "replace_line", "line": 4, "text": "- New bullet text"},
            {"op": "replace_line", "line": 5, "text": "Updated content"},
        ],
    }

    filtered, notes = filter_typst_edits(edits, resume_lines, descriptor=None)

    # Structural lines (1 and 2) should be skipped - filtered as "frozen" or "structural"
    assert any("frozen" in note.lower() or "structural" in note.lower() for note in notes)
    # Non-structural lines should pass through
    remaining_lines = [op.get("line") for op in filtered["ops"]]
    assert 5 in remaining_lines  # content line should pass
    assert 1 not in remaining_lines  # structural line should be filtered


# * Detect template descriptor & inline marker from bundled template
def test_detect_template_uses_descriptor_and_inline_marker():
    root = Path(__file__).resolve().parents[3]
    template_resume = (root / "templates" / "swe-typst" / "resume.typ").resolve()
    content = template_resume.read_text(encoding="utf-8")

    descriptor = detect_template(template_resume, content)
    assert descriptor is not None
    assert descriptor.id == "swe-typst"
    assert descriptor.inline_marker == "swe-typst"

    lines = read_typst(template_resume)
    analysis = analyze_typst(lines, descriptor)
    payload = sections_to_payload(analysis)

    assert payload["template_id"] == "swe-typst"
    assert "sections" in payload
    json.dumps(payload)  # validate JSON serializable


# * Test frozen range detection
def test_find_frozen_ranges_detects_multiline_blocks():
    lines = {
        1: "#set page(",
        2: "  margin: 1in,",
        3: ")",
        4: "= Experience",
        5: "Content",
    }

    ranges = find_frozen_ranges(lines)
    assert len(ranges) >= 1
    # First frozen range should cover lines 1-3
    assert (1, 3) in ranges


def test_is_in_frozen_range():
    frozen_ranges = [(1, 3), (10, 15)]
    assert is_in_frozen_range(1, frozen_ranges)
    assert is_in_frozen_range(2, frozen_ranges)
    assert is_in_frozen_range(3, frozen_ranges)
    assert not is_in_frozen_range(4, frozen_ranges)
    assert is_in_frozen_range(12, frozen_ranges)
    assert not is_in_frozen_range(9, frozen_ranges)


# * Test basic syntax validation
def test_validate_basic_typst_syntax_balanced():
    valid_typst = """
#set page(margin: 1in)
#let entry(title) = {
  text(title)
}
= Experience
- Bullet point
"""
    assert validate_basic_typst_syntax(valid_typst)


def test_validate_basic_typst_syntax_unbalanced():
    # Missing closing parenthesis
    invalid_typst = """
#set page(margin: 1in
= Experience
"""
    assert not validate_basic_typst_syntax(invalid_typst)


def test_validate_basic_typst_syntax_unterminated_string():
    invalid_typst = """
#let name = "John Doe
= Experience
"""
    assert not validate_basic_typst_syntax(invalid_typst)


def test_validate_basic_typst_syntax_with_comments():
    # Comments should be ignored
    valid_typst = """
// This is a comment
#set page(margin: 1in)
/* Block comment */
= Experience
"""
    assert validate_basic_typst_syntax(valid_typst)


# * Test build_typst_context integration
def test_build_typst_context_returns_analysis():
    root = Path(__file__).resolve().parents[3]
    template_resume = (root / "templates" / "swe-typst" / "resume.typ").resolve()
    text = template_resume.read_text(encoding="utf-8")
    lines = read_typst(template_resume)

    descriptor, analysis = build_typst_context(template_resume, lines, text)

    assert descriptor is not None
    assert descriptor.id == "swe-typst"
    assert len(analysis.sections) > 0
    assert analysis.frozen_ranges is not None


# * Test sections_to_payload output format
def test_sections_to_payload_format():
    root = Path(__file__).resolve().parents[3]
    fixtures_dir = root / "tests" / "fixtures" / "documents"
    sample_path = fixtures_dir / "basic_formatted_resume.typ"
    lines = read_typst(sample_path)
    analysis = analyze_typst(lines, descriptor=None)

    payload = sections_to_payload(analysis)

    assert "sections" in payload
    assert "section_order" in payload
    assert "notes" in payload
    assert isinstance(payload["sections"], list)
    assert isinstance(payload["section_order"], list)

    # Verify section structure
    if payload["sections"]:
        section = payload["sections"][0]
        assert "kind" in section
        assert "start_line" in section
        assert "end_line" in section


# * Test filter_typst_edits with frozen ranges
def test_filter_typst_edits_respects_frozen_ranges():
    resume_lines = {
        1: "#set page(",
        2: "  margin: 1in,",
        3: ")",
        4: "= Experience",
        5: "Plain content line",
    }
    frozen_ranges = [(1, 3)]
    edits = {
        "version": 1,
        "meta": {},
        "ops": [
            {"op": "replace_line", "line": 2, "text": "  margin: 0.5in,"},  # In frozen range
            {"op": "replace_line", "line": 5, "text": "Updated content"},  # Not frozen
        ],
    }

    filtered, notes = filter_typst_edits(
        edits, resume_lines, descriptor=None, frozen_ranges=frozen_ranges
    )

    # Edit at line 2 should be skipped (frozen range)
    assert any("frozen" in note.lower() for note in notes)
    # Edit at line 5 should pass through
    remaining_lines = [op["line"] for op in filtered["ops"]]
    assert 5 in remaining_lines
    assert 2 not in remaining_lines
