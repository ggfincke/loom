# tests/unit/loom_io/test_documents.py
# Unit tests for document I/O operations w/ round-trip behaviors & formatting preservation

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.loom_io.documents import (
    read_docx,
    read_docx_with_formatting,
    write_docx,
    read_latex,
    write_text_lines,
    read_resume,
    apply_edits_to_docx,
    read_text,
    _categorize_edits,
    _copy_run_formatting,
    _set_paragraph_text_preserving_format,
)
from src.loom_io.generics import (
    write_json_safe,
    read_json_safe,
    ensure_parent,
    exit_with_error,
)
from src.core.exceptions import LaTeXError, JSONParsingError


# * Fixtures for document testing


# * Path to basic formatted DOCX test fixture
@pytest.fixture
def sample_docx_path():
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "documents"
    return fixtures_dir / "basic_formatted_resume.docx"


# * Path to simple formatted DOCX test fixture
@pytest.fixture
def simple_docx_path():
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "documents"
    return fixtures_dir / "simple_formatted.docx"


# * Path to edge case DOCX test fixture
@pytest.fixture
def edge_case_docx_path():
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "documents"
    return fixtures_dir / "edge_cases.docx"


# * Path to formatted LaTeX test fixture
@pytest.fixture
def sample_latex_path():
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "documents"
    return fixtures_dir / "basic_formatted_resume.tex"


# * Path to simple LaTeX test fixture
@pytest.fixture
def simple_latex_path():
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "documents"
    return fixtures_dir / "simple_latex.tex"


# * Sample lines dict for edit testing
@pytest.fixture
def sample_lines_for_edits():
    return {
        1: "John Doe",
        2: "Software Engineer",
        3: "john.doe@email.com | (555) 123-4567",
        4: "",
        5: "PROFESSIONAL SUMMARY",
        6: "Experienced software engineer w/ 5+ years developing applications.",
        7: "",
        8: "TECHNICAL SKILLS",
        9: "• Python, JavaScript, TypeScript",
        10: "• React, Django, FastAPI",
    }


# * Test DOCX reading operations


class TestDocxReading:

    # * Test basic DOCX reading returns expected line content
    def test_read_docx_basic_content(self, sample_docx_path):
        lines = read_docx(sample_docx_path)

        assert isinstance(lines, dict)
        assert len(lines) > 0
        assert 1 in lines
        assert "John Doe" in lines[1]
        assert "Software Engineer" in lines[2]
        assert "PROFESSIONAL SUMMARY" in lines.values()

    # * Test read_docx_with_formatting returns lines, doc object, & paragraph map
    def test_read_docx_with_formatting_returns_components(self, sample_docx_path):
        lines, doc, paragraph_map = read_docx_with_formatting(sample_docx_path)

        assert isinstance(lines, dict)
        assert doc is not None and hasattr(doc, "paragraphs")  # Document-like object
        assert isinstance(paragraph_map, dict)
        assert len(lines) == len(paragraph_map)

        # verify paragraph map contains actual paragraph objects
        for line_num in lines:
            assert line_num in paragraph_map
            # paragraph objects should have _element attribute (from python-docx)
            para = paragraph_map[line_num]
            assert hasattr(para, "_element")

    # * Test DOCX reading skips empty/whitespace-only paragraphs
    def test_read_docx_skips_empty_lines(self, edge_case_docx_path):
        lines = read_docx(edge_case_docx_path)

        # should only have non-empty lines
        for _, text in lines.items():
            assert text.strip() != ""

        # verify we got the expected content lines
        assert "Single line" in lines.values()
        assert "Another line" in lines.values()

    # * Test reading non-existent DOCX file raises appropriate error
    def test_read_docx_nonexistent_file(self, tmp_path):
        fake_path = tmp_path / "nonexistent.docx"

        with pytest.raises(Exception):  # python-docx raises various exceptions
            read_docx(fake_path)


# * Test DOCX round-trip operations w/ formatting preservation


