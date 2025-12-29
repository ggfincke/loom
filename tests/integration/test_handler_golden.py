# tests/integration/test_handler_golden.py
# Golden tests capturing expected handler behavior for refactoring safety net
#
# These tests verify end-to-end behavior using the unified handler API.
# If these fail after refactoring, the change broke expected functionality.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.loom_io.documents import read_latex, read_typst, get_handler
from src.loom_io.latex_handler import LatexHandler
from src.loom_io.typst_handler import (
    TypstHandler,
    find_frozen_ranges,
    is_in_frozen_range,
)


# === Test Fixtures ===


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def latex_template_path(project_root: Path) -> Path:
    return project_root / "templates" / "swe-latex" / "resume.tex"


@pytest.fixture
def typst_template_path(project_root: Path) -> Path:
    return project_root / "templates" / "swe-typst" / "resume.typ"


@pytest.fixture
def latex_fixture_path(project_root: Path) -> Path:
    return (
        project_root / "tests" / "fixtures" / "documents" / "basic_formatted_resume.tex"
    )


@pytest.fixture
def typst_fixture_path(project_root: Path) -> Path:
    return (
        project_root / "tests" / "fixtures" / "documents" / "basic_formatted_resume.typ"
    )


# === LaTeX Handler Golden Tests ===


# * Golden test: LaTeX template detection
def test_latex_detect_template_golden(latex_template_path: Path):
    """Verify LaTeX template detection finds descriptor & inline marker."""
    handler = get_handler(latex_template_path)
    content = latex_template_path.read_text(encoding="utf-8")
    descriptor = handler.detect_template(latex_template_path, content)

    assert descriptor is not None
    assert descriptor.id == "swe-latex"
    assert descriptor.type == "resume"  # type is document type, not format
    assert descriptor.inline_marker == "swe-latex"
    assert descriptor.inline_only is False
    assert descriptor.source_path is not None


# * Golden test: LaTeX analysis extracts sections
def test_latex_analyze_golden(latex_template_path: Path):
    """Verify LaTeX analysis extracts expected sections."""
    handler = get_handler(latex_template_path)
    content = latex_template_path.read_text(encoding="utf-8")
    lines = read_latex(latex_template_path)
    descriptor = handler.detect_template(latex_template_path, content)
    analysis = handler.analyze(lines, descriptor)

    # Should find multiple sections
    assert len(analysis.sections) > 0

    # Verify section structure
    for section in analysis.sections:
        assert hasattr(section, "key")
        assert hasattr(section, "heading_text")
        assert hasattr(section, "start_line")
        assert hasattr(section, "end_line")
        assert hasattr(section, "confidence")
        assert section.start_line <= section.end_line
        assert section.start_line > 0

    # Verify expected section types present
    section_keys = {s.key for s in analysis.sections}
    assert len(section_keys) >= 3  # Should have at least 3 distinct sections


# * Golden test: LaTeX sections_to_payload output format
def test_latex_sections_to_payload_golden(latex_template_path: Path):
    """Verify LaTeX payload structure for AI consumption."""
    handler = get_handler(latex_template_path)
    content = latex_template_path.read_text(encoding="utf-8")
    lines = read_latex(latex_template_path)
    descriptor = handler.detect_template(latex_template_path, content)
    analysis = handler.analyze(lines, descriptor)
    payload = handler.sections_to_payload(analysis)

    # Required top-level keys
    assert "sections" in payload
    assert isinstance(payload["sections"], list)

    # Verify JSON serializable
    serialized = json.dumps(payload)
    assert len(serialized) > 0

    # Verify section structure in payload
    if payload["sections"]:
        section = payload["sections"][0]
        assert "kind" in section or "key" in section
        assert "start_line" in section
        assert "end_line" in section


# * Golden test: LaTeX edit filtering protects structural content
def test_latex_filter_edits_structural_golden():
    """Verify LaTeX edit filter drops edits on structural lines."""
    handler = LatexHandler()

    resume_lines = {
        1: "\\documentclass{article}",
        2: "\\begin{document}",
        3: "\\section{Experience}",
        4: "\\item Built software systems",
        5: "Plain content line here",
        6: "\\end{document}",
    }
    edits = {
        "version": 1,
        "meta": {},
        "ops": [
            {"op": "replace_line", "line": 1, "text": "\\documentclass{report}"},
            {"op": "replace_line", "line": 5, "text": "Updated content line"},
        ],
    }

    filtered, notes = handler.filter_edits(edits, resume_lines, descriptor=None)

    # Structural line edit (line 1) should be dropped
    remaining_lines = {op.get("line") for op in filtered["ops"]}
    assert 1 not in remaining_lines
    assert 5 in remaining_lines
    assert len(notes) > 0


