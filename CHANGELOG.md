# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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