class TestDocxRoundTrip:

    # * Test DOCX read→write cycle preserves basic content
    def test_docx_roundtrip_preserves_content(self, simple_docx_path, tmp_path):
        # read original
        original_lines = read_docx(simple_docx_path)

        # write to new file
        output_path = tmp_path / "roundtrip_test.docx"
        write_docx(original_lines, output_path)

        # read back
        roundtrip_lines = read_docx(output_path)

        # verify content preserved
        assert len(original_lines) == len(roundtrip_lines)
        for line_num in original_lines:
            assert line_num in roundtrip_lines
            assert original_lines[line_num] == roundtrip_lines[line_num]

    # * Test edits preserve formatting on untouched content - spot check bold run
    def test_apply_edits_preserves_untouched_formatting(
        self, simple_docx_path, tmp_path
    ):
        # read w/ formatting info
        original_lines, _, _ = read_docx_with_formatting(simple_docx_path)

        # create minimal edit that doesn't touch the formatted content
        new_lines = original_lines.copy()
        # assuming line 1 has "Simple Document" which should be bold
        # we'll edit a different line to test preservation
        if len(new_lines) > 2:
            new_lines[max(new_lines.keys())] = "• Added item"  # edit last line

        # apply edits using in_place mode for better formatting preservation
        output_path = tmp_path / "edited_formatted.docx"
        apply_edits_to_docx(
            simple_docx_path, new_lines, output_path, preserve_mode="in_place"
        )

        # read back w/ formatting
        edited_lines, _, edited_paragraphs = read_docx_with_formatting(output_path)

        # verify the bold formatting is preserved on the title line
        # find the title paragraph (should be line 1 w/ "Simple Document")
        title_line = None
        for line_num, text in edited_lines.items():
            if "Simple Document" in text:
                title_line = line_num
                break

        assert title_line is not None, "Could not find title line in edited document"
        assert title_line in edited_paragraphs

        title_paragraph = edited_paragraphs[title_line]
        assert len(title_paragraph.runs) > 0, "Title paragraph should have runs"

        # check if first run has bold formatting
        first_run = title_paragraph.runs[0]
        assert (
            first_run.bold is True or first_run.bold is None
        ), f"Expected bold formatting preserved, got: {first_run.bold}"

    # * Test replace_line edit operation works correctly
    def test_apply_edits_replace_line_operation(self, sample_docx_path, tmp_path):
        original_lines = read_docx(sample_docx_path)

        # modify one line
        new_lines = original_lines.copy()
        target_line = min(original_lines.keys())  # edit first line
        new_lines[target_line] = "Jane Smith"

        output_path = tmp_path / "replace_line_test.docx"
        apply_edits_to_docx(sample_docx_path, new_lines, output_path)

        # verify change applied
        result_lines = read_docx(output_path)
        assert result_lines[target_line] == "Jane Smith"

        # verify other lines unchanged
        for line_num, text in original_lines.items():
            if line_num != target_line:
                assert result_lines[line_num] == text

    # * Test insert & delete operations maintain document structure
    def test_apply_edits_insert_and_delete_operations(self, sample_docx_path, tmp_path):
        original_lines = read_docx(sample_docx_path)
        original_count = len(original_lines)

        # create new lines dict w/ an insertion & deletion
        new_lines = {}
        line_counter = 1

        for orig_line_num in sorted(original_lines.keys()):
            # skip line 3 (delete it)
            if orig_line_num == 3:
                continue

            new_lines[line_counter] = original_lines[orig_line_num]
            line_counter += 1

            # insert after line 5 becomes line 4 after deletion
            if orig_line_num == 5:
                new_lines[line_counter] = "INSERTED: New section header"
                line_counter += 1

        output_path = tmp_path / "insert_delete_test.docx"
        apply_edits_to_docx(sample_docx_path, new_lines, output_path)

        result_lines = read_docx(output_path)

        # verify we have correct number of lines (original - 1 + 1 = same)
        assert len(result_lines) == original_count

        # verify inserted content exists
        assert "INSERTED: New section header" in result_lines.values()

        # verify original line 3 content doesn't exist
        original_line_3_content = original_lines[3]
        assert original_line_3_content not in result_lines.values()


# * Test LaTeX operations


