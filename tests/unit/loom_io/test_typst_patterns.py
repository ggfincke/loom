# tests/unit/loom_io/test_typst_patterns.py
# Unit tests for Typst pattern constants & helper functions

import pytest

from src.loom_io.typst_patterns import (
    STRUCTURAL_PREFIXES,
    SECTION_HEADING_RE,
    ENTRY_FUNC_PATTERNS,
    BULLET_PATTERNS,
    SEMANTIC_MATCHERS,
    is_structural_prefix,
    is_section_heading,
    is_entry_function,
    is_bullet_line,
    is_comment_line,
    is_structural_line,
    is_preservable_content,
    requires_trailing_blank,
    count_delimiters,
    strip_trailing_comment,
    strip_string_literals,
    infer_section_kind,
)


class TestStructuralPrefixes:
    # * Test STRUCTURAL_PREFIXES contains expected Typst commands
    def test_contains_set(self):
        assert "#set" in STRUCTURAL_PREFIXES

    def test_contains_show(self):
        assert "#show" in STRUCTURAL_PREFIXES

    def test_contains_import(self):
        assert "#import" in STRUCTURAL_PREFIXES

    def test_contains_let(self):
        assert "#let" in STRUCTURAL_PREFIXES

    def test_contains_include(self):
        assert "#include" in STRUCTURAL_PREFIXES


class TestSectionHeadingRegex:
    # * Test SECTION_HEADING_RE matches level 1 headings
    def test_matches_level1(self):
        match = SECTION_HEADING_RE.match("= Experience")
        assert match is not None
        assert match.group(1) == "="
        assert match.group(2) == "Experience"

    # * Test SECTION_HEADING_RE matches level 2 headings
    def test_matches_level2(self):
        match = SECTION_HEADING_RE.match("== Software Engineer")
        assert match is not None
        assert match.group(1) == "=="
        assert match.group(2) == "Software Engineer"

    # * Test SECTION_HEADING_RE matches level 3 headings
    def test_matches_level3(self):
        match = SECTION_HEADING_RE.match("=== Details")
        assert match is not None
        assert match.group(1) == "==="

    # * Test SECTION_HEADING_RE handles whitespace
    def test_handles_whitespace(self):
        match = SECTION_HEADING_RE.match("=  Education  ")
        assert match is not None
        # whitespace preserved in title match
        assert "Education" in match.group(2)

    # * Test SECTION_HEADING_RE does not match non-headings
    def test_no_match_for_non_heading(self):
        assert SECTION_HEADING_RE.match("Regular text") is None
        assert SECTION_HEADING_RE.match("#set page(margin: 1in)") is None


class TestEntryFuncPatterns:
    # * Test ENTRY_FUNC_PATTERNS detect #edu
    def test_detects_edu(self):
        assert any(p.search("#edu(") for p in ENTRY_FUNC_PATTERNS)
        assert any(p.search("#edu (") for p in ENTRY_FUNC_PATTERNS)

    # * Test ENTRY_FUNC_PATTERNS detect #work
    def test_detects_work(self):
        assert any(p.search("#work(") for p in ENTRY_FUNC_PATTERNS)

    # * Test ENTRY_FUNC_PATTERNS detect #project
    def test_detects_project(self):
        assert any(p.search("#project(") for p in ENTRY_FUNC_PATTERNS)

    # * Test ENTRY_FUNC_PATTERNS detect #entry
    def test_detects_entry(self):
        assert any(p.search("#entry(") for p in ENTRY_FUNC_PATTERNS)

    # * Test ENTRY_FUNC_PATTERNS don't match arbitrary text
    def test_no_false_positives(self):
        assert not any(p.search("education") for p in ENTRY_FUNC_PATTERNS)
        assert not any(p.search("#set") for p in ENTRY_FUNC_PATTERNS)


