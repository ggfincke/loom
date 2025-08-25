# tests/unit/test_special_operations.py
# Unit tests for PROMPT & MODIFY special operations functionality

import pytest
from unittest.mock import patch, MagicMock
from src.core.pipeline import process_prompt_operation, process_modify_operation
from src.core.constants import EditOperation, DiffOp
from src.core.exceptions import EditError
from src.loom_io.types import Lines


# * Fixtures for special operations testing

@pytest.fixture
def sample_resume_lines() -> Lines:
    return {
        1: "John Doe",
        2: "Senior Software Engineer",
        3: "",
        4: "PROFESSIONAL SUMMARY",
        5: "Software engineer with 5+ years experience in web development",
        6: "and cloud architecture. Proven track record of delivering",
        7: "scalable applications using modern technologies.",
        8: "",
        9: "TECHNICAL SKILLS", 
        10: "• Python, JavaScript, TypeScript",
        11: "• React, Node.js, Django",
        12: "• AWS, Docker, Kubernetes",
        13: "",
        14: "WORK EXPERIENCE",
        15: "Senior Software Engineer | Tech Corp | 2020-2024",
        16: "• Led development of microservices architecture",
        17: "• Implemented CI/CD pipelines reducing deployment time by 60%",
        18: "• Mentored junior developers and conducted code reviews"
    }

@pytest.fixture  
def sample_job_description():
    return (
        "Senior Machine Learning Engineer\n"
        "Requirements:\n"
        "- 5+ years Python/ML experience\n"
        "- TensorFlow, PyTorch, scikit-learn proficiency\n"  
        "- Experience with MLOps, model deployment\n"
        "- Strong background in statistical analysis\n"
        "- Experience with cloud ML services (AWS SageMaker, GCP AI Platform)"
    )

@pytest.fixture
def sections_json_sample():
    return '{"sections": [{"name": "SUMMARY", "start_line": 4, "end_line": 7}, {"name": "SKILLS", "start_line": 9, "end_line": 12}]}'


# * Test process_modify_operation functionality
class TestProcessModifyOperation:
    
    @pytest.fixture
    def replace_line_operation(self):
        return EditOperation(
            operation="replace_line",
            line_number=5,
            content="Original content before modification",
            modified_content="User-modified content with specific changes",
            reasoning="User manually edited this content",
            confidence=0.8,
            original_content="Software engineer with 5+ years experience"
        )
    
    @pytest.fixture
    def replace_range_operation(self):
        return EditOperation(
            operation="replace_range",
            line_number=5,
            start_line=5,
            end_line=7,
            content="Original multi-line content",
            modified_content="User-modified multi-line content\nwith specific technical details\nand enhanced formatting",
            reasoning="User wants more technical focus",
            confidence=0.9
        )
    
    # * Test successful MODIFY operation processing
    def test_process_modify_operation_success(self, replace_line_operation):
        result = process_modify_operation(replace_line_operation)
        
        # verify content was updated w/ user modifications
        assert result.content == "User-modified content with specific changes"
        assert result.operation == "replace_line"
        assert result.line_number == 5
        assert result.reasoning == "User manually edited this content"
        assert result.confidence == 0.8
        
        # original fields should be preserved
        assert result.original_content == "Software engineer with 5+ years experience"
    
    # * Test MODIFY operation w/ multi-line content
    def test_process_modify_operation_multiline(self, replace_range_operation):
        result = process_modify_operation(replace_range_operation)
        
        # verify multi-line content handling
        assert result.content == "User-modified multi-line content\nwith specific technical details\nand enhanced formatting"
        assert result.operation == "replace_range"
        assert result.start_line == 5
        assert result.end_line == 7
        
        # should handle newlines correctly
        assert "\n" in result.content
        assert result.content.count("\n") == 2
    
    # * Test MODIFY operation error w/ missing modified_content
    def test_process_modify_operation_missing_content(self):
        operation = EditOperation(
            operation="replace_line",
            line_number=5,
            content="Original content",
            modified_content=None,  # missing required field
            reasoning="Test operation"
        )
        
        with pytest.raises(EditError) as exc_info:
            process_modify_operation(operation)
        
        assert "MODIFY operation requires modified_content to be set" in str(exc_info.value)
    
    # * Test MODIFY operation w/ empty modified_content
    def test_process_modify_operation_empty_content(self):
        operation = EditOperation(
            operation="replace_line",
            line_number=5,
            content="Original content",
            modified_content="",  # empty but not None
            reasoning="User cleared content"
        )
        
        result = process_modify_operation(operation)
        assert result.content == ""  # should accept empty string
    
    # * Test MODIFY operation preserves all other fields
    def test_process_modify_operation_field_preservation(self):
        operation = EditOperation(
            operation="insert_after",
            line_number=10,
            start_line=None,
            end_line=None, 
            content="Original content",
            modified_content="User-modified insertion content",
            reasoning="Insert new skill",
            confidence=0.95,
            status=DiffOp.APPROVE,
            before_context=["Context line 1", "Context line 2"],
            after_context=["Context line 3"],
            original_content="N/A for insertion"
        )
        
        result = process_modify_operation(operation)
        
        # verify all fields preserved except content
        assert result.operation == "insert_after"
        assert result.line_number == 10
        assert result.content == "User-modified insertion content"
        assert result.reasoning == "Insert new skill"
        assert result.confidence == 0.95
        assert result.status == DiffOp.APPROVE
        assert result.before_context == ["Context line 1", "Context line 2"]
        assert result.after_context == ["Context line 3"]
        assert result.original_content == "N/A for insertion"
    
    # * Test MODIFY operation w/ different operation types
    def test_process_modify_operation_all_types(self):
        operation_types = ["replace_line", "replace_range", "insert_after", "delete_range"]
        
        for op_type in operation_types:
            operation = EditOperation(
                operation=op_type,
                line_number=5,
                start_line=5 if op_type in ["replace_range", "delete_range"] else None,
                end_line=6 if op_type in ["replace_range", "delete_range"] else None,
                content=f"Original {op_type} content",
                modified_content=f"Modified {op_type} content by user",
                reasoning=f"Test {op_type} modification"
            )
            
            result = process_modify_operation(operation)
            
            assert result.operation == op_type
            assert result.content == f"Modified {op_type} content by user"
            assert result.reasoning == f"Test {op_type} modification"


