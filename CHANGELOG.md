# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [1.2.0] - 2025-09-01

### Added
- **Interactive MODIFY & PROMPT operations**: Complete implementation for diff resolution workflow
- **Enhanced LaTeX support**: Improved editing guidelines and section detection
- **AI prompt security**: Anti-injection guards for user data protection
- **Comprehensive test coverage**: ~4000 lines of new tests across core modules
- **Console lifecycle management**: Better initialization and testing support

### Changed
- **Debug mode integration**: Now controlled via `dev_mode` config instead of verbose flags
- **Architecture refactoring**: Consolidated AI utilities, centralized Rich imports, reorganized theming
- **Error handling**: Standardized AI client exceptions and model detection
- **Operation workflows**: Streamlined MODIFY/PROMPT processing with better state management
- **Status indicators**: Simplified symbols for better terminal compatibility

### Removed
- **Verbose flags**: Removed `-v/--verbose` options from commands
- **Standalone modify command**: Integrated into interactive diff workflow
- **Legacy debug functions**: Replaced with unified debug system

### Fixed
- **Circular imports**: Resolved debug module dependencies
- **Interactive UI**: Improved responsiveness and loading displays
- **Test reliability**: Enhanced mocking and environment detection

---

## [1.1.7-nightly.20250901] - 2025-09-01

### Removed
- **Verbose flags**: Removed -v/--verbose options from tailor and models test commands
- **Emoji status indicators**: Replaced emoji characters with simpler text/symbol alternatives
- **Standalone debug functions**: Removed enable_debug() and disable_debug() functions

### Changed
- **Debug mode integration**: Debug mode now controlled via dev_mode config setting instead of verbose flags
- **Status indicator simplification**: Replaced ✅ with ✓, ✗ with X for better terminal compatibility
- **Unified debug output**: All debug messages now use consistent theming with debug color
- **Test coverage updates**: Removed verbose-specific test cases and simplified test logic

---

## [1.1.6-nightly.20250901] - 2025-09-01

### Added
- **Anti-injection security**: Guards in AI prompts to treat user data as data-only
- **LaTeX editing rules**: Comprehensive guidelines for special chars, lists, spacing
- **Dynamic output extensions**: Auto-match tailored resume extension to input type

### Changed
- **Modular prompt architecture**: Shared components eliminate redundancy
- **Path resolution**: Smart output extension detection and handling
- **Format preservation**: Only preserve DOCX formatting for DOCX→DOCX workflows

### Fixed
- **LaTeX output messaging**: Clear compilation guidance for .tex files
- **Test coverage**: Updated for improved path resolution logic

---

## [1.1.5-nightly.20250830] - 2025-08-30

### Added
- **Development environment improvements**: Separated development dependencies into `requirements-dev.txt` and added missing production dependencies (`anthropic`, `ollama`, `simple-term-menu`, `readchar`)
- **Console lifecycle management**: New `get_console()`, `configure_console()`, and `reset_console()` functions for better testing support and initialization control
- **Comprehensive unit test coverage**: Added ~4000 lines of tests covering AI models, CLI logic, console management, diff display, and UI components

### Changed
- **Codebase architecture refactoring**: 
  - Consolidated AI utilities into `src/ai/utils.py` module
  - Centralized Rich imports in `src/ui/core/rich_components.py`
  - Split theming into `theme_definitions.py` and `theme_engine.py` for better separation
  - Reorganized test structure to mirror source code hierarchy
- **Error handling standardization**: AI clients now consistently raise typed exceptions (`AIError`, `ConfigurationError`)
- **Model detection simplification**: Replaced individual model detection functions with unified `get_model_provider()`
- **Code quality improvements**: Added comprehensive type hints and standardized comment styles throughout codebase
- **Environment initialization**: Centralized `load_dotenv()` to application startup for single initialization

### Fixed
- **Circular import resolution**: Fixed debug module dependencies and console loading issues
- **Test reliability**: Improved console mocking and exception handling in test suites
- **Documentation accuracy**: Updated architecture docs to reflect current codebase structure

---

## [1.1.4-nightly.20250829] - 2025-08-29

### Added
- **Enhanced apply command**: Support for job description, model, and sections path in prompt operations.
- **Interactive UI improvements**: Animated spinner and better loading displays for prompt processing.