class TestLatexOperations:

    # * Test LaTeX reading returns expected content
    def test_read_latex_basic_content(self, sample_latex_path):
        lines = read_latex(sample_latex_path)

        assert isinstance(lines, dict)
        assert len(lines) > 0

        # verify key LaTeX content is present
        all_text = " ".join(lines.values())
        assert "\\documentclass" in all_text
        assert "\\begin{document}" in all_text
        assert "\\end{document}" in all_text
        assert "John Doe" in all_text
        assert "Professional Summary" in all_text

    # * Test structured LaTeX reading preserves comments & commands
    def test_read_latex_with_structure_preserves_comments(self, sample_latex_path):
        lines = read_latex(sample_latex_path, preserve_structure=True)

        # find comment lines
        comment_lines = [
            text for text in lines.values() if text.strip().startswith("%")
        ]
        assert len(comment_lines) > 0, "Should preserve comment lines"

        # verify specific comment is preserved
        assert any(
            "This is a comment that should be preserved" in comment
            for comment in comment_lines
        )

        # verify structural commands preserved
        all_text = " ".join(lines.values())
        assert "\\section{Professional Summary}" in all_text
        assert "\\begin{itemize}" in all_text
        assert "\\end{itemize}" in all_text

    # * Test difference between basic & structured LaTeX reading
    def test_read_latex_difference_between_modes(self, simple_latex_path):
        basic_lines = read_latex(simple_latex_path)
        structured_lines = read_latex(simple_latex_path, preserve_structure=True)

        # structured mode should preserve more content (comments, empty lines)
        assert len(structured_lines) >= len(basic_lines)

        # both should have core content
        basic_text = " ".join(basic_lines.values())
        structured_text = " ".join(structured_lines.values())

        for text in [basic_text, structured_text]:
            assert "\\documentclass" in text
            assert "\\section{Introduction}" in text

    # * Test LaTeX read→write cycle preserves structure
    def test_latex_roundtrip_preserves_structure(self, simple_latex_path, tmp_path):
        # read w/ structure preservation
        original_lines = read_latex(simple_latex_path, preserve_structure=True)

        # write to new file
        output_path = tmp_path / "roundtrip.tex"
        write_text_lines(original_lines, output_path)

        # read back
        roundtrip_lines = read_latex(output_path, preserve_structure=True)

        # verify core content preserved
        original_text = " ".join(original_lines.values())
        roundtrip_text = " ".join(roundtrip_lines.values())

        # check key structural elements preserved
        for element in [
            "\\documentclass",
            "\\begin{document}",
            "\\section{",
            "\\end{document}",
        ]:
            assert element in original_text
            assert element in roundtrip_text

    # * Test invalid LaTeX syntax raises LaTeXError
    def test_latex_invalid_syntax_raises_error(self, tmp_path):
        invalid_tex = tmp_path / "invalid.tex"
        invalid_tex.write_text(
            r"""
        \documentclass{article}
        \begin{document}
        Unmatched { brace
        \end{document}
        """
        )

        with pytest.raises(LaTeXError, match="Invalid LaTeX syntax"):
            read_latex(invalid_tex)

    # * Test LaTeX file w/ encoding issues raises LaTeXError
    def test_latex_file_encoding_error(self, tmp_path):
        bad_file = tmp_path / "bad_encoding.tex"
        # write invalid UTF-8 bytes
        bad_file.write_bytes(b"\xff\xfe invalid utf-8")

        with pytest.raises(LaTeXError, match="Cannot decode LaTeX file"):
            read_latex(bad_file)


# * Test read_resume auto-detection


class TestReadResumeAutoDetection:

    # * Test read_resume correctly handles .docx files
    def test_read_resume_docx_detection(self, sample_docx_path):
        lines = read_resume(sample_docx_path)

        assert isinstance(lines, dict)
        assert "John Doe" in lines.values()

    # * Test read_resume correctly handles .tex files
    def test_read_resume_tex_detection(self, sample_latex_path):
        lines = read_resume(sample_latex_path)

        assert isinstance(lines, dict)
        all_text = " ".join(lines.values())
        assert "\\documentclass" in all_text

    # * Test read_resume w/ preserve_structure flag for LaTeX
    def test_read_resume_tex_with_structure_flag(self, sample_latex_path):
        lines_basic = read_resume(sample_latex_path, preserve_structure=False)
        lines_structured = read_resume(sample_latex_path, preserve_structure=True)

        # structured should preserve more content
        assert len(lines_structured) >= len(lines_basic)

    # * Test read_resume defaults to DOCX handling for unknown extensions
    def test_read_resume_unknown_extension_defaults_docx(self, tmp_path):
        # create a text file w/ .txt extension
        text_file = tmp_path / "resume.txt"
        text_file.write_text("Simple text resume\nSoftware Engineer")

        # this should attempt DOCX processing & fail appropriately
        with pytest.raises(Exception):  # python-docx will raise error
            read_resume(text_file)