# * Test enhanced process_prompt_operation functionality  
class TestProcessPromptOperationAdvanced:
    
    @pytest.fixture
    def prompt_operation_replace_line(self):
        return EditOperation(
            operation="replace_line",
            line_number=5,
            content="Software engineer with 5+ years experience in web development",
            prompt_instruction="Make this more technical and focus on machine learning experience",
            reasoning="User wants ML-focused content",
            confidence=0.7,
            original_content="Software engineer with 5+ years experience",
            before_context=["PROFESSIONAL SUMMARY", ""],
            after_context=["and cloud architecture.", "scalable applications."]
        )
    
    @pytest.fixture
    def prompt_operation_insert_after(self):
        return EditOperation(
            operation="insert_after",
            line_number=12,
            content="",
            prompt_instruction="Add a bullet point about MLOps and model deployment experience",
            reasoning="User wants to add ML deployment skills",
            confidence=0.8,
            before_context=["• AWS, Docker, Kubernetes"],
            after_context=["", "WORK EXPERIENCE"]
        )
    
    @pytest.fixture
    def mock_successful_ai_response(self):
        return MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {
                    "strategy": "prompt_regeneration",
                    "model": "gpt-4",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "ops": [{
                    "op": "replace_line",
                    "line": 5,
                    "text": "Machine learning engineer w/ 5+ years experience in ML model development, TensorFlow & PyTorch",
                    "current_snippet": "Software engineer with 5+ years experience",
                    "why": "Enhanced technical focus w/ ML frameworks as requested"
                }]
            },
            error=None
        )
    
    # * Test successful PROMPT operation w/ context building
    @patch('src.core.pipeline.run_generate')
    @patch('src.core.pipeline.build_prompt_operation_prompt')
    def test_process_prompt_operation_context_building(self, mock_build_prompt, mock_run_generate, 
                                                      prompt_operation_replace_line, sample_resume_lines, 
                                                      sample_job_description, mock_successful_ai_response):
        mock_build_prompt.return_value = "Generated prompt"
        mock_run_generate.return_value = mock_successful_ai_response
        
        result = process_prompt_operation(
            edit_op=prompt_operation_replace_line,
            resume_lines=sample_resume_lines,
            job_text=sample_job_description,
            sections_json=None,
            model="gpt-4"
        )
        
        # verify result is an EditOperation
        assert isinstance(result, EditOperation)
        
        # verify prompt builder was called w/ correct context
        mock_build_prompt.assert_called_once()
        call_kwargs = mock_build_prompt.call_args[1] if mock_build_prompt.call_args[1] else {}
        call_args = mock_build_prompt.call_args[0] if mock_build_prompt.call_args[0] else []
        
        # check user instruction preservation
        user_instruction = call_args[0] if call_args else call_kwargs.get('user_instruction')
        assert user_instruction == "Make this more technical and focus on machine learning experience"
        
        # check operation context includes line info
        operation_context = call_args[2] if len(call_args) > 2 else call_kwargs.get('operation_context')
        assert operation_context is not None, "operation_context should not be None"
        assert "Original line 5" in operation_context
        assert "Context before" in operation_context
        assert "Context after" in operation_context
    
    # * Test PROMPT operation error w/ missing prompt_instruction
    def test_process_prompt_operation_missing_instruction(self, sample_resume_lines, sample_job_description):
        operation = EditOperation(
            operation="replace_line",
            line_number=5,
            content="Test content",
            prompt_instruction=None,  # missing required field
            reasoning="Test operation"
        )
        
        with pytest.raises(EditError) as exc_info:
            process_prompt_operation(
                edit_op=operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_description,
                sections_json=None,
                model="gpt-4"
            )
        
        assert "PROMPT operation requires prompt_instruction to be set" in str(exc_info.value)
    
    # * Test PROMPT operation w/ insert_after context
    @patch('src.core.pipeline.run_generate')
    @patch('src.core.pipeline.build_prompt_operation_prompt')
    def test_process_prompt_operation_insert_context(self, mock_build_prompt, mock_run_generate,
                                                    prompt_operation_insert_after, sample_resume_lines,
                                                    sample_job_description):
        mock_build_prompt.return_value = "Generated prompt"
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration"},
                "ops": [{
                    "op": "insert_after",
                    "text": "• MLOps pipeline development w/ Kubernetes & Docker",
                    "why": "Added MLOps experience as requested"
                }]
            },
            error=None
        )
        
        process_prompt_operation(
            edit_op=prompt_operation_insert_after,
            resume_lines=sample_resume_lines,
            job_text=sample_job_description,
            sections_json=None,
            model="gpt-4"
        )
        
        # verify context includes insertion info
        mock_build_prompt.assert_called_once()
        call_kwargs = mock_build_prompt.call_args.kwargs
        operation_context = call_kwargs['operation_context']
        assert "Inserting after line 12" in operation_context
    
    # * Test PROMPT operation w/ sections_json integration
    @patch('src.core.pipeline.run_generate')
    @patch('src.core.pipeline.build_prompt_operation_prompt') 
    def test_process_prompt_operation_with_sections(self, mock_build_prompt, mock_run_generate,
                                                   prompt_operation_replace_line, sample_resume_lines,
                                                   sample_job_description, sections_json_sample,
                                                   mock_successful_ai_response):
        mock_build_prompt.return_value = "Generated prompt"
        mock_run_generate.return_value = mock_successful_ai_response
        
        process_prompt_operation(
            edit_op=prompt_operation_replace_line,
            resume_lines=sample_resume_lines,
            job_text=sample_job_description,
            sections_json=sections_json_sample,
            model="gpt-4"
        )
        
        # verify sections_json was passed through
        call_kwargs = mock_build_prompt.call_args[1] if mock_build_prompt.call_args[1] else {}
        call_args = mock_build_prompt.call_args[0] if mock_build_prompt.call_args[0] else []
        
        sections_param = call_kwargs.get('sections_json') or (call_args[7] if len(call_args) > 7 else None)
        assert sections_param == sections_json_sample
    
    # * Test operation type specific context building
    @patch('src.core.pipeline.run_generate')
    @patch('src.core.pipeline.build_prompt_operation_prompt')
    def test_process_prompt_operation_type_contexts(self, mock_build_prompt, mock_run_generate,
                                                   sample_resume_lines, sample_job_description):
        mock_build_prompt.return_value = "Generated prompt"
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration"},
                "ops": [{"op": "test", "text": "test content", "why": "test reason"}]
            },
            error=None
        )
        
        # test different operation types & their context building
        test_cases = [
            ("replace_line", 5, None, None, "Original line 5:"),
            ("replace_range", 5, 5, 7, "Original lines 5-7:"),
            ("insert_after", 10, None, None, "Inserting after line 10"),
            ("delete_range", 8, 8, 9, "Deleting lines 8-9:")
        ]
        
        for op_type, line_num, start_line, end_line, expected_context in test_cases:
            operation = EditOperation(
                operation=op_type,
                line_number=line_num,
                start_line=start_line,
                end_line=end_line,
                prompt_instruction="Test instruction",
                original_content="Test original content"
            )
            
            process_prompt_operation(
                edit_op=operation,
                resume_lines=sample_resume_lines,
                job_text=sample_job_description,
                sections_json=None,
                model="gpt-4"
            )
            
            # verify operation-specific context was built
            call_kwargs = mock_build_prompt.call_args.kwargs
            operation_context = call_kwargs['operation_context']
            assert expected_context in operation_context
            
            # reset mock for next iteration
            mock_build_prompt.reset_mock()


