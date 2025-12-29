# tests/unit/loom_io/test_latex_patterns.py
# Unit tests for LaTeX pattern constants & helper functions

import pytest

from src.loom_io.latex_patterns import (
    SECTION_CMD_RE,
    SEMANTIC_MATCHERS,
    BULLET_PATTERNS,
    STRUCTURAL_PREFIXES,
    SECTION_PREFIXES,
    is_structural_prefix,
    is_section_command,
    is_protected_prefix,
    is_structural_line,
    is_preservable_content,
    requires_trailing_blank,
)


class TestSectionCmdRegex:
    # * Test SECTION_CMD_RE matches standard section commands
    def test_matches_section(self):
        match = SECTION_CMD_RE.search(r"\section{Experience}")
        assert match is not None
        assert match.group("cmd") == "section"
        assert match.group("title") == "Experience"

    # * Test SECTION_CMD_RE matches starred variants
    def test_matches_starred_section(self):
        match = SECTION_CMD_RE.search(r"\section*{Skills}")
        assert match is not None
        assert match.group("cmd") == "section*"

    # * Test SECTION_CMD_RE matches subsection commands
    def test_matches_subsection(self):
        match = SECTION_CMD_RE.search(r"\subsection{Details}")
        assert match is not None
        assert match.group("cmd") == "subsection"

    # * Test SECTION_CMD_RE matches subsubsection commands
    def test_matches_subsubsection(self):
        match = SECTION_CMD_RE.search(r"\subsubsection{More Details}")
        assert match is not None
        assert match.group("cmd") == "subsubsection"

    # * Test SECTION_CMD_RE matches custom CV section commands
    def test_matches_cvsection(self):
        match = SECTION_CMD_RE.search(r"\cvsection{Work History}")
        assert match is not None
        assert match.group("cmd") == "cvsection"

    # * Test SECTION_CMD_RE matches sectionhead command
    def test_matches_sectionhead(self):
        match = SECTION_CMD_RE.search(r"\sectionhead{Education}")
        assert match is not None
        assert match.group("cmd") == "sectionhead"

    # * Test SECTION_CMD_RE handles whitespace in braces
    def test_handles_whitespace(self):
        match = SECTION_CMD_RE.search(r"\section{  Education  }")
        assert match is not None
        assert match.group("title").strip() == "Education"

    # * Test SECTION_CMD_RE does not match non-section commands
    def test_no_match_for_non_section(self):
        assert SECTION_CMD_RE.search(r"\item Bullet") is None
        assert SECTION_CMD_RE.search(r"\textbf{Bold}") is None


class TestSemanticMatchers:
    # * Test education matcher identifies education sections
    def test_education_matcher(self):
        assert SEMANTIC_MATCHERS["education"].search("Education")
        assert SEMANTIC_MATCHERS["education"].search("EDUCATION")
        assert SEMANTIC_MATCHERS["education"].search("Academic Background")
        assert not SEMANTIC_MATCHERS["education"].search("Work Experience")

    # * Test experience matcher identifies experience sections
    def test_experience_matcher(self):
        assert SEMANTIC_MATCHERS["experience"].search("Experience")
        assert SEMANTIC_MATCHERS["experience"].search("Work History")
        assert SEMANTIC_MATCHERS["experience"].search("Employment")
        assert not SEMANTIC_MATCHERS["experience"].search("Education")

    # * Test skills matcher identifies skills sections
    def test_skills_matcher(self):
        assert SEMANTIC_MATCHERS["skills"].search("Skills")
        assert SEMANTIC_MATCHERS["skills"].search("Technical Skills")
        assert SEMANTIC_MATCHERS["skills"].search("Technologies")
        assert SEMANTIC_MATCHERS["skills"].search("Tools")

    # * Test projects matcher identifies projects sections
    def test_projects_matcher(self):
        assert SEMANTIC_MATCHERS["projects"].search("Projects")
        assert SEMANTIC_MATCHERS["projects"].search("Personal Projects")
        assert SEMANTIC_MATCHERS["projects"].search("Project")

    # * Test publications matcher identifies publications sections
    def test_publications_matcher(self):
        assert SEMANTIC_MATCHERS["publications"].search("Publications")
        assert SEMANTIC_MATCHERS["publications"].search("Research")
        assert not SEMANTIC_MATCHERS["publications"].search("Experience")

    # * Test certifications matcher identifies certifications sections
    def test_certifications_matcher(self):
        assert SEMANTIC_MATCHERS["certifications"].search("Certifications")
        assert SEMANTIC_MATCHERS["certifications"].search("Licenses")
        assert not SEMANTIC_MATCHERS["certifications"].search("Skills")

    # * Test heading matcher identifies heading elements
    def test_heading_matcher(self):
        assert SEMANTIC_MATCHERS["heading"].search(r"\name{John Doe}")
        assert SEMANTIC_MATCHERS["heading"].search(r"\contact")
        assert not SEMANTIC_MATCHERS["heading"].search("Experience")


