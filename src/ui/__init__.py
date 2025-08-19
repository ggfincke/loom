# src/ui/__init__.py
# Main UI package - imports and re-exports from subpackages

# Core UI components
from .core import (
    UI,
    PausableElapsedColumn,
    setup_ui_with_progress,
    load_resume_and_job,
    load_sections,
    load_edits_json,
    PausableTimer,
)

# Theming system
from .theming import (
    THEMES,
    get_active_theme,
    update_gradient_colors,
    LoomColors,
    natural_gradient,
    gradient_text,
    success_gradient,
    accent_gradient,
    get_loom_theme,
    styled_checkmark,
    styled_arrow,
    styled_bullet,
    initialize_theme,
    refresh_theme,
    auto_initialize_theme,
    interactive_theme_selector,
)

# Display utilities
from .display import (
    show_loom_art,
    persist_edits_json,
    report_result,
    write_output_with_diff,
)

# Help system
from .help import (
    CommandHelp,
    OptionHelp,
    command_help,
    get_command_metadata,
    get_all_command_metadata,
    extract_help_from_function,
    get_command_help,
    get_option_help,
    get_workflow_help,
    HelpRenderer,
)

# Quick usage utilities
from .quick import show_quick_usage

__all__ = [
    # Core
    "UI",
    "PausableElapsedColumn",
    "setup_ui_with_progress",
    "load_resume_and_job",
    "load_sections",
    "load_edits_json",
    "PausableTimer",
    
    # Theming
    "THEMES",
    "get_active_theme",
    "update_gradient_colors",
    "LoomColors",
    "natural_gradient",
    "gradient_text",
    "success_gradient",
    "accent_gradient",
    "get_loom_theme",
    "styled_checkmark",
    "styled_arrow",
    "styled_bullet",
    "initialize_theme",
    "refresh_theme",
    "auto_initialize_theme",
    "interactive_theme_selector",
    
    # Display
    "show_loom_art",
    "persist_edits_json",
    "report_result",
    "write_output_with_diff",
    
    # Help
    "CommandHelp",
    "OptionHelp",
    "command_help",
    "get_command_metadata",
    "get_all_command_metadata",
    "extract_help_from_function",
    "get_command_help",
    "get_option_help",
    "get_workflow_help",
    "HelpRenderer",
    
    # Quick
    "show_quick_usage",
]