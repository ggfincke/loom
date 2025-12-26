# tests/unit/ai/test_prompts.py
# Unit tests for AI prompt assembly & validation

import pytest

from src.ai.prompts import (
    build_sectionizer_prompt,
    build_generate_prompt,
    build_edit_prompt,
    build_prompt_operation_prompt,
    _is_latex_content,
)


# * Test prompt builders produce valid, complete prompts
class TestPromptAssembly:

    @pytest.fixture
    def sample_resume_text(self):
        return (
            "1\tJohn Doe\n"
            "2\tSoftware Engineer\n"
            "3\tjohn.doe@email.com\n"
            "4\t\n"
            "5\tPROFESSIONAL SUMMARY\n"
            "6\tExperienced developer with 5 years in web applications.\n"
            "7\t\n"
            "8\tTECHNICAL SKILLS\n"
            "9\t• Python, JavaScript, React\n"
            "10\t• AWS, Docker, PostgreSQL\n"
        )

    @pytest.fixture
    def sample_job_info(self):
        return (
            "Senior Full Stack Engineer\n"
            "Requirements:\n"
            "- 3+ years Python experience\n"
            "- React and Node.js proficiency\n"
            "- AWS cloud experience\n"
            "- Strong problem-solving skills"
        )

    @pytest.fixture
    def sample_sections_json(self):
        return '{"sections": [{"name": "SUMMARY", "start_line": 5, "end_line": 6}]}'

    # * Test sectionizer prompt contains required components
    def test_sectionizer_prompt_assembly(self, sample_resume_text):
        prompt = build_sectionizer_prompt(sample_resume_text)

        # basic sanity checks
        assert isinstance(prompt, str)
        assert len(prompt) > 100, "Prompt should be substantial"

        # required instruction components
        assert "section parser" in prompt.lower()
        assert "JSON" in prompt
        assert "1-based line numbers" in prompt
        assert "confidence" in prompt.lower()

        # schema requirements
        assert "sections" in prompt
        assert "start_line" in prompt
        assert "end_line" in prompt
        assert "subsections" in prompt

        # resume content injection
        assert sample_resume_text in prompt
        assert "John Doe" in prompt

        # section detection rules
        assert "PROFESSIONAL SUMMARY" in prompt
        assert "SUMMARY" in prompt
        assert "EXPERIENCE" in prompt
        assert "SKILLS" in prompt

    # * Test generate prompt contains all required elements
    def test_generate_prompt_assembly(self, sample_job_info, sample_resume_text):
        model = "gpt-5-mini"
        created_at = "2024-01-15T10:30:00Z"

        prompt = build_generate_prompt(
            job_info=sample_job_info,
            resume_with_line_numbers=sample_resume_text,
            model=model,
            created_at=created_at,
        )

        # basic validation
        assert isinstance(prompt, str)
        assert len(prompt) > 500, "Generate prompt should be comprehensive"

        # core instructions
        assert "resume editor" in prompt.lower()
        assert "surgical edits" in prompt.lower()
        assert "line number" in prompt.lower()

        # operation types
        assert "replace_line" in prompt
        assert "replace_range" in prompt
        assert "insert_after" in prompt
        assert "delete_range" in prompt

        # validation rules
        assert "current_snippet" in prompt
        assert "exact" in prompt  # emphasis on exactness
        assert "newline" in prompt  # newline validation rules

        # content injection
        assert sample_job_info in prompt
        assert sample_resume_text in prompt
        assert model in prompt
        assert created_at in prompt

        # safety constraints
        assert "truthful" in prompt.lower()
        assert "do not invent" in prompt.lower() or "don't invent" in prompt.lower()
        assert "embellishment" in prompt.lower()

    # * Test generate prompt includes sections when provided
    def test_generate_prompt_with_sections(
        self, sample_job_info, sample_resume_text, sample_sections_json
    ):
        prompt = build_generate_prompt(
            job_info=sample_job_info,
            resume_with_line_numbers=sample_resume_text,
            model="claude-sonnet-4",
            created_at="2024-01-15T10:30:00Z",
            sections_json=sample_sections_json,
        )

        assert sample_sections_json in prompt
        assert "Known Sections" in prompt

    # * Test edit prompt for fixing validation errors
    def test_edit_prompt_assembly(self, sample_job_info, sample_resume_text):
        model = "gpt-5-mini"
        created_at = "2024-01-15T11:00:00Z"
        edits_json = '{"version": 1, "ops": [{"op": "invalid_op"}]}'
        validation_errors = [
            "replace_line text contains newline; use replace_range",
            "line 999 not in resume bounds",
        ]

        prompt = build_edit_prompt(
            job_info=sample_job_info,
            resume_with_line_numbers=sample_resume_text,
            edits_json=edits_json,
            validation_errors=validation_errors,
            model=model,
            created_at=created_at,
        )

        # basic validation
        assert isinstance(prompt, str)
        assert len(prompt) > 300

        # core purpose
        assert "FIXING VALIDATION ERRORS" in prompt
        assert "previously generated" in prompt.lower()

        # error types
        assert "replace_line text contains newline" in prompt
        assert "line X not in resume bounds" in prompt
        assert "duplicate operation" in prompt

        # content injection
        assert sample_job_info in prompt
        assert sample_resume_text in prompt
        assert edits_json in prompt
        assert model in prompt
        assert created_at in prompt

        # specific validation errors
        for error in validation_errors:
            assert error in prompt

    # * Test prompts handle special characters & edge cases safely
    def test_prompt_parameter_injection_safety(self):
        # test with potentially problematic inputs
        problematic_resume = (
            '1\tName with "quotes" & special chars\n'
            "2\tLine with\nnewlines and\ttabs\n"
            "3\tUnicode: résumé café naïve\n"
        )

        problematic_job = 'Job with "quotes" and\nnewlines'

        # should not raise exceptions
        prompt1 = build_sectionizer_prompt(problematic_resume)
        assert len(prompt1) > 50
        assert problematic_resume in prompt1

        prompt2 = build_generate_prompt(
            job_info=problematic_job,
            resume_with_line_numbers=problematic_resume,
            model="test-model",
            created_at="2024-01-15T12:00:00Z",
        )
        assert len(prompt2) > 100
        assert problematic_job in prompt2
        assert problematic_resume in prompt2


