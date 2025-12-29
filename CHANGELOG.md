# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.8-nightly.20251229] - 2025-12-29

### Added
- **Unified handler architecture**: BaseDocumentHandler abstract class w/ registry pattern for format-agnostic processing
- **Shared utilities**: Template loading, semantic matchers & document types (`template_io`, `shared_patterns`, `types`)
- **CLI helpers**: Model validation module & `HelpOpt()` param factory for standardized help flags
- **ValidationResult type**: Pure data class for validation outcomes & settings cache invalidation

### Changed
- **Handler refactor**: LaTeX/Typst handlers migrated to OO API w/ `get_handler()` registry & backward-compatible legacy API
- **Layer purity**: Move I/O operations from ai/ to CLI layer (`ensure_valid_model` → `model_helpers`)
- **Code formatting**: Apply black formatting across codebase
- **Documentation**: Enhanced layer purity rules & command authoring patterns

---

## [1.3.7-nightly.20251228] - 2025-12-28

### Changed
- **Core types module**: Move `Lines` type & `number_lines` to `core/types.py` for architectural purity
- **Output system**: Add unified output management w/ registry pattern separating core from CLI
- **CLI decorators**: Extract `handle_loom_error`, `require_dev_mode`, `run_with_watch` to `cli/decorators.py`
- **Validation handlers**: Move validation strategies from core to CLI layer
- **Exception hierarchy**: Expand exception classes w/ richer context fields
- **AI cache**: Consolidate `response_cache.py` into `cache.py`
- **Settings access**: Standardize via `get_settings(ctx)` helper w/ context chain search

### Added
- **Command authoring docs**: Add patterns section to `docs/contributing.md`

---

## [1.3.6-nightly.20251227] - 2025-12-27

### Added
- **Section mapping**: Edit analysis w/ sections.json integration
- **Cache LRU eviction**: Max entries & size limits w/ thread-local disable
- **Typst validation**: Compiler availability checks & inline-only descriptor fallback

---

## [1.3.5-nightly.20251227] - 2025-12-27

### Added
- **Bulk processing system**: Multi-job processing w/ parallel execution, retry logic & fail-fast support
- **Comparison matrix engine**: Fit scoring, keyword extraction/coverage, validation aggregation & stuffing detection
- **`loom bulk` command**: Process resume against multiple jobs w/ ranked results & matrix output (JSON/markdown)

### Changed
- **Bulk I/O infrastructure**: Job discovery from directories/manifests/globs, output layout & metadata persistence
- **CLI integration**: Registered bulk command w/ full ArgResolver & exported bulk I/O functions
- **Test coverage**: Comprehensive unit tests for bulk types, scoring & I/O operations (900 lines)

---

## [1.3.4-nightly.20251227] - 2025-12-27

### Added
- **Typst file format support**: Complete .typ resume support w/ template detection & section analysis
- **Typst handler & patterns**: Syntax recognition, safe edit filtering & I/O infrastructure
- **SWE Typst template**: Bundled template w/ metadata & example resume fixture

### Changed
- **CLI integration**: Full Typst workflow support in sectionize, tailor, generate & apply commands
- **Edit filtering**: Generalized safety checks for both LaTeX & Typst formats
- **Test coverage**: Comprehensive unit & integration tests for Typst functionality

---

## [1.3.3-nightly.20251227] - 2025-12-27

### Added
- **ATS analysis system**: Applicant Tracking System analysis command & scoring engine
- **Response caching**: AI response caching system for improved performance
- **Watch mode**: Auto-recompilation workflow support
- **Cache management**: CLI command for cache control operations
- **Verbose mode**: Enhanced verbose logging support across core modules

### Changed
- **Test coverage**: Enhanced test suite for ATS & caching features
- **Integration tests**: Updated prompt/modify operation tests
- **CLI extensibility**: Improved runner & logic for new feature support

---

## [1.3.2-nightly.20251226] - 2025-12-26

### Added
- **Base client architecture**: Template class w/ registry pattern for AI providers
- **Provider validation**: Environment & provider validation modules
- **Testing utilities**: AI client mocking & testing support infrastructure

