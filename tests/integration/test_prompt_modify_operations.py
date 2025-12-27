# tests/integration/test_prompt_modify_operations.py
# Integration tests for PROMPT & MODIFY operation end-to-end workflows

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.core.pipeline import apply_edits, generate_edits
from src.core.constants import EditOperation, DiffOp
from src.core.exceptions import EditError, AIError
from src.loom_io.types import Lines
from src.loom_io.documents import read_resume
from src.config.settings import SettingsManager


# * Fixtures for integration testing


@pytest.fixture
def temp_resume_file():
    # Create a temporary resume file for testing
    content = """John Doe
Senior Software Engineer
john.doe@email.com

PROFESSIONAL SUMMARY
Software engineer with 5+ years experience developing web applications
and building scalable systems using modern technologies.

TECHNICAL SKILLS  
• Python, JavaScript, TypeScript
• React, Node.js, Django, FastAPI
• AWS, Docker, Kubernetes
• PostgreSQL, MongoDB, Redis

WORK EXPERIENCE
Senior Software Engineer | Tech Corp | 2020-2024
• Led development of microservices architecture
• Implemented CI/CD pipelines reducing deployment time by 60%
• Mentored junior developers and conducted code reviews

Software Engineer | StartupCo | 2018-2020  
• Built full-stack web applications using Python/React
• Designed and implemented RESTful APIs
• Collaborated with product team on feature development"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def ml_job_description():
    return """Senior Machine Learning Engineer
Company: AI Innovations Inc.

Requirements:
- 5+ years experience in machine learning and data science
- Expert-level proficiency in Python, TensorFlow, PyTorch
- Experience with MLOps, model deployment, and monitoring
- Strong background in statistical analysis and data visualization
- Experience with cloud ML platforms (AWS SageMaker, GCP AI Platform)
- Knowledge of distributed computing frameworks (Spark, Dask)
- Experience with containerization and orchestration (Docker, Kubernetes)