# * Golden test: LaTeX edit filtering protects \\item commands
def test_latex_filter_edits_item_preservation_golden():
    """Verify LaTeX edit filter prevents \\item removal."""
    handler = LatexHandler()

    resume_lines = {
        1: "\\item Old bullet point",
        2: "Regular text line",
    }
    edits = {
        "version": 1,
        "meta": {},
        "ops": [
            {"op": "replace_line", "line": 1, "text": "No item prefix anymore"},
            {"op": "replace_line", "line": 2, "text": "Updated regular line"},
        ],
    }

    filtered, notes = handler.filter_edits(edits, resume_lines, descriptor=None)

    # Edit removing \\item should be dropped
    remaining_lines = {op.get("line") for op in filtered["ops"]}
    assert 1 not in remaining_lines
    assert 2 in remaining_lines
    assert any("\\item" in note for note in notes)


# * Golden test: LaTeX build_context integration
def test_latex_build_context_golden(latex_template_path: Path):
    """Verify build_context returns expected structure."""
    handler = get_handler(latex_template_path)
    content = latex_template_path.read_text(encoding="utf-8")
    lines = read_latex(latex_template_path)

    descriptor, analysis = handler.build_context(latex_template_path, lines, content)

    assert descriptor is not None
    assert descriptor.id == "swe-latex"
    assert len(analysis.sections) > 0
    assert isinstance(analysis.notes, list)

    # Verify payload can be generated
    payload = handler.sections_to_payload(analysis)
    assert "sections" in payload


# === Typst Handler Golden Tests ===


# * Golden test: Typst template detection
def test_typst_detect_template_golden(typst_template_path: Path):
    """Verify Typst template detection finds descriptor & inline marker."""
    handler = get_handler(typst_template_path)
    content = typst_template_path.read_text(encoding="utf-8")
    descriptor = handler.detect_template(typst_template_path, content)

    assert descriptor is not None
    assert descriptor.id == "swe-typst"
    assert descriptor.type == "resume"  # type is document type, not format
    assert descriptor.inline_marker == "swe-typst"
    assert descriptor.inline_only is False


# * Golden test: Typst analysis extracts sections
def test_typst_analyze_golden(typst_template_path: Path):
    """Verify Typst analysis extracts expected sections."""
    handler = get_handler(typst_template_path)
    content = typst_template_path.read_text(encoding="utf-8")
    lines = read_typst(typst_template_path)
    descriptor = handler.detect_template(typst_template_path, content)
    analysis = handler.analyze(lines, descriptor)

    # Should find multiple sections
    assert len(analysis.sections) > 0

    # Verify section structure
    for section in analysis.sections:
        assert hasattr(section, "key")
        assert hasattr(section, "heading_text")
        assert hasattr(section, "start_line")
        assert hasattr(section, "end_line")
        assert section.start_line <= section.end_line

    # Verify analysis has frozen_ranges (Typst-specific)
    assert analysis.frozen_ranges is not None


# * Golden test: Typst sections_to_payload output format
def test_typst_sections_to_payload_golden(typst_template_path: Path):
    """Verify Typst payload structure for AI consumption."""
    handler = get_handler(typst_template_path)
    content = typst_template_path.read_text(encoding="utf-8")
    lines = read_typst(typst_template_path)
    descriptor = handler.detect_template(typst_template_path, content)
    analysis = handler.analyze(lines, descriptor)
    payload = handler.sections_to_payload(analysis)

    # Required top-level keys
    assert "sections" in payload
    assert "section_order" in payload
    assert isinstance(payload["sections"], list)

    # Verify JSON serializable
    serialized = json.dumps(payload)
    assert len(serialized) > 0