### Changed
- **Prompt operation workflow**: Immediate AI processing with enhanced error handling and timing.
- **Operation persistence**: Complete state tracking with modification flags for interactive sessions.
- **MODIFY operation simplification**: Streamlined processing by removing dual workflow handling and relying entirely on interactive UI content updates.
- **Special operations architecture**: Consolidated handling to eliminate redundant code paths and improve maintainability.

### Removed
- **`modify` CLI command**: Standalone modify command removed in favor of integrated interactive diff workflow.
- **`modified_content` field**: Removed from EditOperation dataclass to simplify the data model and reduce complexity.

### Fixed
- **Interactive UI responsiveness**: Proper loading screen refresh and timing for AI operations.
- **Special operations persistence**: All operations now correctly persist status back to edits.json.
- **Test coverage**: Updated integration and unit tests to reflect simplified operation workflows and removed deprecated test cases.

---

## [1.1.3-nightly.20250823] - 2025-08-23

### Added
- **LaTeX section detection**: Enhanced sectionizer prompt with improved LaTeX document parsing capabilities.

### Changed
- **Prompt operation processing**: Immediate AI integration with enhanced UI for prompt operations workflow.
- **Configuration path consistency**: Default sections_path moved from output_dir to data_dir for better organization.

---

## [1.1.2-nightly.20250822] - 2025-08-22

### Added
- **MODIFY & PROMPT CLI commands**: New specialized operation processing commands for enhanced user interaction.
- **Enhanced special operations persistence**: Improved data handling and state management for MODIFY/PROMPT operations.

### Changed
- **Text input display improvements**: Enhanced diff resolution UI with better text input rendering and formatting.
- **Error handling enhancements**: Improved error handling for special operations with better user feedback.

### Fixed
- **Special operations workflow**: Resolved issues with MODIFY & PROMPT operation processing and state persistence.

> Note: MODIFY & PROMPT operations are still in development and not fully functional. Significant work remains to complete the implementation.

---

## [1.1.1-nightly.20250820] - 2025-08-20

### Added
- Initial UI support for **MODIFY** operation: rich text input interface with cursor navigation and editing.
- Initial UI support for **PROMPT** operation: interactive prompt input interface for LLM instructions.
- Expanded **EditOperation** dataclass with fields for `modified_content` and `prompt_instruction`.

### Changed
- Interactive diff display updated to support text input modes and dynamic content switching.
- Keyboard navigation extended to handle editing behavior during MODIFY/PROMPT operations.
- Operation workflow updated with new state handling logic.

### Fixed
- Issues around text input state management, cursor position and buffer handling.
- Rendering/layout issues when switching between display modes.

> Note: most of this release is UI implementation work; the operations are not fully wired up and remain non-functional.

---

## [1.1.0] - 2025-08-19

### Added
- **Interactive diff framework**: Complete implementation with `--auto` flag for streamlined diff resolution workflow.
- **Diff display system**: Rich-based interface for reviewing staged, unstaged, and untracked changes with responsive layout.
- **EditOperation integration**: Seamless connection between diff workflow and structured edit operations.
- **Development mode**: Enhanced `--dev` mode and display command infrastructure for debugging interactive features.
- **Test environment detection**: Improved test isolation with automatic TTY-dependent feature detection.

### Changed
- **UI module restructuring**: Organized into structured subpackages (help/, quick/, diff/) for better maintainability and separation of concerns.
- **Display command enhancements**: Proper config context usage and improved command infrastructure.

### Fixed
- **Panel content handling**: Removed panel-specific content for cleaner exit selection interface.
- **Test case reliability**: Enhanced test environment detection and interactive mode handling for consistent test execution.

### Testing
- **Comprehensive test coverage**: Added full test suite for interactive diff workflow and related components.

---

## [1.0.1-nightly.20250819] - 2025-08-19

### Added
- **Interactive diff framework**: New `--auto` flag for streamlined diff resolution workflow.
- **Diff resolution display module**: Rich-based interface for reviewing staged, unstaged, and untracked changes.

### Changed
- **UI module restructuring**: Organized subpackages for better maintainability and separation of concerns.

---

## [1.0.0] - 2025-08-17

First stable release. Graduates the 0.x nightlies into a cohesive, production-ready CLI for AI-assisted resume tailoring with multi-provider model support, robust validation, and end-to-end workflows.