# * Test integration scenarios between PROMPT & MODIFY operations
class TestSpecialOperationsIntegration:
    
    # * Test operation status transitions through special operations
    def test_operation_status_workflow(self):
        # create base operation
        operation = EditOperation(
            operation="replace_line",
            line_number=5,
            content="Original content",
            reasoning="Initial reasoning",
            confidence=0.6,
            status=DiffOp.SKIP,
            modified_content="User edited content",
            prompt_instruction="Make this more technical"
        )
        
        # test MODIFY flow
        modified_op = process_modify_operation(operation)
        assert modified_op.content == "User edited content"
        assert modified_op.status == DiffOp.SKIP  # status preserved
        
        # test that original operation fields remain intact for PROMPT processing
        assert operation.prompt_instruction == "Make this more technical"
    
    # * Test field preservation across operations
    def test_field_preservation_across_operations(self):
        operation = EditOperation(
            operation="replace_line",
            line_number=10,
            content="Original test content",
            reasoning="Initial test reasoning",
            confidence=0.75,
            status=DiffOp.APPROVE,
            before_context=["Before 1", "Before 2"],
            after_context=["After 1"],
            original_content="Very original content",
            modified_content="User modified this content",
            prompt_instruction="Enhance this technically"
        )
        
        # process through MODIFY operation
        result = process_modify_operation(operation)
        
        # verify all fields preserved except content update
        assert result.operation == "replace_line"
        assert result.line_number == 10
        assert result.content == "User modified this content"  # updated
        assert result.reasoning == "Initial test reasoning"  # preserved
        assert result.confidence == 0.75  # preserved
        assert result.status == DiffOp.APPROVE  # preserved
        assert result.before_context == ["Before 1", "Before 2"]  # preserved
        assert result.after_context == ["After 1"]  # preserved
        assert result.original_content == "Very original content"  # preserved
        assert result.modified_content == "User modified this content"  # preserved
        assert result.prompt_instruction == "Enhance this technically"  # preserved
    
    # * Test error handling consistency
    def test_error_handling_consistency(self):
        # test MODIFY w/ missing required field
        modify_op = EditOperation(
            operation="replace_line",
            line_number=5,
            modified_content=None  # missing
        )
        
        with pytest.raises(EditError) as modify_exc:
            process_modify_operation(modify_op)
        
        assert "modified_content" in str(modify_exc.value)
        
        # test PROMPT w/ missing required field  
        prompt_op = EditOperation(
            operation="replace_line", 
            line_number=5,
            prompt_instruction=None  # missing
        )
        
        with pytest.raises(EditError) as prompt_exc:
            process_prompt_operation(
                edit_op=prompt_op,
                resume_lines={1: "test"},
                job_text="test job",
                sections_json=None,
                model="test-model"
            )
        
        assert "prompt_instruction" in str(prompt_exc.value)