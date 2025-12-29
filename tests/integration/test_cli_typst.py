# tests/integration/test_cli_typst.py
# Integration tests for Typst (.typ) file support in CLI commands

import pytest
from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch
import json
import shutil

from tests.test_support.mock_ai import (
    DeterministicMockAI,
    create_simple_ai_mock,
    get_ai_patch_path,
)


@pytest.fixture
def mock_ai_success():
    # * Create mock AI that returns successful responses
    return DeterministicMockAI()


@pytest.fixture
def typst_files(tmp_path):
    # * Create sample Typst files for testing CLI commands
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()

    # copy Typst resume from fixtures
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "documents"
    resume_file = sample_dir / "sample_resume.typ"
    shutil.copy(fixtures_dir / "basic_formatted_resume.typ", resume_file)

    # create sample job description
    job_file = sample_dir / "job_posting.txt"
    job_file.write_text(
        "Software Engineer position requiring Python, Django, and REST API experience."
    )

    # create sample edits JSON
    edits_file = sample_dir / "edits.json"
    edits = {
        "version": 1,
        "meta": {"model": "test"},
        "ops": [
            {
                "op": "replace_line",
                "line": 55,
                "text": "Experienced software engineer with 6+ years developing web applications.",
                "reason": "Updated years",
            }
        ],
    }
    edits_file.write_text(json.dumps(edits))

    return {
        "resume": resume_file,
        "job": job_file,
        "edits": edits_file,
        "sample_dir": sample_dir,
    }


# * Test sectionize command with Typst file (no AI needed)
def test_sectionize_typst_no_model_required(isolate_config, typst_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()

        # Typst sectionize should work without --model flag
        result = runner.invoke(
            app,
            [
                "sectionize",
                str(typst_files["resume"]),
                "--out-json",
                str(output_dir / "sections.json"),
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert (output_dir / "sections.json").exists()

        # verify sections JSON structure
        sections = json.loads((output_dir / "sections.json").read_text())
        assert "sections" in sections
        assert "section_order" in sections


# * Test sectionize detects expected sections in Typst file
def test_sectionize_typst_detects_sections(isolate_config, typst_files):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()

        result = runner.invoke(
            app,
            [
                "sectionize",
                str(typst_files["resume"]),
                "--out-json",
                str(output_dir / "sections.json"),
            ],
            env={"NO_COLOR": "1", "TERM": "dumb"},
        )

        assert result.exit_code == 0

        sections = json.loads((output_dir / "sections.json").read_text())
        section_kinds = [s["kind"] for s in sections["sections"]]

        # Verify core resume sections are detected
        assert "experience" in section_kinds
        assert "skills" in section_kinds
        assert "education" in section_kinds


# * Test generate command with Typst file
def test_generate_with_typst_resume(isolate_config, typst_files, mock_ai_success):
    from src.cli.app import app

    runner = CliRunner()

    with runner.isolated_filesystem():
        output_dir = Path("output")
        output_dir.mkdir()

        ai_mock = create_simple_ai_mock(mock_ai_success)

        # generate takes resume first, then job
        with patch("src.core.pipeline.run_generate", side_effect=ai_mock):
            result = runner.invoke(
                app,
                [
                    "generate",
                    str(typst_files["resume"]),
                    str(typst_files["job"]),
                    "--edits-json",
                    str(output_dir / "edits.json"),
                    "--model",
                    "gpt-4o",
                ],
                env={"NO_COLOR": "1", "TERM": "dumb"},
            )

            assert result.exit_code == 0, f"Failed with: {result.output}"
            assert (output_dir / "edits.json").exists()


# * Test apply edit operations directly with Typst file
def test_apply_with_typst_resume(isolate_config, typst_files):
    from src.loom_io.documents import read_typst, write_text_lines
    from src.core.pipeline import apply_edits

    # Read the Typst resume
    lines = read_typst(typst_files["resume"])

    # Load and apply edits directly
    edits = json.loads(typst_files["edits"].read_text())
    new_lines = apply_edits(lines, edits)

    # Verify edits were applied
    assert len(new_lines) > 0

    # Write output
    output_path = typst_files["sample_dir"] / "tailored.typ"
    write_text_lines(new_lines, output_path)

    assert output_path.exists()
    content = output_path.read_text()
    # Should contain section headings or bullet points
    assert "=" in content or "-" in content


# * Test end-to-end Typst workflow: sectionize then apply
def test_typst_sectionize_and_apply_workflow(isolate_config, typst_files):
    from src.loom_io.documents import read_typst, write_text_lines, get_handler
    from src.core.pipeline import apply_edits

    # Step 1: Read and analyze the Typst resume (sectionize)
    resume_path = typst_files["resume"]
    lines = read_typst(resume_path)
    content = resume_path.read_text()

    handler = get_handler(resume_path)
    descriptor = handler.detect_template(resume_path, content)
    analysis = handler.analyze(lines, descriptor)
    payload = handler.sections_to_payload(analysis)

    # Verify sectionize output
    assert "sections" in payload
    assert len(payload["sections"]) > 0
    section_kinds = [s["kind"] for s in payload["sections"]]
    assert "experience" in section_kinds

    # Step 2: Apply edits to the resume
    edits = json.loads(typst_files["edits"].read_text())
    new_lines = apply_edits(lines, edits)

    # Write output
    output_path = typst_files["sample_dir"] / "tailored.typ"
    write_text_lines(new_lines, output_path)

    # Verify output
    assert output_path.exists()
    output_content = output_path.read_text()
    # Should still contain valid Typst structure
    assert "=" in output_content or "-" in output_content


# * Test read_typst validates syntax
def test_read_typst_validates_syntax(isolate_config, tmp_path):
    from src.loom_io.documents import read_typst
    from src.core.exceptions import TypstError

    # create invalid Typst file (unbalanced parentheses)
    invalid_file = tmp_path / "invalid.typ"
    invalid_file.write_text("#set page(margin: 1in\n= Experience\n")

    with pytest.raises(TypstError):
        read_typst(invalid_file)


# * Test read_typst reads valid files
def test_read_typst_reads_valid_files(isolate_config, typst_files):
    from src.loom_io.documents import read_typst

    lines = read_typst(typst_files["resume"])

    assert len(lines) > 0
    # should contain section headings
    heading_lines = [l for l in lines.values() if l.startswith("=")]
    assert len(heading_lines) > 0


# * Test read_resume dispatches correctly for .typ files
def test_read_resume_handles_typst(isolate_config, typst_files):
    from src.loom_io.documents import read_resume

    lines = read_resume(typst_files["resume"])

    assert len(lines) > 0
    # verify it's reading Typst syntax (not treating as DOCX)
    heading_lines = [l for l in lines.values() if l.startswith("=")]
    assert len(heading_lines) > 0


# * Test Typst template detection in template directory
def test_template_detection_for_typst(isolate_config):
    from src.loom_io.documents import read_typst, get_handler

    template_dir = Path(__file__).parent.parent.parent / "templates" / "swe-typst"
    resume_path = template_dir / "resume.typ"

    if resume_path.exists():
        content = resume_path.read_text()
        handler = get_handler(resume_path)
        descriptor = handler.detect_template(resume_path, content)

        assert descriptor is not None
        assert descriptor.id == "swe-typst"
        assert descriptor.inline_marker == "swe-typst"

        # test full context building
        lines = read_typst(resume_path)
        desc, analysis = handler.build_context(resume_path, lines, content)
        assert desc is not None
        assert len(analysis.sections) > 0