### Added
- **Core workflow**: `loom tailor`, `sectionize`, `generate`, `apply`, `models`, `config`, `help`.
- **Multi-provider AI**: OpenAI + Anthropic + local **Ollama**.
- **Formats**: DOCX (in-place & rebuild) and LaTeX via unified I/O.
- **Structured edit ops**: `replace_line`, `replace_range`, `insert_after`, `delete_range`.
- **Config**: Persistent settings at `~/.loom/config.json` with full CLI management.
- **UX**: Themed, branded help; progress bars; banner art; interactive theme selector.

### Changed
- **CLI architecture**: Consolidated commands, centralized helpers, unified error handling, consistent argument normalization.
- **Validation**: Matured strategy-based validation with clearer warnings and safer apply flow.
- **Theming**: Unified gradient/theming system with consistent terminology across commands.

### Fixed
- Robust path handling and settings resolution across commands.
- More reliable JSON/markdown parsing in AI clients; consolidated JSON error handling.
- Manual edits correctly update in-memory validation state; improved retry logic.
- Stability fixes for CLI/UI output capture and progress-safe input.

### Docs
- Updated README, license, testing guides, and architecture notes; streamlined install/usage.

### Testing
- Comprehensive test infrastructure with isolation and CI/CD.
- Unit, integration, E2E, smoke, and stress tests (including document I/O and CLI orchestration).
- Coverage gates and deterministic mocks for model/AI client behavior.

---

## [0.9.0-nightly.20250816] - 2025-08-16
### Added
- **Anthropic (Claude) support**: Full integration with Claude Sonnet/Opus 4 models.
- **Comprehensive Ollama support**: Local model integration for offline AI processing.
- **LaTeX (.tex) resume support**: Unified I/O interface supporting both DOCX and LaTeX formats.
- **Model validation system**: Consistent error handling across all AI providers.
- **CLI command consolidation**: Enhanced tailor modes with unified help system.

### Changed
- **Validation logic consolidation**: Resolved circular import dependencies and improved architecture.
- **Package configuration modernization**: Updated pyproject.toml and dependency management.

### Docs
- **Comprehensive documentation refresh**: README updates and usage guide improvements across the project.

---

## [0.8.2-nightly.20250815] - 2025-08-15
### Added
- **Dynamic theme system**: 12+ color schemes with live preview and interactive selector.
- **Branded help system**: Custom help screens with gradient styling and enhanced UX.
- **Interactive theme selector**: Simple-term-menu integration with live preview capabilities.
- **Custom help handling**: Enhanced option descriptions and improved user experience.
- **Commands table redesign**: Separate panels with prominent help notes for clarity.

### Fixed
- **Model selection mappings**: Corrected validation error handling for consistent behavior.
- **Theme setting functionality**: Resolved issues with theme persistence and application.

### Changed
- **CLI styling enhancements**: Global Typer patches with improved gradient rendering.
- **Configuration display**: Consolidated through `loom config` for better user experience.
- **Visual enhancements**: New gradient banner art and comprehensive styling system.

---

## [0.8.0-nightly.20250814] - 2025-08-14
### Added
- **UI module extraction**: Dedicated package for better separation of concerns.
- **CLI configuration management**: Persistent settings with comprehensive command suite.
- **Enhanced gradient styling**: Consistent visual theme across all CLI components.
- **Command descriptions**: Added to all CLI commands for improved usability.

### Changed
- **Complete CLI architecture consolidation**: Unified, maintainable command structure.
- **Centralized error handling**: Consistent @handle_loom_error decoration across commands.
- **JSON error handling unification**: Centralized exception system for better reliability.
- **CLI argument normalization**: Cleanup of unused options and improved consistency.
- **Validation UX improvements**: Pausable timer and consistent terminology.

### Fixed
- **Manual edit handling**: Proper in-memory validation state updates.

### Docs
- **Documentation updates**: Comprehensive refresh across the project.

---

## [0.7.0-nightly.20250813] - 2025-08-13
### Added
- **UI.input_mode() context manager**: Progress-safe input handling for better user experience.
- **Strategy pattern validation**: Robust validation framework replacing state machine approach.
- **Validation enums**: Centralized constants in new constants.py module.
- **Callback lambdas**: Enhanced argument processing in args.py.

### Fixed
- **Pipeline retry logic**: Proper handling of failed operations and re-prompting.
- **Manual edit handling**: Correct in-memory validation state updates.

