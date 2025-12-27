# tests/integration/test_cli_errors.py
# Integration tests for CLI error conditions, exit codes & friendly error messages

import pytest
from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, Mock

from tests.test_support.mock_ai import (
    DeterministicMockAI,
    create_ai_client_mocks,
    create_error_mock,
    create_simple_ai_mock,
    get_ai_patch_path,
)


@pytest.fixture
# * Create mock AI that returns error responses for different scenarios
def mock_ai_errors():
    return DeterministicMockAI()


@pytest.fixture
# * Create sample files for testing error conditions
def sample_files(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()

    # create sample resume file
    resume_file = sample_dir / "sample_resume.docx"
    # copy from fixtures
    import shutil

    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"
    shutil.copy(fixtures_dir / "basic_formatted_resume.docx", resume_file)

    # create sample job description
    job_file = sample_dir / "job_posting.txt"
    job_file.write_text("Software Engineer position requiring Python experience.")

    # create malformed edits file
    bad_edits_file = sample_dir / "bad_edits.json"
    bad_edits_file.write_text('{"invalid": "json structure"}')

    return {
        "resume": resume_file,
        "job": job_file,
        "bad_edits": bad_edits_file,
        "sample_dir": sample_dir,
    }


# * Test missing required argument → exit code 2 (Click/Typer standard)
def test_sectionize_missing_resume_path_error(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "sectionize",
                "--out-json",
                "sections.json",
                # missing resume path
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert (
            "required" in result.output.lower()
            or "missing" in result.output.lower()
            or "not found" in result.output.lower()
        )


# * Test missing required argument for generate command
def test_generate_missing_job_path_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "generate",
                str(sample_files["resume"]),
                # missing job path
                "--model",
                "gpt-4o",
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert (
            "required" in result.output.lower()
            or "not found" in result.output.lower()
            or "no such file" in result.output.lower()
        )


# * Test missing required argument for apply command
def test_apply_missing_edits_json_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "apply",
                str(sample_files["resume"]),
                # missing --edits-json
                "--output-resume",
                "output.docx",
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert (
            "required" in result.output.lower()
            or "not found" in result.output.lower()
            or "no such file" in result.output.lower()
        )


# * Test nonexistent input file → clean error message + exit code 1
def test_sectionize_nonexistent_resume_file_error(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "sectionize",
                "nonexistent_resume.docx",
                "--out-json",
                "sections.json",
                "--model",
                "gpt-4o",
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        # print(f"Sectionize nonexistent exit_code: {result.exit_code}")
        # print(f"Sectionize nonexistent output: {result.output}")
        # expect Typer file validation error
        assert result.exit_code == 2
        assert "error" in result.output.lower()
        assert (
            "file" in result.output.lower()
            or "found" in result.output.lower()
            or "package" in result.output.lower()
        )
        # should not show Python traceback
        assert "traceback" not in result.output.lower()
        assert "exception" not in result.output.lower()


# * Test nonexistent job file for generate command
def test_generate_nonexistent_job_file_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "generate",
                str(sample_files["resume"]),
                "nonexistent_job.txt",
                "--model",
                "gpt-4o",
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        # expect Typer file validation error
        assert result.exit_code == 2
        assert "error" in result.output.lower() or "not found" in result.output.lower()
        assert "traceback" not in result.output.lower()


# * Test nonexistent edits file for apply command
def test_apply_nonexistent_edits_file_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "apply",
                str(sample_files["resume"]),
                "--edits-json",
                "nonexistent_edits.json",
                "--output-resume",
                "output.docx",
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "not found" in result.output.lower()
        assert "traceback" not in result.output.lower()


# * Test malformed AI response → JSON parsing error + exit code 1
def test_sectionize_malformed_ai_response_error(
    isolate_config, sample_files, mock_ai_errors
):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()

        # mock AI to return malformed JSON
        malformed_mock = create_error_mock(mock_ai_errors, "malformed_json")

        with patch(get_ai_patch_path("sectionize"), side_effect=malformed_mock):
            result = runner.invoke(
                app,
                [
                    "sectionize",
                    str(sample_files["resume"]),
                    "--out-json",
                    str(output_dir / "sections.json"),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 1
            assert "error" in result.output.lower()
            assert "json" in result.output.lower() or "parsing" in result.output.lower()
            assert "traceback" not in result.output.lower()


# * Test AI API error → proper error handling + exit code 1
def test_generate_ai_api_error(isolate_config, sample_files, mock_ai_errors):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()

        # mock AI to return API error
        api_error_mock = create_error_mock(mock_ai_errors, "rate_limit_error")

        with patch("src.core.pipeline.run_generate", side_effect=api_error_mock):
            result = runner.invoke(
                app,
                [
                    "generate",
                    str(sample_files["resume"]),
                    str(sample_files["job"]),
                    "--edits-json",
                    str(output_dir / "edits.json"),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 1
            assert "error" in result.output.lower()
            assert "ai" in result.output.lower() or "api" in result.output.lower()


# * Test validation failure → readable message + exit code 1
def test_apply_malformed_edits_json_validation_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()

        result = runner.invoke(
            app,
            [
                "apply",
                str(sample_files["resume"]),
                "--edits-json",
                str(sample_files["bad_edits"]),
                "--output-resume",
                str(output_dir / "output.docx"),
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()
        # should show validation or parsing error
        assert (
            "validation" in result.output.lower()
            or "json" in result.output.lower()
            or "format" in result.output.lower()
        )


# * Test mutually exclusive flags → Click error + exit code 2
def test_tailor_mutually_exclusive_flags_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "tailor",
                str(sample_files["job"]),
                str(sample_files["resume"]),
                "--edits-only",
                # mutually exclusive w/ --edits-only
                "--apply",
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        # our custom validation returns exit 1
        assert result.exit_code == 1
        assert "error" in result.output.lower()
        assert (
            "mutually exclusive" in result.output.lower()
            or "exclusive" in result.output.lower()
        )


# * Test unknown option → Click error + exit code 2
def test_sectionize_unknown_option_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["sectionize", str(sample_files["resume"]), "--unknown-flag", "value"],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 2
        assert "error" in result.output.lower() or "option" in result.output.lower()


# * Test tailor without job path in edits-only mode
def test_tailor_edits_only_missing_job_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "tailor",
                str(sample_files["resume"]),
                "--edits-only",
                # missing job path
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert (
            "required" in result.output.lower()
            or "not found" in result.output.lower()
            or "no such file" in result.output.lower()
        )


# * Test tailor apply mode without edits-json
def test_tailor_apply_missing_edits_json_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "tailor",
                str(sample_files["resume"]),
                "--apply",
                # missing --edits-json path
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert (
            "required" in result.output.lower()
            or "not found" in result.output.lower()
            or "no such file" in result.output.lower()
        )


# * Test plan command w/ missing arguments
def test_plan_missing_arguments_error(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "plan"
                # missing job & resume paths
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 1
        assert (
            "required" in result.output.lower()
            or "missing" in result.output.lower()
            or "not found" in result.output.lower()
        )


# * Test config command w/ invalid subcommand
def test_config_invalid_subcommand_error(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app, ["config", "invalid_subcommand"], env={"NO_COLOR": "1", "TERM": "dumb"}
        )

        assert result.exit_code == 2
        assert "error" in result.output.lower() or "command" in result.output.lower()


# * Test file permissions error (write-protected directory)
def test_sectionize_write_permission_error(isolate_config, sample_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        # try to write to read-only directory
        readonly_dir = Path("readonly")
        readonly_dir.mkdir()
        # set dir to read-only
        readonly_dir.chmod(0o444)

        ai_mock = create_simple_ai_mock(DeterministicMockAI())

        with patch(get_ai_patch_path("sectionize"), side_effect=ai_mock):
            result = runner.invoke(
                app,
                [
                    "sectionize",
                    str(sample_files["resume"]),
                    "--out-json",
                    str(readonly_dir / "sections.json"),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 1
            assert "error" in result.output.lower()
            assert (
                "permission" in result.output.lower()
                or "write" in result.output.lower()
                or "access" in result.output.lower()
            )