class TestPromptRequiredElements:
    """Test prompts contain all necessary instructional elements"""

    def test_sectionizer_schema_completeness(self):
        """Ensure sectionizer prompt defines complete JSON schema (short keys)"""
        prompt = build_sectionizer_prompt("1\tTest Resume\n")

        # schema field requirements (short keys: k=kind, h=heading, s=start, e=end, c=confidence, sub=subsections)
        required_elements = [
            "sections",
            "k=kind",  # key legend
            "h=heading",  # key legend
            "notes",
        ]

        for element in required_elements:
            assert element in prompt, f"Missing required schema element: {element}"

        # data type specifications (check actual JSON examples w/ short keys)
        assert '"s": 1' in prompt  # short key for start_line
        assert '"c": 0.95' in prompt  # short key for confidence
        assert '"k": "SUMMARY"' in prompt  # short key for kind

    def test_generate_operation_schema_completeness(self):
        """Ensure generate prompt defines all operation schemas (short keys)"""
        prompt = build_generate_prompt(
            job_info="Test job",
            resume_with_line_numbers="1\tTest\n",
            model="test-model",
            created_at="2024-01-15T12:00:00Z",
        )

        # operation requirements
        operations = ["replace_line", "replace_range", "insert_after", "delete_range"]
        for op in operations:
            assert op in prompt, f"Missing operation type: {op}"

        # short key legend should be present
        assert "l=line" in prompt
        assert "t=text" in prompt
        assert "cur=current_snippet" in prompt

        # required fields per operation (check examples w/ short keys)
        assert '"l": 5' in prompt  # short key for line
        assert '"s": 10' in prompt  # short key for start
        assert '"e": 12' in prompt  # short key for end
        assert '"t": "Enhanced bullet"' in prompt  # short key for text
        assert '"cur": "Original"' in prompt  # short key for current_snippet
        assert '"w": "Python req"' in prompt  # short key for why

    def test_validation_checklist_presence(self):
        """Ensure prompts include validation checklists"""
        prompt = build_generate_prompt(
            job_info="Test",
            resume_with_line_numbers="1\tTest\n",
            model="test",
            created_at="2024-01-15T12:00:00Z",
        )

        # validation checklist elements (using short keys)
        assert "VALIDATION CHECKLIST" in prompt
        assert "cur matches" in prompt.lower() or "cur=current" in prompt.lower()
        assert "l/s/e" in prompt  # short key reference


