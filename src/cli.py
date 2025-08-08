from pathlib import Path
from typing import Optional
import typer
import json

from .document import read_docx, number_lines, read_text
from .prompts import build_sectionizer_prompt, build_tailor_prompt
from .openai_client import openai_json

app = typer.Typer(help="Tailor resumes using the OpenAI Responses API")

# CLI commands
@app.command()
def sectionize(
    resume_path: Path = typer.Argument(Path("data/resume.docx"), help="Path to source resume .docx"),
    out_json: Path = typer.Option(Path("data/sections.json"), help="Where to write the sections JSON"),
    model: str = typer.Option("gpt-4o-mini", help="OpenAI model name"),
):
    '''
    Parse a resume (.docx) into sections using OpenAI's Response API
    '''
    lines = read_docx(resume_path)
    numbered = number_lines(lines)
    prompt = build_sectionizer_prompt(numbered)
    data = openai_json(prompt, model=model)
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    typer.echo(f"Wrote {out_json}")

@app.command()
def tailer(
    job_info: Path = typer.Argument(Path("data/job.txt"), help="Job description text to tailor resume for"),
    resume_path: Path = typer.Argument(Path("data/resume.docx"), help="Path to source resume .docx"),
    sections_path: Optional[Path] = typer.Option(Path("data/sections.json"), help="Optional sections.json from the 'sections' command"),
    out_json: Path = typer.Option(Path("data/edits.json"), help="Where to write the edits JSON"),
    model: str = typer.Option("gpt-4o-mini", help="OpenAI model name"),
):
    '''
    Tailor a resume (.docx) to a job description using OpenAI's Response API
    Generates a JSON object with edits by line number
    '''
    job_text = read_text(job_info)
    lines = read_docx(resume_path)
    numbered = number_lines(lines)
    sections_json_str = None
    if sections_path and sections_path.exists():
        sections_json_str = sections_path.read_text(encoding="utf-8")

    prompt = build_tailor_prompt(job_text, numbered, sections_json_str)
    data = openai_json(prompt, model=model)
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    typer.echo(f"Wrote {out_json}")