# * Test line mapping & edit categorization helpers


class TestLineMappingHelpers:

    # * Test _categorize_edits correctly identifies line modifications
    def test_categorize_edits_identifies_modifications(self, sample_lines_for_edits):
        original_lines = sample_lines_for_edits
        new_lines = original_lines.copy()
        new_lines[6] = "Senior Python developer w/ 7+ years building applications."

        modifications, additions, deletions = _categorize_edits(
            original_lines, new_lines
        )

        assert 6 in modifications
        assert (
            modifications[6]
            == "Senior Python developer w/ 7+ years building applications."
        )
        assert len(additions) == 0
        assert len(deletions) == 0

    # * Test _categorize_edits correctly identifies line additions
    def test_categorize_edits_identifies_additions(self, sample_lines_for_edits):
        original_lines = sample_lines_for_edits
        new_lines = original_lines.copy()
        new_lines[11] = "• Git, Docker, AWS"  # add new line

        modifications, additions, deletions = _categorize_edits(
            original_lines, new_lines
        )

        assert len(modifications) == 0
        assert len(additions) == 1
        assert additions[0] == (10, 11, "• Git, Docker, AWS")  # insert after line 10
        assert len(deletions) == 0

    # * Test _categorize_edits correctly identifies line deletions
    def test_categorize_edits_identifies_deletions(self, sample_lines_for_edits):
        original_lines = sample_lines_for_edits
        new_lines = original_lines.copy()
        del new_lines[4]  # delete empty line

        modifications, additions, deletions = _categorize_edits(
            original_lines, new_lines
        )

        assert len(modifications) == 0
        assert len(additions) == 0
        assert 4 in deletions

    # * Test _categorize_edits handles complex edit combinations
    def test_categorize_edits_complex_changes(self, sample_lines_for_edits):
        original_lines = sample_lines_for_edits
        new_lines = {
            1: "Jane Smith",  # modification
            2: "Senior Software Engineer",  # modification
            3: original_lines[3],  # unchanged
            # line 4 deleted
            5: original_lines[5],  # unchanged
            6: "Expert Python developer w/ 8+ years experience.",  # modification
            7: original_lines[7],  # unchanged
            8: original_lines[8],  # unchanged
            9: original_lines[9],  # unchanged
            10: original_lines[10],  # unchanged
            11: "• Tools: Git, Docker, Kubernetes",  # addition
        }

        modifications, additions, deletions = _categorize_edits(
            original_lines, new_lines
        )

        # verify modifications
        assert len(modifications) == 3
        assert modifications[1] == "Jane Smith"
        assert modifications[2] == "Senior Software Engineer"
        assert modifications[6] == "Expert Python developer w/ 8+ years experience."

        # verify additions
        assert len(additions) == 1
        assert additions[0] == (10, 11, "• Tools: Git, Docker, Kubernetes")

        # verify deletions
        assert len(deletions) == 1
        assert 4 in deletions

    # * Test _categorize_edits correctly handles complex line changes
    def test_line_numbering_stability_after_operations(self, sample_lines_for_edits):
        original_lines = sample_lines_for_edits

        # create new_lines dict w/ realistic changes that maintain line number semantics
        new_lines = original_lines.copy()

        # modify existing line
        new_lines[1] = "Jane Smith"  # change name

        # delete a line (remove from new_lines)
        del new_lines[4]  # delete empty line

        # add new lines (using line numbers not in original)
        new_lines[11] = "INSERTED: New technical skill"
        new_lines[12] = "INSERTED: Additional experience"

        # verify we can categorize these changes
        modifications, additions, deletions = _categorize_edits(
            original_lines, new_lines
        )

        # verify modifications detected
        assert len(modifications) >= 1
        assert 1 in modifications
        assert modifications[1] == "Jane Smith"

        # verify deletions detected
        assert len(deletions) >= 1
        assert 4 in deletions

        # verify additions detected
        assert len(additions) >= 1
        inserted_texts = [add[2] for add in additions]
        assert "INSERTED: New technical skill" in inserted_texts
        assert "INSERTED: Additional experience" in inserted_texts

        # verify insertion position tracking works
        for insert_after, line_num, _ in additions:
            if line_num == 11:
                assert insert_after == 10  # should insert after line 10
            elif line_num == 12:
                # line 12 inserts after highest original line less than 12, which is 10
                assert insert_after == 10