class TestPromptEdgeCases:
    """Test prompt builders handle edge cases gracefully"""

    def test_empty_inputs(self):
        """Test prompts with minimal/empty inputs"""
        # should not crash with empty inputs
        prompt1 = build_sectionizer_prompt("")
        assert isinstance(prompt1, str)
        assert len(prompt1) > 100  # still contains instructions

        prompt2 = build_generate_prompt(
            job_info="",
            resume_with_line_numbers="",
            model="test-model",
            created_at="2024-01-15T12:00:00Z",
        )
        assert isinstance(prompt2, str)
        assert len(prompt2) > 200

    def test_very_long_inputs(self):
        """Test prompts with unusually long inputs"""
        long_resume = "\n".join([f"{i}\tLine {i} content" for i in range(1, 1001)])
        long_job = "Very long job description. " * 100

        prompt = build_generate_prompt(
            job_info=long_job,
            resume_with_line_numbers=long_resume,
            model="test-model",
            created_at="2024-01-15T12:00:00Z",
        )

        assert isinstance(prompt, str)
        assert long_resume in prompt
        assert long_job in prompt

    def test_none_optional_parameters(self):
        """Test optional parameters can be None"""
        prompt = build_generate_prompt(
            job_info="Test job",
            resume_with_line_numbers="1\tTest\n",
            model="test-model",
            created_at="2024-01-15T12:00:00Z",
            sections_json=None,  # explicit None
        )

        assert isinstance(prompt, str)
        assert "Known Sections" not in prompt


class TestPromptHelperFunctionality:
    """Test any helper functions mentioned in prompt construction"""

    def test_prompt_consistency_across_models(self):
        """Test prompts remain consistent regardless of model parameter"""
        base_args = {
            "job_info": "Test job description",
            "resume_with_line_numbers": "1\tTest Resume\n2\tContent\n",
            "created_at": "2024-01-15T12:00:00Z",
        }

        models = ["gpt-5-mini", "claude-sonnet-4", "llama3.2"]
        prompts = []

        for model in models:
            prompt = build_generate_prompt(model=model, **base_args)
            prompts.append(prompt)
            # model should appear in prompt
            assert model in prompt

        # core instructions should be identical across models
        # (only model references should differ)
        for prompt in prompts:
            assert "resume editor" in prompt.lower()
            assert "surgical edits" in prompt.lower()
            assert "current_snippet" in prompt

    def test_timestamp_injection_formats(self):
        """Test various timestamp format handling"""
        timestamps = [
            "2024-01-15T12:00:00Z",
            "2024-01-15T12:00:00.123Z",
            "2024-01-15 12:00:00",
        ]

        for timestamp in timestamps:
            prompt = build_generate_prompt(
                job_info="Test",
                resume_with_line_numbers="1\tTest\n",
                model="test-model",
                created_at=timestamp,
            )
            assert timestamp in prompt


