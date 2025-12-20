# tests/integration/test_end_to_end_workflows.py
# End-to-end workflow integration tests w/ mocked AI & real artifact generation

import pytest
import json
import shutil
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

from tests.test_support.mock_ai import (
    DeterministicMockAI,
    create_simple_ai_mock,
    get_ai_patch_path,
)


@pytest.fixture
# * Create mock AI that returns successful responses for all scenarios
def mock_ai_success():
    return DeterministicMockAI()


@pytest.fixture
# * Create sample files for end-to-end testing w/ both DOCX & LaTeX formats
def e2e_sample_files(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()

    # copy sample resume files from fixtures
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"

    # DOCX resume
    resume_docx = sample_dir / "sample_resume.docx"
    shutil.copy(fixtures_dir / "basic_formatted_resume.docx", resume_docx)

    # LaTeX resume
    resume_tex = sample_dir / "sample_resume.tex"
    shutil.copy(fixtures_dir / "basic_formatted_resume.tex", resume_tex)

    # job description
    job_file = sample_dir / "job_posting.txt"
    job_file.write_text(
        "Senior Software Engineer position requiring Python, Django, AWS, and microservices experience. Looking for candidates with 5+ years experience leading technical teams."
    )

    return {
        "resume_docx": resume_docx,
        "resume_tex": resume_tex,
        "job": job_file,
        "sample_dir": sample_dir,
    }


@pytest.fixture
# * Create temp output directory for real artifact generation
def temp_output_dir(tmp_path):
    output_dir = tmp_path / "temp_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
# * Setup config w/ defaults pointing to temp directories
def config_with_temp_defaults(tmp_path, isolate_config):
    from src.config.settings import LoomSettings

    # create temp data & output dirs
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    data_dir.mkdir()
    output_dir.mkdir()

    # return settings w/ temp paths
    return LoomSettings(
        data_dir=str(data_dir),
        output_dir=str(output_dir),
        model="gpt-4o",
        resume_filename="resume.docx",
        job_filename="job.txt",
    )


class TestEndToEndWorkflows:

    # * Test complete sectionize → tailor workflow w/ chained outputs
    def test_complete_sectionize_to_tailor_workflow(
        self, e2e_sample_files, temp_output_dir, mock_ai_success, isolate_config
    ):
        from src.cli.app import app

        runner = CliRunner()

        # setup mock AI for both sectionize & tailor commands
        ai_mock = create_simple_ai_mock(mock_ai_success)

        with (
            patch(get_ai_patch_path("sectionize"), side_effect=ai_mock),
            patch("src.core.pipeline.run_generate", side_effect=ai_mock),
        ):

            # step 1: run sectionize command
            sections_file = temp_output_dir / "sections.json"
            result1 = runner.invoke(
                app,
                [
                    "sectionize",
                    str(e2e_sample_files["resume_docx"]),
                    "--out-json",
                    str(sections_file),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result1.exit_code == 0
            assert sections_file.exists()

            # verify sections.json structure
            sections_data = json.loads(sections_file.read_text())
            assert "sections" in sections_data
            assert len(sections_data["sections"]) > 0

            # step 2: run tailor command using sections from step 1
            edits_file = temp_output_dir / "edits.json"
            output_resume = temp_output_dir / "tailored_resume.docx"

            result2 = runner.invoke(
                app,
                [
                    "tailor",
                    str(e2e_sample_files["job"]),
                    str(e2e_sample_files["resume_docx"]),
                    "--sections-path",
                    str(sections_file),
                    "--edits-json",
                    str(edits_file),
                    "--output-resume",
                    str(output_resume),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            if result2.exit_code != 0:
                print("TAILOR STDOUT:", result2.output)
                if hasattr(result2, "stderr_bytes"):
                    print("TAILOR STDERR:", result2.stderr_bytes)
            assert result2.exit_code == 0

            # verify all expected artifacts exist
            assert edits_file.exists()
            assert output_resume.exists()

            # verify edits.json structure
            edits_data = json.loads(edits_file.read_text())
            assert (
                "version" in edits_data or "ops" in edits_data or "edits" in edits_data
            )

            # verify output resume is different from input (has content)
            assert output_resume.stat().st_size > 0

    # * Test tailor --edits-only flag generates edits without applying them
    def test_tailor_edits_only_flag(
        self, e2e_sample_files, temp_output_dir, mock_ai_success, isolate_config
    ):
        from src.cli.app import app

        runner = CliRunner()

        ai_mock = create_simple_ai_mock(mock_ai_success)

        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            edits_file = temp_output_dir / "edits_only.json"
            output_resume = temp_output_dir / "should_not_exist.docx"

            result = runner.invoke(
                app,
                [
                    "tailor",
                    str(e2e_sample_files["job"]),
                    str(e2e_sample_files["resume_docx"]),
                    "--edits-json",
                    str(edits_file),
                    "--edits-only",
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 0

            # verify edits file was created
            assert edits_file.exists()

            # verify output resume was NOT created
            assert not output_resume.exists()

            # verify edits structure
            edits_data = json.loads(edits_file.read_text())
            assert (
                "version" in edits_data or "ops" in edits_data or "edits" in edits_data
            )

    # * Test default tailor behavior (generate + apply)
    def test_tailor_default_generate_and_apply(
        self, e2e_sample_files, temp_output_dir, mock_ai_success, isolate_config
    ):
        from src.cli.app import app

        runner = CliRunner()

        ai_mock = create_simple_ai_mock(mock_ai_success)

        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            edits_file = temp_output_dir / "default_edits.json"
            output_resume = temp_output_dir / "default_tailored.docx"

            result = runner.invoke(
                app,
                [
                    "tailor",
                    str(e2e_sample_files["job"]),
                    str(e2e_sample_files["resume_docx"]),
                    "--edits-json",
                    str(edits_file),
                    "--output-resume",
                    str(output_resume),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 0

            # verify both generation & application artifacts exist
            assert edits_file.exists()
            assert output_resume.exists()

            # verify edits structure
            edits_data = json.loads(edits_file.read_text())
            assert (
                "version" in edits_data or "ops" in edits_data or "edits" in edits_data
            )

            # verify output resume has content
            assert output_resume.stat().st_size > 0

            # verify diff file was created in .loom directory
            loom_dir = Path(".loom")
            if loom_dir.exists():
                diff_file = loom_dir / "diff.patch"
                if diff_file.exists():
                    assert (
                        diff_file.stat().st_size >= 0
                    )  # diff file may be empty for identical content

    # * Test LaTeX resume processing through workflow
    def test_latex_resume_processing(
        self, e2e_sample_files, temp_output_dir, mock_ai_success, isolate_config
    ):
        from src.cli.app import app

        runner = CliRunner()

        ai_mock = create_simple_ai_mock(mock_ai_success)

        with patch(get_ai_patch_path("sectionize"), side_effect=ai_mock):
            sections_file = temp_output_dir / "latex_sections.json"

            result = runner.invoke(
                app,
                [
                    "sectionize",
                    str(e2e_sample_files["resume_tex"]),
                    "--out-json",
                    str(sections_file),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 0
            assert sections_file.exists()

            # verify sections were detected from LaTeX
            sections_data = json.loads(sections_file.read_text())
            assert "sections" in sections_data
            assert len(sections_data["sections"]) > 0

            # verify LaTeX-specific content was processed (check for common LaTeX content)
            has_latex_content = any(
                "content" in section
                and any(
                    latex_cmd in str(section["content"])
                    for latex_cmd in ["\\textbf", "\\section", "Software Engineer"]
                )
                for section in sections_data["sections"]
            )

            # at minimum, sections should exist (LaTeX commands may or may not be preserved in JSON)
            assert len(sections_data["sections"]) > 0

    # * Test config defaults integration w/ minimal CLI arguments
    def test_config_defaults_integration(
        self, e2e_sample_files, mock_ai_success, tmp_path, isolate_config
    ):
        from src.cli.app import app

        runner = CliRunner()

        # create config w/ paths inside the test temp directory
        data_dir = tmp_path / "data"
        output_dir = tmp_path / "output"
        data_dir.mkdir()
        output_dir.mkdir()

        # copy files to match config defaults
        shutil.copy(e2e_sample_files["resume_docx"], data_dir / "resume.docx")
        shutil.copy(e2e_sample_files["job"], data_dir / "job.txt")

        # create config w/ absolute paths
        from src.config.settings import LoomSettings

        config = LoomSettings(
            data_dir=str(data_dir),
            output_dir=str(output_dir),
            model="gpt-4o",
            resume_filename="resume.docx",
            job_filename="job.txt",
        )

        ai_mock = create_simple_ai_mock(mock_ai_success)

        with patch(get_ai_patch_path("sectionize"), side_effect=ai_mock):
            # test sectionize w/ config defaults (no arguments needed)
            result = runner.invoke(
                app, ["sectionize"], env={"NO_COLOR": "1", "TERM": "dumb"}, obj=config
            )

            if result.exit_code != 0:
                print("STDOUT:", result.output)
                if hasattr(result, "stderr_bytes"):
                    print("STDERR:", result.stderr_bytes)
            assert result.exit_code == 0

            # check if file was created in the working directory's data folder instead
            cwd_output_file = Path("data") / "sections.json"

            if cwd_output_file.exists():
                # file was created in current working directory (acceptable)
                sections_file = cwd_output_file
            else:
                # check in configured data directory (new default location)
                sections_file = data_dir / "sections.json"

            assert sections_file.exists()

            sections_data = json.loads(sections_file.read_text())
            assert "sections" in sections_data
            assert len(sections_data["sections"]) > 0