class TestBulletPatterns:
    # * Test BULLET_PATTERNS detect \\item command
    def test_detects_item(self):
        assert any(p.search(r"\item First bullet") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS detect \\entry command
    def test_detects_entry(self):
        assert any(p.search(r"\entry{Company}") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS detect \\cventry command
    def test_detects_cventry(self):
        assert any(p.search(r"\cventry{2020}{Title}") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS detect \\cvitem command
    def test_detects_cvitem(self):
        assert any(p.search(r"\cvitem{Label}{Value}") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS don't match arbitrary text
    def test_no_false_positives(self):
        assert not any(p.search("itemize") for p in BULLET_PATTERNS)
        assert not any(p.search("entry point") for p in BULLET_PATTERNS)

    # * Test BULLET_PATTERNS require word boundary
    def test_requires_word_boundary(self):
        # should not match "itemized" or "items"
        assert not any(p.search(r"\itemized list") for p in BULLET_PATTERNS)


class TestStructuralPrefixes:
    # * Test STRUCTURAL_PREFIXES contains expected commands
    def test_contains_documentclass(self):
        assert any("documentclass" in p for p in STRUCTURAL_PREFIXES)

    # * Test STRUCTURAL_PREFIXES contains usepackage
    def test_contains_usepackage(self):
        assert any("usepackage" in p for p in STRUCTURAL_PREFIXES)

    # * Test STRUCTURAL_PREFIXES contains begin/end
    def test_contains_begin_end(self):
        assert any("begin{" in p for p in STRUCTURAL_PREFIXES)
        assert any("end{" in p for p in STRUCTURAL_PREFIXES)


class TestSectionPrefixes:
    # * Test SECTION_PREFIXES contains section commands
    def test_contains_section(self):
        assert r"\section" in SECTION_PREFIXES
        assert r"\subsection" in SECTION_PREFIXES
        assert r"\subsubsection" in SECTION_PREFIXES


class TestStructuralChecks:
    # * Test is_structural_prefix identifies document structure
    def test_structural_prefix_documentclass(self):
        assert is_structural_prefix(r"\documentclass{article}")

    # * Test is_structural_prefix identifies packages
    def test_structural_prefix_usepackage(self):
        assert is_structural_prefix(r"\usepackage{geometry}")

    # * Test is_structural_prefix identifies environments
    def test_structural_prefix_begin_end(self):
        assert is_structural_prefix(r"\begin{document}")
        assert is_structural_prefix(r"\end{document}")

    # * Test is_structural_prefix handles whitespace
    def test_structural_prefix_with_whitespace(self):
        assert is_structural_prefix("  \\documentclass{article}")
        assert is_structural_prefix("\t\\usepackage{geometry}")

    # * Test is_structural_prefix rejects non-structural
    def test_structural_prefix_rejects_non_structural(self):
        assert not is_structural_prefix(r"\textbf{bold}")
        assert not is_structural_prefix("Regular text")

    # * Test is_section_command identifies section commands
    def test_section_command_detection(self):
        assert is_section_command(r"\section{Test}")
        assert is_section_command(r"\subsection{Details}")
        assert is_section_command(r"\subsubsection{More}")
        assert not is_section_command(r"\item Test")

    # * Test is_protected_prefix identifies all protected types
    def test_protected_prefix_structural(self):
        assert is_protected_prefix(r"\documentclass{article}")
        assert is_protected_prefix(r"\usepackage{geometry}")

    # * Test is_protected_prefix identifies sections
    def test_protected_prefix_sections(self):
        assert is_protected_prefix(r"\section{Test}")
        assert is_protected_prefix(r"\subsection{Details}")

    # * Test is_protected_prefix identifies items
    def test_protected_prefix_items(self):
        assert is_protected_prefix(r"\item Bullet point")

    # * Test is_protected_prefix identifies comments
    def test_protected_prefix_comments(self):
        assert is_protected_prefix("% This is a comment")


class TestIsStructuralLine:
    # * Test is_structural_line detects structural prefixes
    def test_detects_structural_prefix(self):
        assert is_structural_line(r"\documentclass{article}")
        assert is_structural_line(r"\begin{document}")

    # * Test is_structural_line w/ frozen patterns
    def test_with_frozen_patterns(self):
        frozen = ["FROZEN_TEXT", "CUSTOM_MARKER"]
        assert is_structural_line("Line with FROZEN_TEXT here", frozen_patterns=frozen)
        assert is_structural_line("CUSTOM_MARKER line", frozen_patterns=frozen)
        assert not is_structural_line("Regular line", frozen_patterns=frozen)

    # * Test is_structural_line w/ include_all_protected flag
    def test_include_all_protected(self):
        assert is_structural_line(r"\section{Test}", include_all_protected=True)
        assert is_structural_line(r"\item Bullet", include_all_protected=True)
        assert is_structural_line("% Comment", include_all_protected=True)

    # * Test is_structural_line returns False for empty
    def test_empty_line(self):
        assert not is_structural_line("")
        assert not is_structural_line("   ")


class TestPreservationHelpers:
    # * Test is_preservable_content preserves structural lines
    def test_preserves_structural(self):
        assert is_preservable_content(r"\documentclass{article}")
        assert is_preservable_content(r"\section{Experience}")

    # * Test is_preservable_content preserves non-empty content
    def test_preserves_content(self):
        assert is_preservable_content("Regular text content")
        assert is_preservable_content(r"\item Bullet point")

    # * Test is_preservable_content preserves comments
    def test_preserves_comments(self):
        assert is_preservable_content("% This is a comment")

    # * Test is_preservable_content rejects whitespace-only
    def test_rejects_whitespace(self):
        assert not is_preservable_content("")
        assert not is_preservable_content("   ")
        assert not is_preservable_content("\t\n")

    # * Test requires_trailing_blank after end commands
    def test_trailing_blank_after_end(self):
        assert requires_trailing_blank(r"\end{itemize}")
        assert requires_trailing_blank(r"\end{document}")
        assert requires_trailing_blank(r"\end{enumerate}")

    # * Test requires_trailing_blank after section commands
    def test_trailing_blank_after_section(self):
        assert requires_trailing_blank(r"\section{Test}")
        assert requires_trailing_blank(r"\subsection{Details}")
        assert requires_trailing_blank(r"\subsubsection{More}")

    # * Test requires_trailing_blank after starred section commands
    def test_trailing_blank_after_starred_section(self):
        assert requires_trailing_blank(r"\section*{Test}")
        assert requires_trailing_blank(r"\subsection*{Details}")

    # * Test requires_trailing_blank false for regular content
    def test_no_trailing_blank_for_content(self):
        assert not requires_trailing_blank("Regular text")
        assert not requires_trailing_blank(r"\item Bullet")
        assert not requires_trailing_blank(r"\textbf{Bold text}")