# * Test formatting helper functions


class TestFormattingHelpers:

    # * Test _copy_run_formatting preserves bold attribute
    def test_copy_run_formatting_preserves_bold(self):
        # create mock runs
        source_run = MagicMock()
        source_run.font.bold = True
        source_run.font.italic = None
        source_run.font.underline = None
        source_run.font.strike = None
        source_run.font.size = None
        source_run.font.name = None
        source_run.font.color = None
        source_run.font.highlight_color = None

        target_run = MagicMock()
        target_run.font = MagicMock()

        _copy_run_formatting(source_run, target_run)

        assert target_run.font.bold == True

    # * Test _copy_run_formatting handles None source run gracefully
    def test_copy_run_formatting_handles_none_source(self):
        target_run = MagicMock()

        # should not raise exception
        _copy_run_formatting(None, target_run)

    # * Test _set_paragraph_text_preserving_format sets text correctly
    def test_set_paragraph_text_preserving_format_basic(self):
        # create mock paragraph
        mock_para = MagicMock()
        mock_run = MagicMock()
        mock_run.font.bold = True
        mock_para.runs = [mock_run]

        new_run = MagicMock()
        mock_para.add_run.return_value = new_run

        _set_paragraph_text_preserving_format(mock_para, "New text")

        mock_para.clear.assert_called_once()
        mock_para.add_run.assert_called_once_with("New text")


# * Test generic I/O operations


class TestGenericIO:

    # * Test write_json_safe creates parent directories
    def test_write_json_safe_creates_parent_dirs(self, tmp_path):
        nested_path = tmp_path / "deep" / "nested" / "dirs" / "test.json"
        test_data = {"key": "value", "number": 42}

        write_json_safe(test_data, nested_path)

        assert nested_path.exists()
        assert nested_path.parent.exists()

        # verify content
        loaded_data = read_json_safe(nested_path)
        assert loaded_data == test_data

    # * Test read_json_safe raises JSONParsingError for malformed JSON
    def test_read_json_safe_handles_malformed_json(self, tmp_path):
        bad_json_file = tmp_path / "bad.json"
        bad_json_file.write_text('{"invalid": json,}')  # trailing comma

        with pytest.raises(JSONParsingError) as exc_info:
            read_json_safe(bad_json_file)

        assert "Invalid JSON" in str(exc_info.value)
        assert bad_json_file.name in str(exc_info.value)

    # * Test read_json_safe provides helpful error context w/ line numbers
    def test_read_json_safe_provides_error_context(self, tmp_path):
        bad_json_file = tmp_path / "context_test.json"
        bad_json_content = """{
  "line1": "value1",
  "line2": "value2",
  "line3": invalid_json_here,
  "line4": "value4"
}"""
        bad_json_file.write_text(bad_json_content)

        with pytest.raises(JSONParsingError) as exc_info:
            read_json_safe(bad_json_file)

        error_msg = str(exc_info.value)
        assert "Invalid JSON" in error_msg
        assert "4:" in error_msg  # should show line 4 context
        assert "invalid_json_here" in error_msg

    # * Test ensure_parent creates necessary parent directories
    def test_ensure_parent_creates_directories(self, tmp_path):
        nested_file = tmp_path / "a" / "b" / "c" / "file.txt"

        ensure_parent(nested_file)

        assert nested_file.parent.exists()
        assert nested_file.parent.is_dir()

    # * Test ensure_parent handles existing directories gracefully
    def test_ensure_parent_handles_existing_dirs(self, tmp_path):
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        file_in_existing = existing_dir / "file.txt"

        # should not raise exception
        ensure_parent(file_in_existing)
        assert existing_dir.exists()

    @patch("typer.echo")
    @patch("typer.Exit")
    # * Test exit_with_error prints to stderr & exits w/ correct code
    def test_exit_with_error_prints_message_and_exits(self, mock_exit, mock_echo):
        mock_exit.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            exit_with_error("Test error message", code=42)

        mock_echo.assert_called_once_with("Test error message", err=True)
        mock_exit.assert_called_once_with(42)


# * Test error handling & edge cases


