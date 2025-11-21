# src/loom_io/documents.py
# Document I/O operations for reading & writing DOCX files w/ formatting preservation, plus basic LaTeX/text support

from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.oxml import OxmlElement
from typing import Dict, Tuple, Any, List, Set
from .types import Lines
from ..core.exceptions import LaTeXError
from .generics import ensure_parent
from ..core.validation import validate_basic_latex_syntax


# * Read DOCX file & return text content w/ document object
def read_docx_with_formatting(path: Path) -> Tuple[Lines, Any, Dict[int, Paragraph]]:
    doc = Document(str(path))
    lines = {}
    paragraph_map = {}
    line_number = 1

    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            lines[line_number] = text
            paragraph_map[line_number] = p
            line_number += 1

    return lines, doc, paragraph_map


# * Read DOCX file & return text content (backward compatibility)
def read_docx(path: Path) -> Lines:
    lines, _, _ = read_docx_with_formatting(path)
    return lines


# * Read LaTeX (.tex) file as numbered lines (basic support)
def read_latex(path: Path) -> Lines:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise LaTeXError(f"Cannot decode LaTeX file {path}: {e}")
    except Exception as e:
        raise LaTeXError(f"Cannot read LaTeX file {path}: {e}")

    # validate basic LaTeX syntax
    if not validate_basic_latex_syntax(text):
        raise LaTeXError(f"Invalid LaTeX syntax detected in {path}")

    lines: Lines = {}
    line_number = 1
    for raw in text.splitlines():
        t = raw.strip()
        if t:
            lines[line_number] = t
            line_number += 1
    return lines


# * Read LaTeX (.tex) file w/ structure preservation
def read_latex_with_structure(path: Path) -> Lines:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise LaTeXError(f"Cannot decode LaTeX file {path}: {e}")
    except Exception as e:
        raise LaTeXError(f"Cannot read LaTeX file {path}: {e}")

    # validate basic LaTeX syntax
    if not validate_basic_latex_syntax(text):
        raise LaTeXError(f"Invalid LaTeX syntax detected in {path}")

    lines: Lines = {}
    line_number = 1

    for raw in text.splitlines():
        # preserve important structural elements even if "empty"
        t = raw.strip()

        # preserve important LaTeX constructs
        if (
            t.startswith("%")  # comments
            or t.startswith("\\documentclass")
            or t.startswith("\\usepackage")
            or t.startswith("\\begin{")
            or t.startswith("\\end{")
            or t.startswith("\\section")
            or t.startswith("\\subsection")
            or t.startswith("\\item")
            or (t and not t.isspace())
        ):
            lines[line_number] = t
            line_number += 1
        # preserve strategic empty lines
        elif raw == "" and line_number > 1:
            # add empty line for structural spacing
            prev_line = lines.get(line_number - 1, "")
            if (
                prev_line.startswith("\\end{")
                or prev_line.startswith("\\section")
                or prev_line.startswith("\\subsection")
            ):
                lines[line_number] = ""
                line_number += 1

    return lines


# * Read resume by file extension (.docx or .tex)
def read_resume(path: Path, preserve_structure: bool = False) -> Lines:
    suffix = path.suffix.lower()
    if suffix == ".tex":
        if preserve_structure:
            return read_latex_with_structure(path)
        return read_latex(path)
    # use DOCX handling as default
    return read_docx(path)


# * Apply edits to document w/ different preservation modes
def apply_edits_to_docx(
    original_path: Path,
    new_lines: Lines,
    output_path: Path,
    preserve_mode: str = "in_place",
) -> None:
    # preserve_mode: "in_place" (better formatting) or "rebuild" (faster)
    if preserve_mode == "in_place":
        _apply_edits_in_place(original_path, new_lines, output_path)
    else:  # use rebuild mode
        _apply_edits_rebuild(original_path, new_lines, output_path)


def _apply_edits_in_place(
    original_path: Path, new_lines: Lines, output_path: Path
) -> None:
    # edit document in-place to preserve formatting & styles

    # reuse existing reader for lines & paragraph map
    lines, doc, paragraph_map = read_docx_with_formatting(original_path)

    # compute modifications, additions, deletions
    modifications, additions, deletions = _categorize_edits(lines, new_lines)

    # apply deletions from end to start
    for line_num in sorted(deletions, reverse=True):
        if line_num in paragraph_map:
            para = paragraph_map[line_num]
            p_element = para._element
            p_element.getparent().remove(p_element)

    # apply modifications preserving run formatting
    for line_num, new_text in modifications.items():
        if line_num in paragraph_map:
            para = paragraph_map[line_num]
            _set_paragraph_text_preserving_format(para, new_text)

    # group additions by insertion position
    additions_by_position: Dict[int | None, List[Tuple[int, str]]] = {}
    for insert_after, line_num, text in additions:
        if insert_after not in additions_by_position:
            additions_by_position[insert_after] = []
        additions_by_position[insert_after].append((line_num, text))

    # sort groups by line number
    for position in additions_by_position:
        additions_by_position[position].sort(key=lambda x: x[0])

    # insert new paragraph content
    # sort numeric positions only
    numeric_positions = sorted(
        [p for p in additions_by_position.keys() if p is not None], reverse=True
    )

    # insert after paragraphs bottom-up
    for insert_after in numeric_positions:
        reference_para = paragraph_map.get(insert_after)
        if not reference_para:
            continue
        for line_num, text in reversed(additions_by_position[insert_after]):
            new_para = _insert_paragraph_after(reference_para, text)
            # copy reference paragraph style
            if reference_para.style:
                new_para.style = reference_para.style

    # insert at beginning in reverse order
    if None in additions_by_position:
        for line_num, text in reversed(additions_by_position[None]):
            new_para = doc.add_paragraph(text)
            doc.element.body.insert(0, new_para._element)

    # persist modified document
    ensure_parent(output_path)
    doc.save(str(output_path))


