# src/ui/diff_resolution/__init__.py
# Interactive diff resolution components for edit review UI

from .diff_display import InteractiveDiffResolver, main_display_loop
from .diff_renderer import DiffRenderer, create_renderer_from_console
from .diff_state import (
    DiffState,
    DiffStateManager,
    DiffReviewMode,
    AIContext,
    DiffAIProcessor,
    PromptCallback,
    get_default_prompt_callback,
    OPTIONS,
)
from .diff_input import DiffInputHandler

__all__ = [
    "InteractiveDiffResolver",
    "main_display_loop",
    "DiffRenderer",
    "create_renderer_from_console",
    "DiffState",
    "DiffStateManager",
    "DiffReviewMode",
    "AIContext",
    "DiffAIProcessor",
    "PromptCallback",
    "get_default_prompt_callback",
    "DiffInputHandler",
    "OPTIONS",
]