# * Test LaTeX section detection in sectionizer prompt
class TestLatexSectionDetection:

    @pytest.fixture
    def latex_resume_sample(self):
        return (
            "1\t\\documentclass[11pt]{article}\n"
            "2\t\\usepackage{geometry}\n"
            "3\t\\begin{document}\n"
            "4\t\n"
            "5\t\\name{John Doe}\n"
            "6\t\\contact{john.doe@email.com}\n"
            "7\t\n"
            "8\t\\section{Professional Summary}\n"
            "9\tExperienced software engineer with 5+ years developing web applications.\n"
            "10\t\n"
            "11\t\\section*{Technical Skills}\n"
            "12\t• Python, JavaScript, React\n"
            "13\t• Docker, AWS, CI/CD\n"
            "14\t\n"
            "15\t\\sectionhead{Work Experience}\n"
            "16\tSenior Developer at Tech Corp (2020-2024)\n"
            "17\t• Built scalable web applications\n"
            "18\t\n"
            "19\t\\subsection{Education}\n"
            "20\tComputer Science BS, State University\n"
            "21\t\n"
            "22\t\\end{document}\n"
        )

    @pytest.fixture
    def mixed_latex_resume(self):
        return (
            "1\t\\documentclass{resume}\n"
            "2\t\\begin{document}\n"
            "3\t\n"
            "4\tJOHN DOE\n"
            "5\tSoftware Engineer\n"
            "6\t\n"
            "7\t\\section{SUMMARY}\n"
            "8\tSoftware engineer with expertise in web development.\n"
            "9\t\n"
            "10\tSKILLS\n"
            "11\t• Programming languages\n"
            "12\t\n"
            "13\t\\section*{Experience}\n"
            "14\tSenior Developer | Tech Corp | 2020-2024\n"
            "15\t\\end{document}\n"
        )

    # * Test LaTeX section detection instructions are present
    def test_latex_instructions_in_prompt(self, latex_resume_sample):
        prompt = build_sectionizer_prompt(latex_resume_sample)

        # LaTeX-specific instruction components
        assert "LaTeX Section Detection" in prompt
        assert "\\section{Title}" in prompt
        assert "\\section*{Title}" in prompt
        assert "\\sectionhead{Title}" in prompt
        assert "\\subsection{Title}" in prompt
        assert "\\subsubsection{Title}" in prompt

        # preamble handling instructions
        assert "\\documentclass" in prompt
        assert "\\usepackage" in prompt
        assert "\\begin{document}" in prompt
        assert "preamble" in prompt.lower()

        # content extraction guidance
        assert "Extract the title text from within the curly braces" in prompt
        assert "heading_text" in prompt

    # * Test LaTeX context notes are included
    def test_latex_context_notes(self, latex_resume_sample):
        prompt = build_sectionizer_prompt(latex_resume_sample)

        # LaTeX context guidance
        assert "LaTeX Context Notes" in prompt
        assert "LaTeX resumes typically start with preamble" in prompt
        assert "Section content appears between \\begin{document}" in prompt
        assert "Look for meaningful content sections" in prompt
        assert "Custom commands like \\sectionhead{}" in prompt
        assert "\\name{}, \\contact{}" in prompt

    # * Test schema includes LaTeX heading text format (short keys)
    def test_latex_schema_format(self, latex_resume_sample):
        prompt = build_sectionizer_prompt(latex_resume_sample)

        # schema should include LaTeX command format (check actual example w/ short keys)
        assert '"h": "Professional Summary"' in prompt  # short key for heading_text

        # should still include basic schema elements (short keys)
        assert '"k": "SUMMARY"' in prompt  # short key for kind
        assert '"s": 1' in prompt  # short key for start_line
        assert '"e": 5' in prompt  # short key for end_line
        assert '"c": 0.95' in prompt  # short key for confidence

    # * Test LaTeX resume content is preserved in prompt
    def test_latex_content_injection(self, latex_resume_sample):
        prompt = build_sectionizer_prompt(latex_resume_sample)

        # LaTeX resume content should be included
        assert latex_resume_sample in prompt
        assert "\\documentclass[11pt]{article}" in prompt
        assert "\\section{Professional Summary}" in prompt
        assert "\\section*{Technical Skills}" in prompt
        assert "\\sectionhead{Work Experience}" in prompt
        assert "\\subsection{Education}" in prompt

    # * Test mixed LaTeX & plain text handling
    def test_mixed_format_handling(self, mixed_latex_resume):
        prompt = build_sectionizer_prompt(mixed_latex_resume)

        # should handle both LaTeX commands & plain text headings
        assert "\\section{SUMMARY}" in prompt
        assert "SKILLS" in prompt  # plain text heading
        assert "\\section*{Experience}" in prompt

        # LaTeX instructions should still be present
        assert "LaTeX Section Detection" in prompt
        assert "meaningful content sections" in prompt

    # * Test preamble vs content section distinction
    def test_preamble_distinction_guidance(self, latex_resume_sample):
        prompt = build_sectionizer_prompt(latex_resume_sample)

        # guidance on what to ignore vs include
        assert "Ignore preamble commands" in prompt
        assert "these are setup, not content sections" in prompt
        assert "treat as OTHER if needed" in prompt

        # guidance on what to include
        assert "meaningful content sections" in prompt
        assert "not structural/formatting commands" in prompt

    # * Test LaTeX command variations are covered
    def test_latex_command_variations(self, latex_resume_sample):
        prompt = build_sectionizer_prompt(latex_resume_sample)

        # standard variations
        assert "\\section{Title}" in prompt
        assert "\\section*{Title}" in prompt

        # custom command variations
        assert "\\sectionhead{Title}" in prompt
        assert "\\subsection{Title}" in prompt
        assert "\\subsubsection{Title}" in prompt

        # document structure commands
        assert "\\documentclass" in prompt
        assert "\\usepackage" in prompt
        assert "\\begin{document}" in prompt

    # * Test LaTeX detection doesn't break regular resume processing
    def test_latex_additions_dont_break_regular_resumes(self):
        sample_resume_text = (
            "1\tJohn Doe\n"
            "2\tSoftware Engineer\n"
            "3\tjohn.doe@email.com\n"
            "4\t\n"
            "5\tPROFESSIONAL SUMMARY\n"
            "6\tExperienced developer with 5 years in web applications.\n"
            "7\t\n"
            "8\tTECHNICAL SKILLS\n"
            "9\t• Python, JavaScript, React\n"
            "10\t• AWS, Docker, PostgreSQL\n"
        )
        prompt = build_sectionizer_prompt(sample_resume_text)

        # regular resume content should still work
        assert sample_resume_text in prompt
        assert "PROFESSIONAL SUMMARY" in prompt
        assert "TECHNICAL SKILLS" in prompt

        # LaTeX instructions should be present but not interfering
        assert "LaTeX Section Detection" in prompt
        assert len(prompt) > 500  # substantial prompt
        assert "JSON schema" in prompt