### Changed
- **AI client migration**: Unified base class architecture for all providers
- **Models catalog**: Simplified catalog & streamlined client API
- **Diff resolution**: Consolidated logic & removed ai_processor module
- **CLI validation**: Updated commands to use new validation API
- **LaTeX handling**: Enhanced pattern extraction & processing

---

## [1.3.1-nightly.20251226] - 2025-12-26

### Changed
- **Prompt optimization**: Token-efficient keys & normalization system
- **Diff display**: Modularized into state, renderer & display components
- **Theme system**: Automatic initialization at startup & enhanced engine
- **File operations**: Consolidated utilities in loom_io module
- **Help system**: Added option introspection capabilities
- **Code cleanup**: Removed deprecated edit_helpers module

---

## [1.3.0] - 2025-12-20

### Added
- **Universal LaTeX handler**: Complete template metadata system with section detection and safe edit filtering
- **Template commands**: `loom templates` for discovery, `loom init` for scaffolding from bundled templates
- **swe-latex template**: Bundled LaTeX resume template with TOML metadata and inline markers
- **Provider caching**: API key and availability caching for OpenAI, Claude, and Ollama
- **GitHub Actions**: CI/CD workflows for testing, releases, and prerelease tagging

### Changed
- **AI architecture**: Centralized JSON parsing, response validation, and error handling in `ai/utils.py`
- **Unified tailoring runner**: New `runner.py` consolidates command orchestration logic
- **Diff display**: Refactored with state machine pattern for improved maintainability
- **LaTeX patterns**: Consolidated into dedicated `latex_patterns.py` module
- **Edit helpers**: Extracted shared operation logic to `edit_helpers.py`
- **Code formatting**: Applied Black formatter across entire codebase

### Infrastructure
- **Test coverage**: 809 tests at 88% coverage with pytest-socket network isolation
- **Build system**: Package data support for template distribution

---

## [1.2.11] - 2025-12-20

### Changed
- **Diff display refactoring**: Restructured `diff_display.py` with state machine pattern (1193 lines reorganized) for improved maintainability
- **Theme engine enhancements**: Improved `theme_engine.py` implementation
- **Module export cleanup**: Removed unused exports from UI module `__init__.py` files

---

## [1.2.10] - 2025-12-20

### Changed
- **AI response processing**: Centralized response processing and validation logic in `ai/utils.py` (+108 lines)
- **Document utilities**: Reorganized `documents.py` structure (111 lines modified) and enhanced `generics.py` (+8 lines)
- **Plan command**: Simplified `plan.py` command with unified architecture (-64 lines net)

---

## [1.2.9] - 2025-12-20

### Added
- **Comprehensive LaTeX handler**: New `latex_handler.py` module (655 lines) for robust LaTeX document processing

### Changed
- **LaTeX pattern consolidation**: New `latex_patterns.py` module (59 lines) for centralized pattern handling
- **LaTeX I/O infrastructure**: Enhanced `loom_io/__init__.py` with improved exports (+46 lines)
- **AI error handling**: Improved error handling in `ai/utils.py` (+31 lines modified)
- **Test suite updates**: Updated `test_logic.py` and `test_pipeline.py` for new LaTeX functionality

---

## [1.2.8] - 2025-11-23

### Changed
- **Templates directory structure**: Reorganized swe-latex template into `templates/swe-latex/` subdirectory for multi-template support
- **Templates README**: Updated to generic layout documentation with CLI usage examples (`loom templates`, `loom init`)
- **LaTeX build artifacts**: Updated `.gitignore` patterns to support nested templates (`templates/**/*.aux` etc.)
- **Documentation references**: Updated `docs/latex-templates-design.md` to reference both templates layout and template-specific documentation
- **PEP 440 version format**: Updated nightly release format from `-nightly.20251120` to `.dev20251120` for consistency with Python standards
- **Code formatting**: Applied Black formatter to entire codebase for consistent PEP 8 compliance

### Infrastructure
- **Black code formatter**: Integrated into development tooling with configuration in pyproject.toml
- **Optional dependencies**: Moved dev dependencies to `[project.optional-dependencies]` section in pyproject.toml

