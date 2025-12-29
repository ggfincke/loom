# tests/unit/loom_io/test_latex_handler.py
# Unit tests for LaTeX handler using new OO API

from pathlib import Path
import json

from src.loom_io.documents import get_handler, read_latex


# * Verify generic LaTeX analysis detects expected sections
def test_analyze_latex_detects_core_sections():
    root = Path(__file__).resolve().parents[3]
    fixtures_dir = root / "tests" / "fixtures" / "documents"
    sample_path = fixtures_dir / "basic_formatted_resume.tex"
    lines = read_latex(sample_path)

    handler = get_handler(sample_path)
    analysis = handler.analyze(lines)
    section_keys = {section.key for section in analysis.sections}

    assert "experience" in section_keys
    assert "skills" in section_keys
    assert "education" in section_keys


# * Ensure LaTeX edit filter drops structural changes & preserves commands
def test_filter_latex_edits_enforces_command_preservation():
    resume_lines = {
        1: "\\documentclass{article}",
        2: "\\begin{document}",
        3: "\\section{Experience}",
        4: "\\item Old bullet",
        5: "Plain content line",
        6: "\\end{document}",
    }
    edits = {
        "version": 1,
        "meta": {},
        "ops": [
            {"op": "replace_line", "line": 1, "text": "\\documentclass{report}"},
            {"op": "replace_line", "line": 4, "text": "New bullet text"},
            {"op": "replace_line", "line": 5, "text": "Updated content"},
        ],
    }

    # Use handler via get_handler w/ a dummy .tex path
    from src.loom_io.latex_handler import LatexHandler

    handler = LatexHandler()
    filtered, notes = handler.filter_edits(edits, resume_lines, descriptor=None)

    assert any("structural" in note for note in notes)
    assert any("Dropped edit removing \\item" in note for note in notes)
    assert len(filtered["ops"]) == 1
    assert filtered["ops"][0]["line"] == 5


# * Detect template descriptor & inline marker from bundled template
def test_detect_template_uses_descriptor_and_inline_marker():
    root = Path(__file__).resolve().parents[3]
    template_resume = (root / "templates" / "swe-latex" / "resume.tex").resolve()
    content = template_resume.read_text(encoding="utf-8")

    handler = get_handler(template_resume)
    descriptor = handler.detect_template(template_resume, content)
    assert descriptor is not None
    assert descriptor.id == "swe-latex"
    assert descriptor.inline_marker == "swe-latex"

    lines = read_latex(template_resume)
    analysis = handler.analyze(lines, descriptor)
    payload = handler.sections_to_payload(analysis)

    assert payload["meta"]["template_id"] == "swe-latex"
    # version/handler fields removed for token efficiency
    assert "sections" in payload
    json.dumps(payload)  # validate JSON serializable