# * Test build_prompt_operation_prompt for user-driven content generation
class TestPromptOperationPrompt:

    @pytest.fixture
    def sample_user_instruction(self):
        return "Make this sound more technical and focused on machine learning"

    @pytest.fixture
    def sample_operation_context(self):
        return "replace_line operation at line 5: 'Experienced software engineer'"

    @pytest.fixture
    def sample_job_text(self):
        return (
            "Senior ML Engineer - AI/ML Focus\n"
            "Requirements:\n"
            "- 5+ years Python/ML experience\n"
            "- TensorFlow, PyTorch proficiency\n"
            "- MLOps & deployment experience"
        )

    @pytest.fixture
    def sample_resume_text(self):
        return (
            "1\tJohn Doe\n"
            "2\tSoftware Engineer\n"
            "3\tjohn.doe@email.com\n"
            "4\t\n"
            "5\tPROFESSIONAL SUMMARY\n"
            "6\tExperienced developer with 5 years in web applications.\n"
            "7\t\n"
            "8\tTECHNICAL SKILLS\n"
            "9\t• Python, JavaScript, React\n"
            "10\t• AWS, Docker, PostgreSQL\n"
        )

    # * Test basic prompt assembly w/ all required components
    def test_prompt_operation_assembly(
        self, sample_user_instruction, sample_job_text, sample_resume_text
    ):
        prompt = build_prompt_operation_prompt(
            user_instruction=sample_user_instruction,
            operation_type="replace_line",
            operation_context="line 5 context",
            job_text=sample_job_text,
            resume_with_line_numbers=sample_resume_text,
            model="gpt-4",
            created_at="2024-01-01T00:00:00Z",
        )

        # basic sanity checks
        assert isinstance(prompt, str)
        assert len(prompt) > 200  # should be substantial

        # required components present
        assert sample_user_instruction in prompt
        assert "replace_line" in prompt
        assert sample_job_text in prompt
        assert sample_resume_text in prompt
        assert "gpt-4" in prompt
        assert "2024-01-01T00:00:00Z" in prompt

    # * Test JSON schema inclusion & format validation (short keys)
    def test_json_schema_in_prompt(
        self, sample_user_instruction, sample_job_text, sample_resume_text
    ):
        prompt = build_prompt_operation_prompt(
            user_instruction=sample_user_instruction,
            operation_type="replace_range",
            operation_context="multi-line context",
            job_text=sample_job_text,
            resume_with_line_numbers=sample_resume_text,
            model="claude-3",
            created_at="2024-01-01T00:00:00Z",
        )

        # JSON schema components (short keys)
        assert '"version": 1' in prompt
        assert '"ops": [' in prompt
        assert '"meta"' in prompt
        assert '"op": "replace_line"' in prompt
        assert '"t": "User-requested content"' in prompt  # short key for text
        assert '"cur": "Original"' in prompt  # short key for current_snippet
        assert '"w": "User instruction"' in prompt  # short key for why

    # * Test operation type handling for different edit types
    def test_operation_type_variants(
        self, sample_user_instruction, sample_job_text, sample_resume_text
    ):
        operation_types = [
            "replace_line",
            "replace_range",
            "insert_after",
            "delete_range",
        ]

        for op_type in operation_types:
            prompt = build_prompt_operation_prompt(
                user_instruction=sample_user_instruction,
                operation_type=op_type,
                operation_context=f"{op_type} context",
                job_text=sample_job_text,
                resume_with_line_numbers=sample_resume_text,
                model="test-model",
                created_at="2024-01-01T00:00:00Z",
            )

            assert f"Operation type: {op_type}" in prompt
            assert f"{op_type} context" in prompt

    # * Test optional sections_json parameter handling
    def test_sections_json_parameter(
        self, sample_user_instruction, sample_job_text, sample_resume_text
    ):
        sections_json = '{"sections": [{"name": "SUMMARY", "start_line": 5}]}'

        # test w/ sections_json provided
        prompt_with_sections = build_prompt_operation_prompt(
            user_instruction=sample_user_instruction,
            operation_type="replace_line",
            operation_context="context",
            job_text=sample_job_text,
            resume_with_line_numbers=sample_resume_text,
            model="test-model",
            created_at="2024-01-01T00:00:00Z",
            sections_json=sections_json,
        )

        # test w/o sections_json
        prompt_without_sections = build_prompt_operation_prompt(
            user_instruction=sample_user_instruction,
            operation_type="replace_line",
            operation_context="context",
            job_text=sample_job_text,
            resume_with_line_numbers=sample_resume_text,
            model="test-model",
            created_at="2024-01-01T00:00:00Z",
        )

        # both should be valid prompts
        assert len(prompt_with_sections) > 200
        assert len(prompt_without_sections) > 200

    # * Test prompt validation requirements & constraints (short keys)
    def test_prompt_validation_requirements(
        self, sample_user_instruction, sample_job_text, sample_resume_text
    ):
        prompt = build_prompt_operation_prompt(
            user_instruction=sample_user_instruction,
            operation_type="replace_line",
            operation_context="context",
            job_text=sample_job_text,
            resume_with_line_numbers=sample_resume_text,
            model="test-model",
            created_at="2024-01-01T00:00:00Z",
        )

        # validation requirements (condensed format)
        assert "VALIDATION" in prompt
        assert "ONE op" in prompt or "Exactly ONE" in prompt
        assert "cur matches" in prompt.lower()
        assert "bounded embellishment only" in prompt
        assert "t has no \\n" in prompt or "replace_line" in prompt

    # * Test user instruction content preservation
    def test_user_instruction_variants(self, sample_job_text, sample_resume_text):
        instructions = [
            "Make this more technical",
            "Add specific ML frameworks like TensorFlow",
            "Emphasize leadership experience",
            "Include quantifiable metrics and achievements",
        ]

        for instruction in instructions:
            prompt = build_prompt_operation_prompt(
                user_instruction=instruction,
                operation_type="replace_line",
                operation_context="test context",
                job_text=sample_job_text,
                resume_with_line_numbers=sample_resume_text,
                model="test-model",
                created_at="2024-01-01T00:00:00Z",
            )

            assert instruction in prompt
            assert len(prompt) > 500  # substantial prompt

    # * Test model & timestamp integration
    def test_model_and_timestamp_integration(
        self, sample_user_instruction, sample_job_text, sample_resume_text
    ):
        models = ["gpt-4", "claude-3-opus", "gpt-3.5-turbo", "claude-3-sonnet"]
        timestamps = ["2024-01-01T00:00:00Z", "2024-12-31T23:59:59Z"]

        for model in models:
            for timestamp in timestamps:
                prompt = build_prompt_operation_prompt(
                    user_instruction=sample_user_instruction,
                    operation_type="replace_line",
                    operation_context="context",
                    job_text=sample_job_text,
                    resume_with_line_numbers=sample_resume_text,
                    model=model,
                    created_at=timestamp,
                )

                assert f'"model": "{model}"' in prompt
                assert timestamp in prompt