# * Golden test: Typst edit filtering protects structural content
def test_typst_filter_edits_structural_golden():
    """Verify Typst edit filter drops edits on structural lines."""
    handler = TypstHandler()

    resume_lines = {
        1: "#set page(margin: 1in)",
        2: "#let entry(title) = { text(title) }",
        3: "= Experience",
        4: "- Built software systems",
        5: "Plain content line here",
    }
    edits = {
        "version": 1,
        "meta": {},
        "ops": [
            {"op": "replace_line", "line": 1, "text": "#set page(margin: 0.5in)"},
            {"op": "replace_line", "line": 5, "text": "Updated content line"},
        ],
    }

    filtered, notes = handler.filter_edits(edits, resume_lines, descriptor=None)

    # Structural line edit (line 1) should be dropped
    remaining_lines = {op.get("line") for op in filtered["ops"]}
    assert 1 not in remaining_lines
    assert 5 in remaining_lines


# * Golden test: Typst frozen range detection
def test_typst_frozen_ranges_golden():
    """Verify Typst frozen range detection for multiline blocks."""
    lines = {
        1: "#set page(",
        2: "  margin: 1in,",
        3: ")",
        4: "= Experience",
        5: "Content line",
    }

    ranges = find_frozen_ranges(lines)

    # Lines 1-3 form a multiline #set block
    assert len(ranges) >= 1
    assert is_in_frozen_range(1, ranges)
    assert is_in_frozen_range(2, ranges)
    assert is_in_frozen_range(3, ranges)
    assert not is_in_frozen_range(5, ranges)


# * Golden test: Typst build_context integration
def test_typst_build_context_golden(typst_template_path: Path):
    """Verify build_context returns expected structure."""
    handler = get_handler(typst_template_path)
    content = typst_template_path.read_text(encoding="utf-8")
    lines = read_typst(typst_template_path)

    descriptor, analysis = handler.build_context(typst_template_path, lines, content)

    assert descriptor is not None
    assert descriptor.id == "swe-typst"
    assert len(analysis.sections) > 0
    assert analysis.frozen_ranges is not None


# * Golden test: Typst syntax validation
def test_typst_validate_syntax_golden():
    """Verify Typst syntax validation detects balanced delimiters."""
    handler = TypstHandler()

    valid_content = """
#set page(margin: 1in)
#let entry(title) = {
  text(title)
}
= Experience
- Bullet point
"""
    assert handler.validate_syntax(valid_content) is True

    invalid_content = """
#set page(margin: 1in
= Experience
"""
    assert handler.validate_syntax(invalid_content) is False


# === Cross-Format Golden Tests ===


# * Golden test: Both handlers produce serializable payloads
def test_both_handlers_json_serializable_golden(
    latex_template_path: Path, typst_template_path: Path
):
    """Verify both handlers produce fully JSON-serializable output."""
    # LaTeX
    latex_handler = get_handler(latex_template_path)
    latex_content = latex_template_path.read_text(encoding="utf-8")
    latex_lines = read_latex(latex_template_path)
    latex_desc = latex_handler.detect_template(latex_template_path, latex_content)
    latex_analysis = latex_handler.analyze(latex_lines, latex_desc)
    latex_data = latex_handler.sections_to_payload(latex_analysis)

    # Typst
    typst_handler = get_handler(typst_template_path)
    typst_content = typst_template_path.read_text(encoding="utf-8")
    typst_lines = read_typst(typst_template_path)
    typst_desc = typst_handler.detect_template(typst_template_path, typst_content)
    typst_analysis = typst_handler.analyze(typst_lines, typst_desc)
    typst_data = typst_handler.sections_to_payload(typst_analysis)

    # Both should serialize without error
    json.dumps(latex_data)
    json.dumps(typst_data)

    # Both should have sections
    assert len(latex_data["sections"]) > 0
    assert len(typst_data["sections"]) > 0


# * Golden test: Generic fixture files also work
def test_generic_fixtures_work_golden(
    latex_fixture_path: Path, typst_fixture_path: Path
):
    """Verify handlers work on generic fixtures without template descriptors."""
    # LaTeX fixture (no template descriptor)
    latex_handler = get_handler(latex_fixture_path)
    latex_lines = read_latex(latex_fixture_path)
    latex_analysis = latex_handler.analyze(latex_lines, descriptor=None)
    assert len(latex_analysis.sections) > 0

    # Typst fixture (no template descriptor)
    typst_handler = get_handler(typst_fixture_path)
    typst_lines = read_typst(typst_fixture_path)
    typst_analysis = typst_handler.analyze(typst_lines, descriptor=None)
    assert len(typst_analysis.sections) > 0