### Fixed
- **Test failures**: Updated model validation tests to handle "not found" error messages
- **Template path**: Fixed LaTeX handler test to use new template path `templates/swe-latex/resume.tex`

---

## [1.2.6-nightly.20251120] - 2025-11-20

### Added
- **LaTeX handler tests**: Unit tests for `latex_handler` module (section detection, edit filtering, template detection, payload generation)
- **Template command tests**: Unit tests for `templates` and `init` commands (listing, scaffolding, error handling)
- **Integration tests**: LaTeX sectionize workflow validation and template command integration tests

### Changed
- **Test infrastructure**: Made `pytest-socket` optional in `conftest.py` to prevent failures when not installed
- **Code style**: Comment consistency improvements ("using" → "w/")

### Removed
- **Deprecated tests**: Removed 975-line `test_prompt_command.py` (no longer relevant)

---

## [1.2.5-nightly.20251120] - 2025-11-20

### Added
- **Template distribution infrastructure**: `MANIFEST.in` includes `*.tex`, `*.toml`, `*.md` files from templates directory
- **swe-latex template metadata**: Comprehensive `loom-template.toml` with section patterns, frozen paths, and custom metadata
- **Inline template marker**: Added `% loom-template: swe-latex` to `resume.tex` for robust template detection
- **Package data support**: Enabled `include-package-data = true` in `pyproject.toml` for template bundling

### Changed
- **Templates README**: Updated with CLI usage instructions (`loom templates`, `loom init`) and removed "Future Integration" section

---

## [1.2.4-nightly.20251120] - 2025-11-20

### Added
- **LaTeX-aware sectionize**: `.tex` files now bypass AI and use native handler for instant section extraction
- **LaTeX auto-sectionization**: `tailor` and `apply` commands auto-generate sections for LaTeX when not provided
- **Template detection helpers**: New `build_latex_context()` function centralizes template detection logic
- **LaTeX edit filtering**: `apply_edits_core()` now filters edits to preserve LaTeX structure and display safety notes

### Changed
- **Sectionize workflow**: Model parameter no longer required for LaTeX files
- **Progress indicators**: Adjusted step counts for LaTeX vs DOCX processing (3 vs 4 steps)
- **Template metadata display**: Commands show detected template ID and notes when LaTeX templates found
- **Error message style**: Updated mutual exclusivity messages ("and" → "&")

---

## [1.2.3-nightly.20251120] - 2025-11-20

### Added
- **Template discovery command**: `loom templates` lists all bundled LaTeX templates with metadata
- **Template initialization command**: `loom init --template <id>` scaffolds new resume workspaces from templates
- **Template command help**: Enhanced help system with option metadata and usage examples for template commands

### Changed
- **CLI app registration**: Added `templates` and `init` commands to main app
- **Help renderer**: Updated quick usage guide with template workflow examples
- **Code style**: Minor comment consistency improvements ("the app" → "app", "and" → "&")

---

## [1.2.2-nightly.20251120] - 2025-11-20

### Added
- **Universal LaTeX handler**: New `latex_handler.py` module with template metadata support
  - `TemplateDescriptor`, `LatexSection`, `LatexAnalysis` dataclasses for structured LaTeX processing
  - Template detection via `loom-template.toml` files or inline `% loom-template: <id>` markers
  - Generic LaTeX section detection supporting `\section`, `\subsection`, `\cvsection`, `\sectionhead`
  - Semantic section matching for Education, Experience, Projects, Skills, Publications, Certifications
  - Intelligent bullet detection (`\item`, `\entry`, `\cventry`, `\cvitem`)
  - Safe edit filtering to preserve LaTeX structure (frozen paths, structural patterns, command preservation)
- **LaTeX handler API**: Exported functions `detect_template()`, `analyze_latex()`, `sections_to_payload()`, `filter_latex_edits()`, `load_descriptor()`
- **Design documentation**: Comprehensive architecture guide in `docs/latex-templates-design.md`

---

## [1.2.1-nightly.20250901] - 2025-09-01

### Added
- **Git hooks for automated versioning**: Install script and pre-commit/pre-push hooks to automatically version nightly releases and ensure changelog consistency

---

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