# * Test _is_latex_content() helper function
class TestIsLatexContent:

    def test_docx_content_returns_false(self):
        """Plain text resume content should return False."""
        assert _is_latex_content("1\tJohn Doe\n2\tSoftware Engineer") is False

    def test_documentclass_at_start_returns_true(self):
        """Content starting with \\documentclass should return True."""
        assert _is_latex_content("\\documentclass{article}\n\\begin{document}") is True

    def test_documentclass_with_whitespace_returns_true(self):
        """Content with leading whitespace before \\documentclass should return True."""
        assert _is_latex_content("  \\documentclass{article}") is True

    def test_begin_document_anywhere_returns_true(self):
        """Content containing \\begin{document} anywhere should return True."""
        assert _is_latex_content("some preamble\n\\begin{document}") is True

    def test_empty_string_returns_false(self):
        """Empty string should return False."""
        assert _is_latex_content("") is False

    def test_whitespace_only_returns_false(self):
        """Whitespace-only content should return False."""
        assert _is_latex_content("   \n\t  ") is False

    def test_partial_markers_return_false(self):
        """Partial LaTeX markers should return False."""
        assert _is_latex_content("document class article") is False
        assert _is_latex_content("begin document") is False

    def test_numbered_lines_latex_returns_true(self):
        """Numbered LaTeX resume lines should return True."""
        content = (
            "1\t\\documentclass[11pt]{article}\n"
            "2\t\\usepackage{geometry}\n"
            "3\t\\begin{document}"
        )
        assert _is_latex_content(content) is True
