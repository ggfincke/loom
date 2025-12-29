# tests/unit/loom_io/test_template_io.py
# Unit tests for shared template loading utilities

import re
from pathlib import Path

import pytest

from src.loom_io.template_io import (
    TEMPLATE_FILENAME,
    TemplateDescriptor,
    TemplateSectionRule,
    FrozenRules,
    find_template_descriptor_path,
    load_descriptor,
    detect_inline_marker,
)
from src.core.exceptions import TemplateNotFoundError, TemplateParseError


# * Test find_template_descriptor_path finds template in same directory
def test_find_template_descriptor_path_finds_in_same_dir(tmp_path):
    resume = tmp_path / "resume.tex"
    resume.write_text("content")
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text('[template]\nid = "test"\ntype = "resume"')

    result = find_template_descriptor_path(resume)
    assert result == template


# * Test find_template_descriptor_path finds template in parent directory
def test_find_template_descriptor_path_finds_in_parent(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    resume = subdir / "resume.tex"
    resume.write_text("content")
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text('[template]\nid = "test"\ntype = "resume"')

    result = find_template_descriptor_path(resume)
    assert result == template


# * Test find_template_descriptor_path finds template in grandparent directory
def test_find_template_descriptor_path_finds_in_grandparent(tmp_path):
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)
    resume = subdir / "resume.tex"
    resume.write_text("content")
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text('[template]\nid = "test"\ntype = "resume"')

    result = find_template_descriptor_path(resume)
    assert result == template


# * Test find_template_descriptor_path returns None when no template exists
def test_find_template_descriptor_path_returns_none_when_missing(tmp_path):
    resume = tmp_path / "resume.tex"
    resume.write_text("content")

    result = find_template_descriptor_path(resume)
    assert result is None


# * Test load_descriptor parses valid TOML correctly
def test_load_descriptor_parses_valid_toml(tmp_path):
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text(
        """
[template]
id = "my-template"
type = "resume"
name = "My Template"
version = "1.0"

[sections.experience]
pattern = "Experience"
pattern_type = "literal"
kind = "experience"
split_items = true

[frozen]
patterns = ["\\\\header"]
"""
    )

    result = load_descriptor(template)

    assert result.id == "my-template"
    assert result.type == "resume"
    assert result.name == "My Template"
    assert result.version == "1.0"
    assert "experience" in result.sections
    assert result.sections["experience"].split_items is True
    assert result.frozen.patterns == ["\\header"]


# * Test load_descriptor raises TemplateNotFoundError for missing file
def test_load_descriptor_raises_on_missing_file(tmp_path):
    missing = tmp_path / "nonexistent.toml"

    with pytest.raises(TemplateNotFoundError) as exc_info:
        load_descriptor(missing)

    assert "not found" in str(exc_info.value).lower()


# * Test load_descriptor raises TemplateParseError for invalid TOML
def test_load_descriptor_raises_on_invalid_toml(tmp_path):
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text("this is not valid toml [[[")

    with pytest.raises(TemplateParseError) as exc_info:
        load_descriptor(template)

    assert "invalid toml" in str(exc_info.value).lower()


# * Test load_descriptor raises TemplateParseError when required fields missing
def test_load_descriptor_raises_on_missing_required_fields(tmp_path):
    # Missing template.type
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text('[template]\nid = "test"')

    with pytest.raises(TemplateParseError) as exc_info:
        load_descriptor(template)

    assert "missing required" in str(exc_info.value).lower()


# * Test load_descriptor handles empty sections gracefully
def test_load_descriptor_handles_empty_sections(tmp_path):
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text('[template]\nid = "test"\ntype = "resume"')

    result = load_descriptor(template)

    assert result.sections == {}
    assert result.frozen.paths == []
    assert result.frozen.patterns == []


# * Test load_descriptor preserves inline_marker
def test_load_descriptor_preserves_inline_marker(tmp_path):
    template = tmp_path / TEMPLATE_FILENAME
    template.write_text('[template]\nid = "test"\ntype = "resume"')

    result = load_descriptor(template, inline_marker="my-marker")

    assert result.inline_marker == "my-marker"


# * Test detect_inline_marker with LaTeX pattern
def test_detect_inline_marker_with_latex_pattern():
    content = """
\\documentclass{article}
% loom-template: swe-latex
\\begin{document}
"""
    pattern = re.compile(r"%\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)")

    result = detect_inline_marker(content, pattern)

    assert result == "swe-latex"


# * Test detect_inline_marker with Typst pattern
def test_detect_inline_marker_with_typst_pattern():
    content = """
// loom-template: swe-typst
#set page(margin: 1in)
"""
    pattern = re.compile(
        r"(?://|/\*)\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)", re.IGNORECASE
    )

    result = detect_inline_marker(content, pattern)

    assert result == "swe-typst"


# * Test detect_inline_marker with block comment
def test_detect_inline_marker_with_block_comment():
    content = """
/* loom-template: my-template */
#set page(margin: 1in)
"""
    pattern = re.compile(
        r"(?://|/\*)\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)", re.IGNORECASE
    )

    result = detect_inline_marker(content, pattern)

    assert result == "my-template"


# * Test detect_inline_marker returns None when no marker present
def test_detect_inline_marker_returns_none_without_marker():
    content = """
\\documentclass{article}
\\begin{document}
"""
    pattern = re.compile(r"%\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)")

    result = detect_inline_marker(content, pattern)

    assert result is None


# * Test detect_inline_marker respects max_lines
def test_detect_inline_marker_respects_max_lines():
    content = """Line 1
Line 2
Line 3
% loom-template: should-not-find
"""
    pattern = re.compile(r"%\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)")

    # Marker is on line 4, but we only search first 3 lines
    result = detect_inline_marker(content, pattern, max_lines=3)

    assert result is None


# * Test detect_inline_marker finds marker within max_lines
def test_detect_inline_marker_finds_within_max_lines():
    content = """% loom-template: found-it
Line 2
Line 3
Line 4
"""
    pattern = re.compile(r"%\s*loom-template:\s*(?P<id>[A-Za-z0-9_\-]+)")

    result = detect_inline_marker(content, pattern, max_lines=3)

    assert result == "found-it"


# * Test TemplateSectionRule defaults
def test_template_section_rule_defaults():
    rule = TemplateSectionRule(key="test", pattern="Test")

    assert rule.pattern_type == "literal"
    assert rule.kind is None
    assert rule.split_items is False
    assert rule.optional is True


# * Test FrozenRules defaults
def test_frozen_rules_defaults():
    rules = FrozenRules()

    assert rules.paths == []
    assert rules.patterns == []


# * Test TemplateDescriptor inline_only flag
def test_template_descriptor_inline_only_flag():
    desc = TemplateDescriptor(
        id="test",
        type="resume",
        name=None,
        version=None,
        sections={},
        frozen=FrozenRules(),
        custom={},
        inline_only=True,
    )

    assert desc.inline_only is True