class TestBulletPatterns:
    # * Test BULLET_PATTERNS detect dash bullets
    def test_detects_dash_bullet(self):
        assert any(p.match("- Bullet point") for p in BULLET_PATTERNS)
        assert any(p.match("  - Indented bullet") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS detect plus bullets
    def test_detects_plus_bullet(self):
        assert any(p.match("+ Bullet point") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS detect numbered lists
    def test_detects_numbered_list(self):
        assert any(p.match("1. First item") for p in BULLET_PATTERNS)
        assert any(p.match("10. Tenth item") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS don't match non-bullets
    def test_no_false_positives(self):
        assert not any(p.match("Regular text") for p in BULLET_PATTERNS)
        assert not any(p.match("-without space") for p in BULLET_PATTERNS)


class TestSemanticMatchers:
    # * Test education matcher
    def test_education_matcher(self):
        assert SEMANTIC_MATCHERS["education"].search("Education")
        assert SEMANTIC_MATCHERS["education"].search("EDUCATION")
        assert SEMANTIC_MATCHERS["education"].search("Academic Background")
        assert not SEMANTIC_MATCHERS["education"].search("Work Experience")

    # * Test experience matcher
    def test_experience_matcher(self):
        assert SEMANTIC_MATCHERS["experience"].search("Experience")
        assert SEMANTIC_MATCHERS["experience"].search("Work History")
        assert SEMANTIC_MATCHERS["experience"].search("Employment")
        assert not SEMANTIC_MATCHERS["experience"].search("Education")

    # * Test skills matcher
    def test_skills_matcher(self):
        assert SEMANTIC_MATCHERS["skills"].search("Skills")
        assert SEMANTIC_MATCHERS["skills"].search("Technical Skills")
        assert SEMANTIC_MATCHERS["skills"].search("Technologies")

    # * Test projects matcher
    def test_projects_matcher(self):
        assert SEMANTIC_MATCHERS["projects"].search("Projects")
        assert SEMANTIC_MATCHERS["projects"].search("Personal Projects")

    # * Test summary matcher
    def test_summary_matcher(self):
        assert SEMANTIC_MATCHERS["summary"].search("Summary")
        assert SEMANTIC_MATCHERS["summary"].search("Professional Summary")
        assert SEMANTIC_MATCHERS["summary"].search("Objective")


class TestStructuralChecks:
    # * Test is_structural_prefix identifies Typst commands
    def test_structural_prefix_set(self):
        assert is_structural_prefix("#set page(margin: 1in)")

    def test_structural_prefix_show(self):
        assert is_structural_prefix("#show heading: it => text(blue)")

    def test_structural_prefix_import(self):
        assert is_structural_prefix('#import "template.typ": *')

    def test_structural_prefix_let(self):
        assert is_structural_prefix("#let name(content) = {}")

    def test_structural_prefix_with_whitespace(self):
        assert is_structural_prefix('  #set text(font: "Arial")')

    def test_structural_prefix_rejects_non_structural(self):
        assert not is_structural_prefix("Regular text")
        assert not is_structural_prefix("= Heading")
        assert not is_structural_prefix("- Bullet")


class TestSectionHeadingFunction:
    # * Test is_section_heading returns level and title
    def test_returns_level_and_title(self):
        result = is_section_heading("= Experience")
        assert result is not None
        level, title = result
        assert level == 1
        assert title == "Experience"

    def test_level2_heading(self):
        result = is_section_heading("== Software Engineer")
        assert result is not None
        level, title = result
        assert level == 2
        assert title == "Software Engineer"

    def test_returns_none_for_non_heading(self):
        assert is_section_heading("Regular text") is None
        assert is_section_heading("#set page()") is None
        assert is_section_heading("") is None


class TestEntryFunctionDetection:
    # * Test is_entry_function detects entry functions
    def test_detects_entry_functions(self):
        assert is_entry_function("#work(")
        assert is_entry_function("#edu(")
        assert is_entry_function("#project(")
        assert is_entry_function("#entry(")

    def test_rejects_non_entry(self):
        assert not is_entry_function("#set")
        assert not is_entry_function("= Education")
        assert not is_entry_function("work")


class TestBulletLineDetection:
    # * Test is_bullet_line detects bullets
    def test_detects_bullet_lines(self):
        assert is_bullet_line("- First bullet")
        assert is_bullet_line("+ Second bullet")
        assert is_bullet_line("1. Numbered item")

    def test_rejects_non_bullets(self):
        assert not is_bullet_line("Regular text")
        assert not is_bullet_line("= Heading")


class TestCommentDetection:
    # * Test is_comment_line detects comments
    def test_detects_comments(self):
        assert is_comment_line("// This is a comment")
        assert is_comment_line("  // Indented comment")

    def test_rejects_non_comments(self):
        assert not is_comment_line("Regular text")
        assert not is_comment_line("= Heading")
        assert not is_comment_line("/* block comment */")  # only // is line comment


class TestDelimiterCounting:
    # * Test count_delimiters counts balanced delimiters
    def test_counts_parentheses(self):
        assert count_delimiters("(a, b)") == 0  # balanced
        assert count_delimiters("(a, (b, c)") == 1  # one unbalanced open
        assert count_delimiters(")") == -1  # one unbalanced close

    def test_counts_brackets(self):
        assert count_delimiters("[a, b]") == 0
        assert count_delimiters("[[nested]]") == 0

    def test_counts_braces(self):
        assert count_delimiters("{a, b}") == 0
        assert count_delimiters("{nested {item}}") == 0

    def test_ignores_strings(self):
        # delimiters inside strings shouldn't be counted
        assert count_delimiters('"("') == 0  # parenthesis in string


class TestStringProcessing:
    # * Test strip_trailing_comment removes comments
    def test_strips_trailing_comment(self):
        assert strip_trailing_comment("text // comment") == "text "
        assert strip_trailing_comment("no comment") == "no comment"

    def test_preserves_comment_in_string(self):
        # // inside a string shouldn't be stripped
        result = strip_trailing_comment('"url://example.com"')
        assert "//" in result

    # * Test strip_string_literals removes strings
    def test_strips_string_literals(self):
        result = strip_string_literals('text "in quotes" more')
        assert '"' not in result
        assert "in quotes" not in result


class TestIsStructuralLine:
    # * Test is_structural_line detects structural lines
    def test_detects_structural_prefix(self):
        assert is_structural_line("#set page()")
        assert is_structural_line("#show heading: it => {}")

    def test_with_frozen_patterns(self):
        frozen = ["FROZEN_TEXT", "CUSTOM_MARKER"]
        assert is_structural_line("Line with FROZEN_TEXT", frozen_patterns=frozen)
        assert not is_structural_line("Regular line", frozen_patterns=frozen)

    def test_empty_line(self):
        assert not is_structural_line("")
        assert not is_structural_line("   ")


class TestPreservationHelpers:
    # * Test is_preservable_content preserves structural lines
    def test_preserves_structural(self):
        assert is_preservable_content("#set page()")
        assert is_preservable_content("// Comment")

    def test_preserves_headings(self):
        assert is_preservable_content("= Experience")
        assert is_preservable_content("== Details")

    def test_preserves_content(self):
        assert is_preservable_content("Regular text content")
        assert is_preservable_content("- Bullet point")

    def test_rejects_whitespace(self):
        assert not is_preservable_content("")
        assert not is_preservable_content("   ")

    # * Test requires_trailing_blank
    def test_trailing_blank_after_heading(self):
        assert requires_trailing_blank("= Experience")
        assert requires_trailing_blank("== Details")

    def test_trailing_blank_after_closing_delimiter(self):
        assert requires_trailing_blank(")")
        assert requires_trailing_blank("]")

    def test_no_trailing_blank_for_content(self):
        assert not requires_trailing_blank("Regular text")
        assert not requires_trailing_blank("- Bullet")


class TestInferSectionKind:
    # * Test infer_section_kind identifies section types
    def test_infers_education(self):
        assert infer_section_kind("Education") == "education"
        assert infer_section_kind("Academic Background") == "education"

    def test_infers_experience(self):
        assert infer_section_kind("Professional Experience") == "experience"
        assert infer_section_kind("Work History") == "experience"

    def test_infers_skills(self):
        assert infer_section_kind("Technical Skills") == "skills"
        assert infer_section_kind("Technologies") == "skills"

    def test_infers_summary(self):
        assert infer_section_kind("Professional Summary") == "summary"
        assert infer_section_kind("Objective") == "summary"

    def test_returns_none_for_unknown(self):
        assert infer_section_kind("Custom Section") is None
        assert infer_section_kind("Other") is None
