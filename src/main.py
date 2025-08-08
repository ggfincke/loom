import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from docx import Document
from openai import OpenAI

app = typer.Typer(help="Tailor resumes using the OpenAI Responses API")

# read docx file & return text content
def read_docx(path: Path) -> str:
    doc = Document(str(path))
    lines = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)

# write text to docx
def write_docx(text: str, output_path: Path) -> None:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(str(output_path))


if __name__ == "__main__":
    app()
