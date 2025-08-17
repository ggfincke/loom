# tests/unit/test_ai_prompts.py
# Unit tests for AI prompt assembly & validation

import pytest

from src.ai.prompts import (
    build_sectionizer_prompt,
    build_generate_prompt, 
    build_edit_prompt
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
            created_at=created_at
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
        assert "EXACT" in prompt  # emphasis on exactness
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
    def test_generate_prompt_with_sections(self, sample_job_info, sample_resume_text, sample_sections_json):
        prompt = build_generate_prompt(
            job_info=sample_job_info,
            resume_with_line_numbers=sample_resume_text,
            model="claude-sonnet-4",
            created_at="2024-01-15T10:30:00Z",
            sections_json=sample_sections_json
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
            "line 999 not in resume bounds"
        ]
        
        prompt = build_edit_prompt(
            job_info=sample_job_info,
            resume_with_line_numbers=sample_resume_text,
            edits_json=edits_json,
            validation_errors=validation_errors,
            model=model,
            created_at=created_at
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
            "1\tName with \"quotes\" & special chars\n"
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
            created_at="2024-01-15T12:00:00Z"
        )
        assert len(prompt2) > 100
        assert problematic_job in prompt2
        assert problematic_resume in prompt2


class TestPromptRequiredElements:
    """Test prompts contain all necessary instructional elements"""
    
    def test_sectionizer_schema_completeness(self):
        """Ensure sectionizer prompt defines complete JSON schema"""
        prompt = build_sectionizer_prompt("1\tTest Resume\n")
        
        # schema field requirements
        required_fields = [
            "sections", "name", "heading_text", "start_line", "end_line", 
            "confidence", "subsections", "normalized_order", "notes"
        ]
        
        for field in required_fields:
            assert field in prompt, f"Missing required schema field: {field}"
        
        # data type specifications
        assert "<int>" in prompt
        assert "<float>" in prompt
        assert '"string"' in prompt
    
    def test_generate_operation_schema_completeness(self):
        """Ensure generate prompt defines all operation schemas"""
        prompt = build_generate_prompt(
            job_info="Test job",
            resume_with_line_numbers="1\tTest\n",
            model="test-model",
            created_at="2024-01-15T12:00:00Z"
        )
        
        # operation requirements
        operations = ["replace_line", "replace_range", "insert_after", "delete_range"]
        for op in operations:
            assert op in prompt, f"Missing operation type: {op}"
        
        # required fields per operation
        assert '"line": <int>' in prompt
        assert '"start": <int>' in prompt
        assert '"end": <int>' in prompt
        assert '"text": "string"' in prompt
        assert '"current_snippet": "string"' in prompt
        assert '"why": "string (optional)"' in prompt
    
    def test_validation_checklist_presence(self):
        """Ensure prompts include validation checklists"""
        prompt = build_generate_prompt(
            job_info="Test",
            resume_with_line_numbers="1\tTest\n", 
            model="test",
            created_at="2024-01-15T12:00:00Z"
        )
        
        # validation checklist elements
        assert "VALIDATION CHECKLIST" in prompt or "validate before outputting" in prompt.lower()
        assert "no unescaped quotes" in prompt.lower()
        assert "line numbers exist" in prompt.lower()


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
            created_at="2024-01-15T12:00:00Z"
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
            created_at="2024-01-15T12:00:00Z"
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
            sections_json=None  # explicit None
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
            "created_at": "2024-01-15T12:00:00Z"
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
                created_at=timestamp
            )
            assert timestamp in prompt