### Changed
- **Command consolidation phase 2**: Shared helper functions and primitive extraction.
- **I/O coupling removal**: Core pipeline module decoupled from I/O operations.
- **Pipeline wrapper removal**: Simplified command consolidation architecture.
- **UI input coordination**: Consolidated progress creation and error handling.

### Maintenance
- **Path naming standardization**: Removed ellipsis placeholders for consistency.

---

## [0.6.0-nightly.20250812] - 2025-08-12
### Added
- **GenerateResult type**: Standardized AI client outputs for consistent behavior.
- **Structured result returns**: OpenAI client returns structured results instead of raising JSON exceptions.
- **Test prompts file**: Edge cases for validation logic testing and quality assurance.
- **Model and timestamp metadata**: Enhanced prompt tracking with creation timestamps.

### Changed
- **CLI architecture improvements**: Enhanced error handling, console management, and argument resolution.
- **Document editing enhancements**: Better validation and improved DOCX handling.
- **Prompt clarity improvements**: Crystal clear expected output specifications.

### Fixed
- **Markdown block handling**: OpenAI client strips markdown before JSON validation.
- **Path naming standardization**: Removed ellipsis placeholders for consistency.

---

## [0.5.0-nightly.20250811] - 2025-08-11
### Added
- **Major document editing enhancements**: Python-docx compatible paragraph insertion and safer apply flow.
- **ASCII art branding**: Professional CLI output with branded visual elements.
- **loom_io module**: Dedicated I/O utilities package for better organization.
- **Centralized settings management**: Improved file path handling and configuration access.
- **Module-level docstrings**: Documentation added to all Python files.

### Changed
- **Complete file structure refactoring**: Improved maintainability and organization.
- **CLI structure modernization**: Main logic moved to commands.py with updated entry points.
- **CLI argument handling**: Settings loaded once with consistent defaults application.
- **Error handling and validation**: Improved edit generation and application processes.

### Docs
- **Architecture documentation**: Detailed CLI design and data flow documentation.
- **Dedicated docs directory**: Organized documentation structure.

### Maintenance
- **PyProject.toml addition**: Fixed deprecation errors and modernized packaging.
- **GitIgnore improvements**: Better file management for data files and outputs.

---

## [0.4.0-nightly.20250810] - 2025-08-10
### Added
- **Validation warnings for edits**: Enhanced risk management and transparency in edit processes.
- **Annotated argument types**: Improved CLI clarity and usability with type hints.

### Docs
- **Architecture documentation**: Comprehensive overview of Loom CLI's internal design and data flow.

### Changed
- **CLI argument handling improvements**: Streamlined input parsing and enhanced code readability.
- **Edit validation processes**: Better risk management for safer resume modifications.

---

## [0.3.0-nightly.20250809] - 2025-08-09
### Added
- **Generate and apply commands**: Introduced `loom generate` and `loom apply` for modular resume edit workflow.
- **Document handling refactoring**: Improved edit management and processing capabilities.

### Changed
- **CLI workflow separation**: Distinct, composable commands for flexible user workflows.
- **Document processing improvements**: Enhanced resume handling and edit application.

---

## [0.2.0-nightly.20250808] - 2025-08-08
### Added
- **Progress indicators**: Visual feedback for resume processing and tailoring operations.
- **Dynamic settings integration**: File paths and OpenAI model configuration from settings.
- **Configuration management commands**: Detailed help and usage examples for user guidance.
- **Enhanced tailoring prompts**: Additional editing guidelines for better job alignment.

### Changed
- **Output path standardization**: Consistent file management across sectionize and tailor commands.
- **CLI argument defaults**: Standardized data paths for improved consistency.
- **OpenAI client improvements**: Markdown block stripping for better JSON validation.

### Fixed
- **Project initialization**: Setup and package metadata establishment.
- **GitIgnore improvements**: Better file management and dependency handling.

### Docs
- **README enhancements**: Improved installation and usage instructions.

---

## [0.1.0-nightly.20250807] - 2025-08-07
### Added
- **Typer-based CLI creation**: Foundation with main.py and basic resume processing capabilities.
- **Resume reading/writing functions**: Core document handling utilities.
- **Sectionizer and tailor prompts**: Initial LLM integration for resume processing.
- **Project setup**: Package metadata and development environment configuration.

---

## [0.0.1-nightly.20250807] - 2025-08-07
### Added
- Initial commit.