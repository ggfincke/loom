# tests/integration/test_cli_commands.py
# Integration tests for CLI command success paths & flag combinations

import pytest
from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, Mock
import json

from tests.test_support.mock_ai import DeterministicMockAI, create_ai_client_mocks, create_simple_ai_mock, get_ai_patch_path


@pytest.fixture
# * Create mock AI that returns successful responses for all scenarios
def mock_ai_success():
    return DeterministicMockAI()


@pytest.fixture
# * Create sample files for testing CLI commands
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
    job_file.write_text("Software Engineer position requiring Python, Django, and REST API experience.")
    
    return {
        "resume": resume_file,
        "job": job_file,
        "sample_dir": sample_dir
    }


# * Test sectionize command w/ basic flags
def test_sectionize_success_with_output_json(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        # setup simple mock
        ai_mock = create_simple_ai_mock(mock_ai_success)
        
        with patch(get_ai_patch_path("sectionize"), side_effect=ai_mock):
            result = runner.invoke(app, [
                "sectionize", 
                str(sample_files["resume"]),
                "--out-json", str(output_dir / "sections.json"),
                "--model", "gpt-4o"
            ], env={"NO_COLOR": "1", "TERM": "dumb"})
            
            assert result.exit_code == 0
            assert "sections" in result.output.lower()
            assert (output_dir / "sections.json").exists()


# * Test sectionize w/ model selection
def test_sectionize_success_with_model_selection(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        ai_mock = create_simple_ai_mock(mock_ai_success)
        
        with patch(get_ai_patch_path("sectionize"), side_effect=ai_mock):
            result = runner.invoke(app, [
                "sectionize",
                str(sample_files["resume"]),
                "--out-json", str(output_dir / "sections.json"),
                "--model", "gpt-4o-mini"
            ], env={"NO_COLOR": "1", "TERM": "dumb"})
            
            assert result.exit_code == 0
            assert (output_dir / "sections.json").exists()


# * Ensure LaTeX sectionize path uses handler without AI dependency
def test_sectionize_latex_uses_handler(isolate_config):
    from src.cli.app import app

    runner = CliRunner()
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"
    sample_latex = fixtures_dir / "basic_formatted_resume.tex"

    with runner.isolated_filesystem():
        resume_path = Path("resume.tex")
        resume_path.write_text(sample_latex.read_text(encoding="utf-8"), encoding="utf-8")

        result = runner.invoke(
            app,
            ["sectionize", str(resume_path), "--out-json", "sections.json"],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 0
        data = json.loads(Path("sections.json").read_text(encoding="utf-8"))
        assert data.get("handler") == "latex"
        section_names = {section["name"] for section in data.get("sections", [])}
        assert "EXPERIENCE" in section_names


# * Templates command should list bundled templates & init should copy files
def test_templates_and_init_commands(isolate_config):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        list_result = runner.invoke(
            app, ["templates"], env={"NO_COLOR": "1", "TERM": "dumb"}
        )
        assert list_result.exit_code == 0
        assert "swe-latex" in list_result.output

        target_dir = Path("my-resume")
        init_result = runner.invoke(
            app,
            ["init", "--template", "swe-latex", "--output", str(target_dir)],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert init_result.exit_code == 0
        assert (target_dir / "resume.tex").exists()
        assert (target_dir / "loom-template.toml").exists()


# * Test generate command w/ basic parameters
def test_generate_success_basic(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        ai_mock = create_simple_ai_mock(mock_ai_success)
        
        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            result = runner.invoke(app, [
                "generate",
                str(sample_files["resume"]),
                str(sample_files["job"]),
                "--edits-json", str(output_dir / "edits.json"),
                "--model", "gpt-4o"
            ], env={"NO_COLOR": "1", "TERM": "dumb"})
            
            assert result.exit_code == 0
            assert "edits" in result.output.lower()
            assert (output_dir / "edits.json").exists()


# * Test apply command w/ edits file
def test_apply_success_basic(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        # create sample edits file
        edits_file = output_dir / "sample_edits.json"
        edits_file.write_text('{"version": 1, "meta": {"strategy": "rule", "model": "gpt-4o", "created_at": "2024-01-15T10:30:00Z"}, "ops": [{"op": "replace_line", "line": 5, "text": "Updated summary line", "current_snippet": "Original text", "why": "Enhanced for job requirements"}]}')
        
        result = runner.invoke(app, [
            "apply",
            str(sample_files["resume"]),
            "--edits-json", str(edits_file),
            "--output-resume", str(output_dir / "tailored_resume.docx")
        ], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        assert "apply" in result.output.lower() or "tailored" in result.output.lower()
        assert (output_dir / "tailored_resume.docx").exists()


# * Test tailor command w/ edits-only flag
def test_tailor_edits_only_success(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        ai_mock = create_simple_ai_mock(mock_ai_success)
        
        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            result = runner.invoke(app, [
                "tailor",
                str(sample_files["job"]),
                str(sample_files["resume"]),
                "--edits-only",
                "--edits-json", str(output_dir / "edits.json"),
                "--model", "gpt-4o"
            ], env={"NO_COLOR": "1", "TERM": "dumb"})
            
            assert result.exit_code == 0
            assert "edits" in result.output.lower()
            assert (output_dir / "edits.json").exists()
            # should not create output resume in edits-only mode
            assert not (output_dir / "tailored_resume.docx").exists()


# * Test tailor command w/ apply flag
def test_tailor_apply_success(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        # create sample edits file
        edits_file = output_dir / "existing_edits.json"
        edits_file.write_text('{"version": 1, "meta": {"strategy": "rule", "model": "gpt-4o", "created_at": "2024-01-15T10:30:00Z"}, "ops": [{"op": "replace_line", "line": 5, "text": "Updated summary line", "current_snippet": "Original text", "why": "Enhanced for job requirements"}]}')
        
        # set config to point to our sample resume
        from src.config.settings import settings_manager
        settings_manager.set("resume_filename", str(sample_files["resume"]))
        
        result = runner.invoke(app, [
            "tailor",
            "--apply",
            "--edits-json", str(edits_file),
            "--output-resume", str(output_dir / "applied_resume.docx")
        ], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        assert "wrote" in result.output.lower() or "tailored" in result.output.lower()
        assert (output_dir / "applied_resume.docx").exists()


# * Test tailor command full end-to-end
def test_tailor_full_end_to_end_success(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        ai_mock = create_simple_ai_mock(mock_ai_success)
        
        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            result = runner.invoke(app, [
                "tailor",
                str(sample_files["job"]),
                str(sample_files["resume"]),
                "--output-resume", str(output_dir / "full_tailored.docx"),
                "--edits-json", str(output_dir / "full_edits.json"),
                "--model", "gpt-4o"
            ], env={"NO_COLOR": "1", "TERM": "dumb"})
            
            assert result.exit_code == 0
            assert "tailor" in result.output.lower()
            # both edits & output resume should be created
            assert (output_dir / "full_edits.json").exists()
            assert (output_dir / "full_tailored.docx").exists()


# * Test plan command basic functionality
def test_plan_success_basic(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    ai_mock = create_simple_ai_mock(mock_ai_success)
    
    with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
        result = runner.invoke(app, [
            "plan",
            str(sample_files["resume"]),
            str(sample_files["job"]),
            "--model", "gpt-4o"
        ], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        # print(f"Plan command exit_code: {result.exit_code}")
        # print(f"Plan command output: {result.output}")
        assert result.exit_code == 0
        assert "plan" in result.output.lower() or "strategy" in result.output.lower()


# * Test apply w/ preserve formatting flags
def test_apply_with_preserve_formatting_flags(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        # create sample edits file
        edits_file = output_dir / "preserve_edits.json"
        edits_file.write_text('{"version": 1, "meta": {"strategy": "rule", "model": "gpt-4o", "created_at": "2024-01-15T10:30:00Z"}, "ops": [{"op": "replace_line", "line": 5, "text": "Updated summary line", "current_snippet": "Original text", "why": "Enhanced for job requirements"}]}')
        
        result = runner.invoke(app, [
            "apply",
            str(sample_files["resume"]),
            "--edits-json", str(edits_file),
            "--output-resume", str(output_dir / "formatted_resume.docx"),
            "--preserve-formatting",
            "--preserve-mode", "strict"
        ], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        assert (output_dir / "formatted_resume.docx").exists()


# * Test generate w/ sections path & risk settings
def test_generate_with_sections_and_risk_settings(isolate_config, sample_files, mock_ai_success):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()
        
        # create sample sections file
        sections_file = output_dir / "sample_sections.json"
        sections_file.write_text('{"sections": [{"name": "SUMMARY", "start_line": 5, "end_line": 6}]}')
        
        ai_mock = create_simple_ai_mock(mock_ai_success)
        
        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            result = runner.invoke(app, [
                "generate",
                str(sample_files["resume"]),
                str(sample_files["job"]),
                "--sections-path", str(sections_file),
                "--edits-json", str(output_dir / "risk_edits.json"),
                "--model", "gpt-4o"
            ], env={"NO_COLOR": "1", "TERM": "dumb"})
            
            # print(f"Generate sections exit_code: {result.exit_code}")
            # print(f"Generate sections output: {result.output}")
            assert result.exit_code == 0
            assert (output_dir / "risk_edits.json").exists()




# * Test config command basic functionality
def test_config_list_success(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, [
            "config", "list"
        ], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        assert "config" in result.output.lower() or "settings" in result.output.lower()


# * Test models command functionality
def test_models_command_success(isolate_config):
    from src.cli.app import app
    
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, [
            "models"
        ], env={"NO_COLOR": "1", "TERM": "dumb"})
        
        assert result.exit_code == 0
        assert "model" in result.output.lower() or "provider" in result.output.lower()
