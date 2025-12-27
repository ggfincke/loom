# tests/integration/test_cli_ats.py
# Integration tests for loom ats CLI command

import pytest
from typer.testing import CliRunner
from pathlib import Path
import json
import shutil


@pytest.fixture
# Create test files for ATS command testing.
def ats_fixtures(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()

    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"

    # copy clean resume
    clean_resume = sample_dir / "clean_resume.docx"
    shutil.copy(fixtures_dir / "basic_formatted_resume.docx", clean_resume)

    # copy problem resume (with tables, headers)
    problem_resume = sample_dir / "problem_resume.docx"
    if (fixtures_dir / "ats_problem_resume.docx").exists():
        shutil.copy(fixtures_dir / "ats_problem_resume.docx", problem_resume)
    else:
        # fallback: use clean resume if fixture missing
        shutil.copy(fixtures_dir / "basic_formatted_resume.docx", problem_resume)

    return {
        "clean_resume": clean_resume,
        "problem_resume": problem_resume,
        "sample_dir": sample_dir,
    }


# * Test basic ats command (no AI)
# ATS command w/ --no-ai on clean resume should pass.
# * Verify ats command no ai clean resume
def test_ats_command_no_ai_clean_resume(isolate_config, ats_fixtures):
    from src.cli.app import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ats",
            str(ats_fixtures["clean_resume"]),
            "--no-ai",
        ],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    assert result.exit_code == 0
    assert "ATS Compatibility Report" in result.output or "Score:" in result.output


# * Test ats command w/ JSON output
# ATS command should write valid JSON report.
# * Verify ats command json output
def test_ats_command_json_output(isolate_config, ats_fixtures):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        report_path = output_dir / "ats_report.json"

        result = runner.invoke(
            app,
            [
                "ats",
                str(ats_fixtures["clean_resume"]),
                "--no-ai",
                "--out-json",
                str(report_path),
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 0
        assert report_path.exists()

        # verify JSON is valid
        with open(report_path) as f:
            data = json.load(f)

        assert "version" in data
        assert "score" in data
        assert "issues" in data
        assert "recommendations" in data
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100


# * Test ats command detects issues
# ATS command should detect tables in problem resume.
# * Verify ats command detects table issues
def test_ats_command_detects_table_issues(isolate_config, ats_fixtures):
    from src.cli.app import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ats",
            str(ats_fixtures["problem_resume"]),
            "--no-ai",
        ],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    # should complete successfully
    assert result.exit_code == 0

    # if using ats_problem_resume.docx, should detect issues
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"
    if (fixtures_dir / "ats_problem_resume.docx").exists():
        # should have detected tables or header/footer issues
        assert "table" in result.output.lower() or "header" in result.output.lower()


# * Test --fail-on critical flag
# ATS command w/ --fail-on critical should exit 2 on critical issues.
# * Verify ats command fail on critical
def test_ats_command_fail_on_critical(isolate_config, ats_fixtures):
    from src.cli.app import app

    runner = CliRunner()

    # first check if problem resume actually has critical issues
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"
    if not (fixtures_dir / "ats_problem_resume.docx").exists():
        pytest.skip("Problem resume fixture not available")

    result = runner.invoke(
        app,
        [
            "ats",
            str(ats_fixtures["problem_resume"]),
            "--no-ai",
            "--fail-on",
            "critical",
        ],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    # should exit w/ code 2 due to critical issues (tables)
    assert result.exit_code == 2


# * Test --fail-on w/ clean resume passes
# ATS command w/ --fail-on critical should pass on clean resume.
# * Verify ats command fail on passes clean
def test_ats_command_fail_on_passes_clean(isolate_config, ats_fixtures):
    from src.cli.app import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ats",
            str(ats_fixtures["clean_resume"]),
            "--no-ai",
            "--fail-on",
            "critical",
        ],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    # clean resume should pass
    assert result.exit_code == 0


# * Test invalid --fail-on value
# ATS command should reject invalid --fail-on values.
# * Verify ats command invalid fail on
def test_ats_command_invalid_fail_on(isolate_config, ats_fixtures):
    from src.cli.app import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ats",
            str(ats_fixtures["clean_resume"]),
            "--no-ai",
            "--fail-on",
            "invalid",
        ],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    # should fail w/ error
    assert result.exit_code == 1
    assert "critical" in result.output.lower() or "warning" in result.output.lower()


# * Test ats command rejects .tex files (V1)
# ATS command should reject LaTeX files (not supported in V1).
# * Verify ats command rejects tex files
def test_ats_command_rejects_tex_files(isolate_config, tmp_path):
    from src.cli.app import app

    runner = CliRunner()

    # create a dummy tex file
    tex_file = tmp_path / "resume.tex"
    tex_file.write_text(
        "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
    )

    result = runner.invoke(
        app,
        [
            "ats",
            str(tex_file),
            "--no-ai",
        ],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    # should fail w/ clear error
    assert result.exit_code == 1
    assert ".docx" in result.output.lower() or "latex" in result.output.lower()


# * Test ats command help
# ATS command --help should work.
# * Verify ats command help
def test_ats_command_help(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        ["ats", "--help"],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    # help should show description
    assert "ATS" in result.output or "ats" in result.output.lower()
    assert "--no-ai" in result.output
    assert "--fail-on" in result.output


# * Test ats appears in main help
# ATS command should appear in main help output.
# * Verify ats in main help
def test_ats_in_main_help(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--help"],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )

    assert result.exit_code == 0
    assert "ats" in result.output.lower()