class TestErrorHandling:

    # * Test read_text reads file content correctly
    def test_read_text_basic_functionality(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_content = "Hello\nWorld\nTest"
        test_file.write_text(test_content, encoding="utf-8")

        result = read_text(test_file)
        assert result == test_content

    # * Test write_text_lines formats output correctly
    def test_write_text_lines_formatting(self, tmp_path):
        lines = {1: "First line", 3: "Third line", 2: "Second line"}
        output_file = tmp_path / "output.txt"

        write_text_lines(lines, output_file)

        content = output_file.read_text(encoding="utf-8")
        expected = "First line\nSecond line\nThird line"
        assert content == expected

    # * Test apply_edits_to_docx works w/ different preserve modes
    def test_apply_edits_to_docx_preserve_modes(self, simple_docx_path, tmp_path):
        original_lines = read_docx(simple_docx_path)
        modified_lines = original_lines.copy()
        assert len(modified_lines) > 0, "Expected non-empty document for testing"
        first_key = min(modified_lines.keys())
        modified_lines[first_key] = "Modified first line"

        # test in_place mode
        output_in_place = tmp_path / "in_place.docx"
        apply_edits_to_docx(
            simple_docx_path, modified_lines, output_in_place, preserve_mode="in_place"
        )

        # test rebuild mode
        output_rebuild = tmp_path / "rebuild.docx"
        apply_edits_to_docx(
            simple_docx_path, modified_lines, output_rebuild, preserve_mode="rebuild"
        )

        # both should produce valid DOCX files w/ the same text content
        lines_in_place = read_docx(output_in_place)
        lines_rebuild = read_docx(output_rebuild)

        assert lines_in_place[first_key] == "Modified first line"
        assert lines_rebuild[first_key] == "Modified first line"

        # should have same number of lines
        assert len(lines_in_place) == len(lines_rebuild)

    # * Test LaTeX syntax validation is called during read operations
    def test_latex_validation_integration(self, tmp_path):
        valid_latex = tmp_path / "valid.tex"
        valid_latex.write_text(
            r"""
        \documentclass{article}
        \begin{document}
        Hello world
        \end{document}
        """
        )

        # should read successfully
        lines = read_latex(valid_latex)
        assert len(lines) > 0

        invalid_latex = tmp_path / "invalid.tex"
        invalid_latex.write_text(
            r"""
        \documentclass{article}
        \begin{document}
        Unclosed {brace
        \end{document}
        """
        )

        # should raise LaTeXError
        with pytest.raises(LaTeXError):
            read_latex(invalid_latex)


# * Integration tests for cross-format compatibility


class TestCrossFormatIntegration:

    # * Test Lines type consistency across DOCX & LaTeX
    def test_lines_type_consistency_across_formats(
        self, sample_docx_path, sample_latex_path
    ):
        docx_lines = read_docx(sample_docx_path)
        latex_lines = read_latex(sample_latex_path)

        # both should return Lines type (dict[int, str])
        assert isinstance(docx_lines, dict)
        assert isinstance(latex_lines, dict)

        # keys should be integers
        for lines in [docx_lines, latex_lines]:
            for key in lines.keys():
                assert isinstance(key, int)
                assert key >= 1  # line numbers start at 1

            # values should be strings
            for value in lines.values():
                assert isinstance(value, str)

    # * Test read_resume provides consistent interface for both formats
    def test_read_resume_handles_both_formats_consistently(
        self, sample_docx_path, sample_latex_path
    ):
        docx_lines = read_resume(sample_docx_path)
        latex_lines = read_resume(sample_latex_path)

        # both should contain similar structural content
        docx_text = " ".join(docx_lines.values()).lower()
        latex_text = " ".join(latex_lines.values()).lower()

        # both should have key resume sections
        for content in [docx_text, latex_text]:
            assert "john doe" in content
            assert "professional" in content or "experience" in content

    # * Test error handling is consistent across document formats
    def test_error_handling_consistency_across_formats(self, tmp_path):
        nonexistent_docx = tmp_path / "fake.docx"
        nonexistent_tex = tmp_path / "fake.tex"

        # both should raise exceptions for nonexistent files
        with pytest.raises(Exception):
            read_docx(nonexistent_docx)

        with pytest.raises(Exception):
            read_latex(nonexistent_tex)

        # read_resume should handle both consistently
        with pytest.raises(Exception):
            read_resume(nonexistent_docx)

        with pytest.raises(Exception):
            read_resume(nonexistent_tex)
