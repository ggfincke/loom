# src/loom_io/documents.py
# Document I/O operations for reading and writing DOCX files with formatting preservation

from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from typing import Dict, Tuple, Any, List, Set
from .types import Lines

# read docx file & return both text content & document object
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

# read docx file & return text content (backward compatibility)
def read_docx(path: Path) -> Lines:
    lines, _, _ = read_docx_with_formatting(path)
    return lines

# apply edits to document with different preservation modes
def apply_edits_to_docx(original_path: Path, new_lines: Lines, output_path: Path, 
                        preserve_mode: str = "in_place") -> None:
    # preserve_mode: "in_place" (better formatting preservation) or "rebuild" (faster)
    if preserve_mode == "in_place":
        _apply_edits_in_place(original_path, new_lines, output_path)
    else:  # rebuild mode
        _apply_edits_rebuild(original_path, new_lines, output_path)

def _apply_edits_in_place(original_path: Path, new_lines: Lines, output_path: Path) -> None:
    # edit document in-place to preserve all formatting, styles, headers, footers
    
    # reuse existing reader to build lines and paragraph map
    lines, doc, paragraph_map = read_docx_with_formatting(original_path)
    
    # compute modifications / additions / deletions once
    modifications, additions, deletions = _categorize_edits(lines, new_lines)
    
    # apply deletions from end to beginning
    for line_num in sorted(deletions, reverse=True):
        if line_num in paragraph_map:
            para = paragraph_map[line_num]
            p_element = para._element
            p_element.getparent().remove(p_element)
    
    # apply modifications while preserving run-level formatting
    for line_num, new_text in modifications.items():
        if line_num in paragraph_map:
            para = paragraph_map[line_num]
            _set_paragraph_text_preserving_format(para, new_text)
    
    # group additions by insert position
    additions_by_position: Dict[int | None, List[Tuple[int, str]]] = {}
    for insert_after, line_num, text in additions:
        if insert_after not in additions_by_position:
            additions_by_position[insert_after] = []
        additions_by_position[insert_after].append((line_num, text))
    
    # sort each group by line number
    for position in additions_by_position:
        additions_by_position[position].sort(key=lambda x: x[0])
    
    # insert new paragraphs
    # sort only numeric positions (None is handled separately)
    numeric_positions = sorted([p for p in additions_by_position.keys() if p is not None], reverse=True)
    
    # insert after specified paragraphs (from bottom up so indices remain valid)
    for insert_after in numeric_positions:
        reference_para = paragraph_map.get(insert_after)
        if not reference_para:
            continue
        for line_num, text in reversed(additions_by_position[insert_after]):
            new_para = _insert_paragraph_after(reference_para, text)
            # copy style from reference paragraph
            if reference_para.style:
                new_para.style = reference_para.style
    
    # insert at beginning (reverse so final order is ascending)
    if None in additions_by_position:
        for line_num, text in reversed(additions_by_position[None]):
            new_para = doc.add_paragraph(text)
            doc.element.body.insert(0, new_para._element)
    
    # save modified document
    doc.save(str(output_path))

def _insert_paragraph_after(paragraph: Paragraph, text: str) -> Paragraph:
    # insert new paragraph after given paragraph
    new_p = paragraph._element.addnext(paragraph._element._new())
    new_para = Paragraph(new_p, paragraph._parent)
    new_para.text = text
    return new_para

def _copy_run_formatting(source_run, target_run) -> None:
    # copy common run-level formatting if present
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
        if getattr(source_run.font, "color", None) and getattr(source_run.font.color, "rgb", None) is not None:
            target_run.font.color.rgb = source_run.font.color.rgb
        if getattr(source_run.font, "highlight_color", None) is not None:
            target_run.font.highlight_color = source_run.font.highlight_color
    if hasattr(source_run, "style") and source_run.style:
        target_run.style = source_run.style

def _set_paragraph_text_preserving_format(target_para: Paragraph, new_text: str, template_para: Paragraph | None = None) -> None:
    # set new text while preserving first-run formatting from template
    template = template_para if template_para is not None else target_para
    template_run = template.runs[0] if template.runs else None
    target_para.clear()
    new_run = target_para.add_run(new_text)
    if template_run:
        _copy_run_formatting(template_run, new_run)

def _categorize_edits(original_lines: Dict[int, str], new_lines: Lines):
    # categorize edits into modifications, additions, deletions
    modifications: Dict[int, str] = {}
    additions: List[Tuple[int | None, int, str]] = []
    deletions: Set[int] = set()
    
    original_set = set(original_lines.keys())
    new_set = set(new_lines.keys())
    
    # lines to modify (exist in both but changed)
    for line_num in sorted(new_set):
        if line_num in original_set and new_lines[line_num] != original_lines[line_num]:
            modifications[line_num] = new_lines[line_num]
    
    # lines to delete (exist in original but not in new)
    for line_num in original_set:
        if line_num not in new_set:
            deletions.add(line_num)
    
    # lines to add (exist in new but not in original)
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

def _apply_edits_rebuild(original_path: Path, new_lines: Lines, output_path: Path) -> None:
    # rebuild document from scratch (faster but may lose some formatting)
    # read original document
    lines, _, paragraph_map = read_docx_with_formatting(original_path)
    
    # sort line numbers for processing
    sorted_line_nums = sorted(new_lines.keys())
    max_original_line = max(lines.keys()) if lines else 0
    
    # track paragraphs to keep and their new content
    paragraphs_to_process = []
    
    for line_num in sorted_line_nums:
        new_text = new_lines[line_num]
        
        if line_num <= max_original_line and line_num in paragraph_map:
            # existing paragraph, preserve formatting
            para = paragraph_map[line_num]
            paragraphs_to_process.append(('modify', para, new_text))
        else:
            # new paragraph not in original
            paragraphs_to_process.append(('new', None, new_text))
    
    # create new document with edits
    new_doc = Document()
    
    # note: document styles cannot be copied, will use defaults
    
    # process paragraphs in order
    for action, original_para, new_text in paragraphs_to_process:
        if action == 'modify' and original_para:
            # preserve formatting from original
            new_para = new_doc.add_paragraph()
            
            # copy paragraph-level formatting
            if original_para.style:
                new_para.style = original_para.style
            if original_para.paragraph_format:
                _copy_paragraph_format(original_para.paragraph_format, new_para.paragraph_format)
            
            # preserve character-level formatting via runs
            if original_para.runs:
                _set_paragraph_text_preserving_format(new_para, new_text, template_para=original_para)
            else:
                new_para.text = new_text
        else:
            # new paragraph without formatting reference
            new_doc.add_paragraph(new_text)
    
    # save modified document
    new_doc.save(str(output_path))

def _copy_paragraph_format(source_format, target_format):
    # best-effort copy of paragraph formatting properties
    for prop in dir(source_format):
        if prop.startswith('_'):
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
            # some properties might be read-only or unsupported
            pass

# write text to docx file (creates plain document)
def write_docx(lines: Lines, output_path: Path) -> None:
    doc = Document()
    for line_num in sorted(lines.keys()):
        doc.add_paragraph(lines[line_num])
    doc.save(str(output_path))

# number lines in a resume
def number_lines(resume: Lines) -> str:
    return "\n".join(f"{i:>4} {text}" for i, text in sorted(resume.items()))

# read text from file
def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")