Preferred:
- PhD in Computer Science, Statistics, or related field
- Published research in machine learning conferences
- Experience with reinforcement learning and deep learning
- Familiarity with MLflow, Kubeflow, or similar ML platforms"""


@pytest.fixture
def sample_edits_with_special_ops():
    # Edits containing both regular & special operations
    return {
        "version": 1,
        "meta": {
            "model": "gpt-4",
            "created_at": "2024-01-01T00:00:00Z",
            "strategy": "job_tailoring",
        },
        "ops": [
            {
                "op": "replace_line",
                "line": 6,
                "text": "Machine learning engineer with 5+ years experience in ML model development",
                "current_snippet": "Software engineer with 5+ years experience developing web applications",
                "why": "Align summary with ML role requirements",
            },
            {
                "op": "replace_range",
                "start": 10,
                "end": 12,
                "text": "• Python, TensorFlow, PyTorch, scikit-learn\n• MLOps tools: MLflow, Kubeflow, SageMaker\n• Cloud ML platforms: AWS, GCP, Azure ML",
                "current_snippet": "• Python, JavaScript, TypeScript\n• React, Node.js, Django, FastAPI\n• AWS, Docker, Kubernetes",
                "why": "Update skills to match ML requirements",
            },
            {
                "op": "insert_after",
                "line": 12,
                "text": "• Statistical analysis, data visualization (matplotlib, seaborn)",
                "why": "Add statistical analysis skills mentioned in job requirements",
            },
        ],
    }


@pytest.fixture
def resume_lines_from_temp_file(temp_resume_file):
    # Load resume lines from temp file
    lines = {}
    with open(temp_resume_file, "r") as f:
        for i, line in enumerate(f.readlines(), 1):
            lines[i] = line.rstrip("\n")
    return lines


# * Integration test for complete PROMPT operation workflow
class TestPromptOperationIntegration:

    @patch("src.core.pipeline.run_generate")
    # * Verify prompt operation end to end
    def test_prompt_operation_end_to_end(
        self, mock_run_generate, resume_lines_from_temp_file, ml_job_description
    ):
        # Test complete PROMPT operation from user input to applied changes

        # mock AI response
        mock_run_generate.return_value = MagicMock(
            success=True,
            data={
                "version": 1,
                "meta": {"strategy": "prompt_regeneration", "model": "gpt-4"},
                "ops": [
                    {
                        "op": "replace_line",
                        "line": 6,
                        "text": "Machine learning engineer with 5+ years experience in TensorFlow, PyTorch, and statistical modeling",
                        "current_snippet": "Software engineer with 5+ years experience developing web applications",
                        "why": "Enhanced w/ specific ML frameworks and statistical focus as requested",
                    }
                ],
            },
            error=None,
            raw_text=None,
        )

        # create operation w/ PROMPT status
        operation = EditOperation(
            operation="replace_line",
            line_number=6,
            content="Software engineer with 5+ years experience developing web applications",
            original_content="Software engineer with 5+ years experience developing web applications",
            prompt_instruction="Make this more technical with specific ML frameworks and statistical focus",
            reasoning="User wants ML-specific content",
            confidence=0.8,
            status=DiffOp.PROMPT,
        )

        # create mock edits structure
        edits_data = {
            "version": 1,
            "meta": {"model": "gpt-4", "created_at": "2024-01-01T00:00:00Z"},
            "ops": [
                {
                    "op": "replace_line",
                    "line": 6,
                    "text": operation.content,
                    "current_snippet": operation.original_content,
                    "why": operation.reasoning,
                }
            ],
        }

        # simulate processing edits w/ PROMPT operations
        from src.core.pipeline import process_prompt_operation

        # process the PROMPT operation
        result_op = process_prompt_operation(
            edit_op=operation,
            resume_lines=resume_lines_from_temp_file,
            job_text=ml_job_description,
            sections_json=None,
            model="gpt-4",
        )

        # verify the operation was updated
        assert "Machine learning engineer" in result_op.content
        assert "TensorFlow" in result_op.content
        assert "PyTorch" in result_op.content
        assert "statistical modeling" in result_op.content
        assert result_op.confidence == 0.9  # should be high for user-requested content

        # test applying the processed operation
        processed_edits = {
            "version": 1,
            "meta": {"model": "gpt-4", "created_at": "2024-01-01T00:00:00Z"},
            "ops": [
                {
                    "op": result_op.operation,
                    "line": result_op.line_number,
                    "text": result_op.content,
                    "current_snippet": result_op.original_content,
                    "why": result_op.reasoning,
                }
            ],
        }

        # apply edits & verify changes
        result_lines = apply_edits(resume_lines_from_temp_file, processed_edits)

        assert result_lines[6] == result_op.content
        assert "Machine learning engineer" in result_lines[6]

    # * Verify prompt operation w/ sections context
    def test_prompt_operation_with_sections_context(
        self, resume_lines_from_temp_file, ml_job_description
    ):
        # Test PROMPT operation w/ sections context for better targeting

        sections_json = json.dumps(
            {
                "sections": [
                    {
                        "name": "SUMMARY",
                        "start_line": 5,
                        "end_line": 7,
                        "confidence": 0.9,
                    },
                    {
                        "name": "SKILLS",
                        "start_line": 9,
                        "end_line": 12,
                        "confidence": 0.95,
                    },
                ]
            }
        )

        operation = EditOperation(
            operation="replace_line",
            line_number=6,
            prompt_instruction="Make this summary more quantitative with specific ML achievements",
            original_content="Software engineer with 5+ years experience developing web applications",
            status=DiffOp.PROMPT,
        )

        with patch("src.core.pipeline.run_generate") as mock_run_generate:
            mock_run_generate.return_value = MagicMock(
                success=True,
                data={
                    "version": 1,
                    "meta": {"strategy": "prompt_regeneration"},
                    "ops": [
                        {
                            "op": "replace_line",
                            "text": "ML engineer w/ 5+ years delivering 15+ production models, achieving 23% accuracy improvement",
                            "why": "Added quantitative metrics and ML-specific achievements",
                        }
                    ],
                },
                error=None,
            )

            from src.core.pipeline import process_prompt_operation

            result = process_prompt_operation(
                edit_op=operation,
                resume_lines=resume_lines_from_temp_file,
                job_text=ml_job_description,
                sections_json=sections_json,
                model="gpt-4",
            )

        # verify quantitative content was generated
        assert "15+" in result.content or "23%" in result.content
        assert "ML engineer" in result.content or "production models" in result.content


# * Integration tests for mixed workflows (both PROMPT & MODIFY operations)
class TestMixedSpecialOperationsWorkflow:

    # * Verify mixed operations in single edit session
    def test_mixed_operations_in_single_edit_session(
        self, resume_lines_from_temp_file, ml_job_description
    ):
        # Test applying both PROMPT & MODIFY operations in single session

        # create mixed operations
        prompt_op = EditOperation(
            operation="replace_line",
            line_number=6,
            prompt_instruction="Make this summary highlight ML model deployment experience",
            original_content="Software engineer with 5+ years experience developing web applications",
            status=DiffOp.PROMPT,
        )

        modify_op = EditOperation(
            operation="insert_after",
            line_number=12,
            content="• Deep learning architectures: CNNs, RNNs, Transformers",
            reasoning="User manually added deep learning skills",
            status=DiffOp.MODIFY,
        )

        # process PROMPT operation
        with patch("src.core.pipeline.run_generate") as mock_run_generate:
            mock_run_generate.return_value = MagicMock(
                success=True,
                data={
                    "version": 1,
                    "meta": {"strategy": "prompt_regeneration"},
                    "ops": [
                        {
                            "op": "replace_line",
                            "text": "ML engineer with 5+ years experience deploying production models using MLOps best practices",
                            "why": "Emphasized ML model deployment experience as requested",
                        }
                    ],
                },
                error=None,
            )

            from src.core.pipeline import (
                process_prompt_operation,
                process_modify_operation,
            )

            processed_prompt = process_prompt_operation(
                edit_op=prompt_op,
                resume_lines=resume_lines_from_temp_file,
                job_text=ml_job_description,
                sections_json=None,
                model="gpt-4",
            )

        # process MODIFY operation
        processed_modify = process_modify_operation(modify_op)

        # create combined edits
        combined_edits = {
            "version": 1,
            "meta": {"model": "mixed", "created_at": "2024-01-01T00:00:00Z"},
            "ops": [
                {
                    "op": processed_prompt.operation,
                    "line": processed_prompt.line_number,
                    "text": processed_prompt.content,
                    "why": processed_prompt.reasoning,
                },
                {
                    "op": processed_modify.operation,
                    "line": processed_modify.line_number,
                    "text": processed_modify.content,
                    "why": processed_modify.reasoning,
                },
            ],
        }

        # apply combined edits
        result_lines = apply_edits(resume_lines_from_temp_file, combined_edits)

        # verify both operations were applied
        assert "ML engineer" in result_lines[6]
        assert "production models" in result_lines[6]
        assert (
            "Deep learning architectures" in result_lines[13]
        )  # inserted after line 12
        assert "CNNs, RNNs, Transformers" in result_lines[13]

    # * Verify operation dependencies & line shifts
    def test_operation_dependencies_and_line_shifts(self, resume_lines_from_temp_file):
        # Test that operations handle line number shifts from previous operations

        # operations that will shift line numbers
        insert_op = EditOperation(
            operation="insert_after",
            line_number=8,  # insert after line 8
            content="Additional technical expertise in machine learning",
            status=DiffOp.MODIFY,
        )

        modify_op = EditOperation(
            operation="replace_line",
            line_number=10,  # this will become line 11 after insert
            content="• Advanced Python, TensorFlow 2.x, PyTorch Lightning",
            status=DiffOp.MODIFY,
        )

        # process operations
        from src.core.pipeline import process_modify_operation

        processed_insert = process_modify_operation(insert_op)
        processed_modify = process_modify_operation(modify_op)

        # create edits in order
        edits = {
            "version": 1,
            "meta": {"model": "user_modified", "created_at": "2024-01-01T00:00:00Z"},
            "ops": [
                {
                    "op": processed_insert.operation,
                    "line": processed_insert.line_number,
                    "text": processed_insert.content,
                    "why": processed_insert.reasoning,
                },
                {
                    "op": processed_modify.operation,
                    "line": processed_modify.line_number,
                    "text": processed_modify.content,
                    "why": processed_modify.reasoning,
                },
            ],
        }

        # apply edits
        result_lines = apply_edits(resume_lines_from_temp_file, edits)

        # verify insertion happened
        assert "machine learning" in result_lines[9]  # inserted after line 8

        # verify modification happened at correct shifted line
        assert (
            "TensorFlow 2.x" in result_lines[11]
            or "PyTorch Lightning" in result_lines[11]
        )


# * Error handling integration tests
class TestSpecialOperationsErrorHandling:

    # * Verify prompt operation ai failure recovery
    def test_prompt_operation_ai_failure_recovery(
        self, resume_lines_from_temp_file, ml_job_description
    ):
        # Test error handling when AI fails during PROMPT operation

        operation = EditOperation(
            operation="replace_line",
            line_number=6,
            prompt_instruction="Make this more technical",
            status=DiffOp.PROMPT,
        )

        with patch("src.core.pipeline.run_generate") as mock_run_generate:
            mock_run_generate.return_value = MagicMock(
                success=False, error="API rate limit exceeded", data=None
            )

            from src.core.pipeline import process_prompt_operation

            with pytest.raises(AIError) as exc_info:
                process_prompt_operation(
                    edit_op=operation,
                    resume_lines=resume_lines_from_temp_file,
                    job_text=ml_job_description,
                    sections_json=None,
                    model="gpt-4",
                )

            assert "AI failed to process PROMPT operation" in str(exc_info.value)
            assert "API rate limit exceeded" in str(exc_info.value)

    # * Verify modify operation missing fields
    def test_modify_operation_missing_fields(self):
        # Test error handling for MODIFY operations w/ missing fields

        operation = EditOperation(
            operation="replace_line",
            line_number=6,
            content="",  # empty content should fail
            status=DiffOp.MODIFY,
        )

        from src.core.pipeline import process_modify_operation

        with pytest.raises(EditError) as exc_info:
            process_modify_operation(operation)

        assert "MODIFY operation requires content to be set" in str(exc_info.value)

    @patch("src.core.pipeline.run_generate")
    # * Verify invalid ai response handling
    def test_invalid_ai_response_handling(
        self, mock_run_generate, resume_lines_from_temp_file, ml_job_description
    ):
        # Test handling of invalid AI responses during PROMPT operations

        # test different types of invalid responses
        invalid_responses = [
            MagicMock(success=True, data="Invalid string response", error=None),
            MagicMock(success=True, data={"invalid": "structure"}, error=None),
            MagicMock(
                success=True, data={"version": 2, "ops": []}, error=None
            ),  # wrong version
            MagicMock(success=True, data={"version": 1}, error=None),  # missing ops
        ]

        operation = EditOperation(
            operation="replace_line",
            line_number=6,
            prompt_instruction="Test instruction",
            status=DiffOp.PROMPT,
        )

        from src.core.pipeline import process_prompt_operation

        for invalid_response in invalid_responses:
            mock_run_generate.return_value = invalid_response

            with pytest.raises(AIError):
                process_prompt_operation(
                    edit_op=operation,
                    resume_lines=resume_lines_from_temp_file,
                    job_text=ml_job_description,
                    sections_json=None,
                    model="gpt-4",
                )
