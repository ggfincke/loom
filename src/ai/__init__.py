# src/ai/__init__.py
# AI model clients & related functionality

from .prompts import build_sectionizer_prompt, build_generate_prompt
from .types import GenerateResult


# * Lazy proxy to avoid importing provider SDKs at package import time
# type: ignore[name-defined]
def run_generate(prompt: str, model: str) -> GenerateResult:
    from .clients.factory import run_generate as _run_generate

    return _run_generate(prompt, model)


__all__ = [
    "build_sectionizer_prompt",
    "build_generate_prompt",
    "run_generate",
    "GenerateResult",
]