def _insert_paragraph_after(paragraph: Paragraph, text: str) -> Paragraph:
    # insert paragraph after given one (python-docx safe)
    new_p = OxmlElement("w:p")
    # insert after reference paragraph
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if text:
        new_para.add_run(text)
    return new_para


def _copy_run_formatting(source_run: Run, target_run: Run) -> None:
    # copy run-level formatting if available
    if not source_run:
        return
    if source_run.font:
        if source_run.font.bold is not None:
            target_run.font.bold = source_run.font.bold
        if source_run.font.italic is not None:
            target_run.font.italic = source_run.font.italic
        if source_run.font.underline is not None:
            target_run.font.underline = source_run.font.underline
        if source_run.font.strike is not None:
            target_run.font.strike = source_run.font.strike
        if source_run.font.size is not None:
            target_run.font.size = source_run.font.size
        if source_run.font.name is not None:
            target_run.font.name = source_run.font.name
        if (
            getattr(source_run.font, "color", None)
            and getattr(source_run.font.color, "rgb", None) is not None
        ):
            target_run.font.color.rgb = source_run.font.color.rgb
        if getattr(source_run.font, "highlight_color", None) is not None:
            target_run.font.highlight_color = source_run.font.highlight_color
    if hasattr(source_run, "style") and source_run.style:
        target_run.style = source_run.style


def _set_paragraph_text_preserving_format(
    target_para: Paragraph, new_text: str, template_para: Paragraph | None = None
) -> None:
    # set text preserving first-run formatting
    template = template_para if template_para is not None else target_para
    template_run = template.runs[0] if template.runs else None
    target_para.clear()
    new_run = target_para.add_run(new_text)
    if template_run:
        _copy_run_formatting(template_run, new_run)


def _categorize_edits(
    original_lines: Dict[int, str], new_lines: Lines
) -> Tuple[Dict[int, str], List[Tuple[int | None, int, str]], Set[int]]:
    # categorize edits by type
    modifications: Dict[int, str] = {}
    additions: List[Tuple[int | None, int, str]] = []
    deletions: Set[int] = set()

    original_set = set(original_lines.keys())
    new_set = set(new_lines.keys())

    # identify modified lines
    for line_num in sorted(new_set):
        if line_num in original_set and new_lines[line_num] != original_lines[line_num]:
            modifications[line_num] = new_lines[line_num]

    # identify deleted lines
    for line_num in original_set:
        if line_num not in new_set:
            deletions.add(line_num)

    # identify added lines
    for line_num in sorted(new_set):
        if line_num not in original_set:
            insert_after = None
            for existing_line in sorted(original_set):
                if existing_line < line_num:
                    insert_after = existing_line
                else:
                    break
            additions.append((insert_after, line_num, new_lines[line_num]))

    return modifications, additions, deletions


def _apply_edits_rebuild(
    original_path: Path, new_lines: Lines, output_path: Path
) -> None:
    # rebuild document from scratch (faster)
    # load original document
    lines, _, paragraph_map = read_docx_with_formatting(original_path)

    # sort line numbers for iteration
    sorted_line_nums = sorted(new_lines.keys())
    max_original_line = max(lines.keys()) if lines else 0

    # track paragraphs & their content
    paragraphs_to_process = []

    for line_num in sorted_line_nums:
        new_text = new_lines[line_num]

        if line_num <= max_original_line and line_num in paragraph_map:
            # preserve existing paragraph formatting
            para = paragraph_map[line_num]
            paragraphs_to_process.append(("modify", para, new_text))
        else:
            # create new paragraph
            paragraphs_to_process.append(("new", None, new_text))

    # create document w/ edits
    new_doc = Document()

    # note: document styles use defaults

    # process paragraphs sequentially
    for action, original_para, new_text in paragraphs_to_process:
        if action == "modify" and original_para:
            # preserve original formatting
            new_para = new_doc.add_paragraph()

            # copy paragraph formatting
            if original_para.style:
                new_para.style = original_para.style
            if original_para.paragraph_format:
                _copy_paragraph_format(
                    original_para.paragraph_format, new_para.paragraph_format
                )

            # preserve character formatting via runs
            if original_para.runs:
                _set_paragraph_text_preserving_format(
                    new_para, new_text, template_para=original_para
                )
            else:
                new_para.text = new_text
        else:
            # create paragraph w/o formatting reference
            new_doc.add_paragraph(new_text)

    # persist modified document
    ensure_parent(output_path)
    new_doc.save(str(output_path))


def _copy_paragraph_format(source_format: Any, target_format: Any) -> None:
    # copy paragraph formatting properties
    for prop in dir(source_format):
        if prop.startswith("_"):
            continue
        try:
            value = getattr(source_format, prop)
        except Exception:
            continue
        if callable(value) or value is None:
            continue
        try:
            setattr(target_format, prop, value)
        except Exception:
            # handle read-only or unsupported properties
            pass


# * Write text to DOCX file (creates plain document)
def write_docx(lines: Lines, output_path: Path) -> None:
    doc = Document()
    for line_num in sorted(lines.keys()):
        doc.add_paragraph(lines[line_num])
    ensure_parent(output_path)
    doc.save(str(output_path))


# * Write numbered lines to plain text file (.tex or .txt)
def write_text_lines(lines: Lines, output_path: Path) -> None:
    ordered = "\n".join(f"{text}" for _, text in sorted(lines.items()))
    ensure_parent(output_path)
    Path(output_path).write_text(ordered, encoding="utf-8")


# * Read text from file
def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")
