# src/loom_io/template_io.py
# Shared template loading utilities for LaTeX & Typst handlers

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Pattern

from ..core.exceptions import TemplateNotFoundError, TemplateParseError

TEMPLATE_FILENAME = "loom-template.toml"


# rule defining how to detect a section in a template
@dataclass
class TemplateSectionRule:
    key: str
    pattern: str
    pattern_type: str = "literal"
    kind: str | None = None
    split_items: bool = False
    optional: bool = True


# rules specifying paths & patterns that should not be modified
@dataclass
class FrozenRules:
    paths: list[Path] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)


# complete template descriptor loaded from loom-template.toml
@dataclass
class TemplateDescriptor:
    id: str
    type: str
    name: str | None
    version: str | None
    sections: dict[str, TemplateSectionRule]
    frozen: FrozenRules
    custom: Dict[str, Any]
    source_path: Path | None = None
    inline_marker: str | None = None
    inline_only: bool = False


# * Find loom-template.toml by walking up from resume path
def find_template_descriptor_path(resume_path: Path) -> Path | None:
    current = resume_path.resolve().parent
    for parent in [current] + list(current.parents):
        candidate = parent / TEMPLATE_FILENAME
        if candidate.exists():
            return candidate
    return None


# * Load & parse template descriptor TOML file
def load_descriptor(
    descriptor_path: Path, inline_marker: str | None = None
) -> TemplateDescriptor:
    try:
        with open(descriptor_path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        raise TemplateNotFoundError(f"Template descriptor not found: {descriptor_path}")
    except tomllib.TOMLDecodeError as e:
        raise TemplateParseError(
            f"Invalid TOML in template descriptor {descriptor_path}: {e}"
        ) from e

    template_meta = raw.get("template", {})
    template_id = template_meta.get("id")
    template_type = template_meta.get("type")

    # Validate required fields
    if template_id is None or template_type is None:
        raise TemplateParseError(
            f"Template descriptor {descriptor_path} missing required template.id or template.type"
        )

    sections_raw = raw.get("sections", {})
    section_rules: dict[str, TemplateSectionRule] = {}
    for key, config in sections_raw.items():
        section_rules[key] = TemplateSectionRule(
            key=key,
            pattern=config.get("pattern", ""),
            pattern_type=config.get("pattern_type", "literal"),
            kind=config.get("kind"),
            split_items=bool(config.get("split_items", False)),
            optional=bool(config.get("optional", True)),
        )

    frozen_raw = raw.get("frozen", {})
    frozen_paths = [Path(p) for p in frozen_raw.get("paths", [])]
    frozen_patterns = frozen_raw.get("patterns", [])
    frozen_rules = FrozenRules(paths=frozen_paths, patterns=frozen_patterns or [])

    custom_meta = raw.get("custom", {})

    return TemplateDescriptor(
        id=template_id,
        type=template_type,
        name=template_meta.get("name"),
        version=template_meta.get("version"),
        sections=section_rules,
        frozen=frozen_rules,
        custom=custom_meta if isinstance(custom_meta, dict) else {},
        source_path=descriptor_path,
        inline_marker=inline_marker,
        inline_only=False,
    )


# * Detect inline template marker using format-specific pattern
def detect_inline_marker(
    content: str,
    pattern: Pattern[str],
    max_lines: int | None = None,
) -> str | None:
    if max_lines:
        content = "\n".join(content.split("\n")[:max_lines])
    match = pattern.search(content)
    if match:
        return match.group("id").strip()
    return None


__all__ = [
    "TEMPLATE_FILENAME",
    "TemplateSectionRule",
    "FrozenRules",
    "TemplateDescriptor",
    "find_template_descriptor_path",
    "load_descriptor",
    "detect_inline_marker",
]
