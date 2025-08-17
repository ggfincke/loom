# Testing Infrastructure Guide

This document covers Loom's testing infrastructure, how to run tests effectively, and how to write new tests that integrate with the existing test framework.

## How to Run Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

# Run tests in specific directories
pytest tests/unit/       # All unit tests
pytest tests/integration/ # All integration tests
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=85
```

### Parallel Test Execution

```bash
# Run tests in parallel (faster execution)
pytest -n auto           # Auto-detect CPU cores
pytest -n 4             # Use 4 processes
```

### Running Specific Tests

```bash
# Run specific test file
pytest tests/unit/test_pipeline.py

# Run specific test class
pytest tests/unit/test_pipeline.py::TestApplyEdits

# Run specific test method
pytest tests/unit/test_pipeline.py::TestApplyEdits::test_single_operation_success

# Run tests matching pattern
pytest -k "pipeline"     # All tests with "pipeline" in name
pytest -k "not slow"     # All tests except those marked slow
```

## Test Configuration

### Test Markers

Tests are organized using pytest markers defined in `pytest.ini`:

- `@pytest.mark.unit` - Fast unit tests for individual functions/classes
- `@pytest.mark.integration` - Integration tests that test component interaction
- `@pytest.mark.e2e` - End-to-end tests that test full workflows
- `@pytest.mark.slow` - Tests that take longer to run (can be skipped)

### Configuration Files

- **`pytest.ini`** - Main pytest configuration
  - Test discovery paths
  - Coverage settings (75% minimum)
  - Warning filters
  - Default options (`-v`, coverage reporting)

- **`requirements.txt`** - Testing dependencies
  - `pytest` - Test framework
  - `pytest-cov` - Coverage reporting
  - `pytest-mock` - Mocking utilities
  - `pytest-socket` - Network call blocking
  - `pytest-xdist` - Parallel execution
  - `freezegun` - Time mocking
  - `faker` - Test data generation

## Test Structure & Organization

### Directory Structure

```
tests/
├── conftest.py              # Global fixtures & configuration
├── fixtures/                # Static test data
│   ├── sample_resumes/
│   ├── sample_sections/
│   ├── sample_edits/
│   └── mock_responses/
├── unit/                    # Unit tests
│   ├── test_pipeline.py     # Core edit operations
│   ├── test_validation.py   # Validation logic
│   ├── test_exceptions.py   # Error handling
│   └── test_constants.py    # Enum definitions
└── integration/             # Integration tests
    └── test_config_integration.py
```

### Test Categories

**Unit Tests** (`tests/unit/`)
- Test individual functions and classes in isolation
- Fast execution (< 1 second per test)
- Heavy use of mocking for external dependencies
- Focus on business logic and edge cases

**Integration Tests** (`tests/integration/`)
- Test interaction between components
- May involve file I/O, configuration loading
- Slower execution but still isolated from network

**End-to-End Tests** (future)
- Test complete workflows from CLI to output
- May involve real file operations and AI calls

## Test Isolation & Fixtures

### Automatic Isolation

All tests automatically use these isolation fixtures:

```python
@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    # Creates isolated ~/.loom directory
    # Patches Path.home() to return temp directory
    # Provides clean config.json for each test

@pytest.fixture(autouse=True) 
def block_network():
    # Blocks all network calls by default
    # Tests requiring network must use @pytest.mark.enable_socket
```

### Available Fixtures

**Configuration & Environment**
```python
def test_example(isolate_config, mock_env_vars, temp_output_dirs):
    # isolate_config: Isolated ~/.loom config
    # mock_env_vars: Test API keys & environment
    # temp_output_dirs: Isolated data/output/loom directories
```

**Sample Data**
```python
def test_example(sample_resume_content, sample_job_description, sample_sections_data):
    # Pre-defined test content for consistent testing
```

**Core Logic Testing**
```python
def test_example(sample_lines_dict, valid_edits_v1, mock_ai_success_response):
    # sample_lines_dict: Lines dict for pipeline testing
    # valid_edits_v1: Valid edits structure for testing
    # mock_ai_success_response: Mock successful AI response
```

### Creating Custom Fixtures

Add fixtures to `tests/conftest.py`:

```python
@pytest.fixture
def custom_resume_data():
    return {
        1: "Custom Name",
        2: "Custom Title",
        # ... more lines
    }

@pytest.fixture
def mock_external_service():
    with patch('src.module.external_call') as mock:
        mock.return_value = "test response"
        yield mock
```

## Writing Effective Tests

### Test Structure Guidelines

Follow the **Arrange-Act-Assert** pattern:

```python
def test_apply_edits_replace_line(sample_lines_dict):
    # Arrange
    edits = {
        "version": 1,
        "ops": [{"op": "replace_line", "line": 5, "text": "New content"}]
    }
    
    # Act
    result = apply_edits(sample_lines_dict, edits)
    
    # Assert
    assert result[5] == "New content"
    assert len(result) == len(sample_lines_dict)  # No lines added/removed
```

### Parametrized Testing

Use `@pytest.mark.parametrize` for systematic testing:

```python
@pytest.mark.parametrize("op_type,op_data,expected", [
    ("replace_line", {"line": 5, "text": "New"}, {5: "New"}),
    ("insert_after", {"line": 5, "text": "New"}, "inserted_content"),
    ("delete_range", {"start": 5, "end": 6}, "deleted_content"),
])
def test_edit_operations(sample_lines_dict, op_type, op_data, expected):
    edits = {"version": 1, "ops": [{"op": op_type, **op_data}]}
    result = apply_edits(sample_lines_dict, edits)
    # Verify expected behavior based on operation type
```

### Testing Error Conditions

Always test both success and failure cases:

```python
def test_edit_operation_success(sample_lines_dict):
    # Test successful operation
    edits = {"version": 1, "ops": [{"op": "replace_line", "line": 5, "text": "New"}]}
    result = apply_edits(sample_lines_dict, edits)
    assert result[5] == "New"

def test_edit_operation_out_of_bounds(sample_lines_dict):
    # Test error condition
    edits = {"version": 1, "ops": [{"op": "replace_line", "line": 999, "text": "New"}]}
    with pytest.raises(EditError, match="line 999: line does not exist"):
        apply_edits(sample_lines_dict, edits)
```

### Mocking External Dependencies

Mock AI calls, file operations, and network requests:

```python
@patch('src.core.pipeline.run_generate')
def test_generate_edits_success(mock_run_generate, sample_lines_dict):
    # Setup mock response
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.data = {"version": 1, "ops": []}
    mock_run_generate.return_value = mock_result
    
    # Test function
    result = generate_edits(sample_lines_dict, "job desc", None, "gpt-4o")
    
    # Verify mock was called correctly
    mock_run_generate.assert_called_once()
    assert result["version"] == 1
```

## Test Data Management

### Static Test Fixtures

Store reusable test data in `tests/fixtures/`:

```
tests/fixtures/
├── sample_resumes/
│   ├── basic_resume.txt
│   └── complex_resume.txt
├── sample_sections/
│   └── basic_resume_sections.json
├── sample_edits/
│   └── basic_tailoring_edits.json
└── mock_responses/
    ├── openai_sectionize_response.json
    └── openai_tailor_response.json
```

Load fixture data:

```python
def test_with_fixture_data():
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    
    with open(fixtures_dir / "sample_edits" / "basic_tailoring_edits.json") as f:
        edits = json.load(f)
    
    # Use edits in test...
```

### Dynamic Test Data

Use `faker` for generating random test data:

```python
from faker import Faker

def test_with_dynamic_data():
    fake = Faker()
    
    resume_lines = {
        1: fake.name(),
        2: fake.job(),
        3: fake.text(max_nb_chars=100)
    }
    
    # Test with generated data...
```

## Testing Best Practices

### 1. Test Naming

Use descriptive test names that explain the scenario:

```python
# Good
def test_apply_edits_replace_line_updates_content()
def test_validate_edits_out_of_bounds_line_produces_warning()
def test_handle_loom_error_recoverable_validation_error_returns_none()

# Bad
def test_apply_edits()
def test_validation()
def test_error_handling()
```

### 2. Test Independence

Each test should be completely independent:

```python
# Good - each test has its own data
def test_edit_operation_a(sample_lines_dict):
    edits = {"version": 1, "ops": [{"op": "replace_line", "line": 1, "text": "A"}]}
    result = apply_edits(sample_lines_dict, edits)
    assert result[1] == "A"

def test_edit_operation_b(sample_lines_dict):
    edits = {"version": 1, "ops": [{"op": "replace_line", "line": 1, "text": "B"}]}
    result = apply_edits(sample_lines_dict, edits)
    assert result[1] == "B"

# Bad - tests depend on shared state
shared_data = {"modified": False}

def test_modifies_shared_data():
    shared_data["modified"] = True
    assert shared_data["modified"]

def test_expects_shared_data():  # This will fail if run in different order
    assert shared_data["modified"]
```

### 3. Coverage Goals

Aim for high coverage on core business logic:

- **Core modules** (`src/core/`): 85-90% coverage target
- **CLI modules** (`src/cli/`): 70-80% coverage target
- **I/O modules** (`src/loom_io/`): 75-85% coverage target
- **Configuration** (`src/config/`): 80-90% coverage target

### 4. Test Performance

Keep unit tests fast:

- Unit tests should run in < 1 second
- Use `@pytest.mark.slow` for longer tests
- Mock external dependencies aggressively
- Use `pytest-xdist` for parallel execution

### 5. Error Message Testing

Test specific error messages for better debugging:

```python
def test_validation_error_message():
    with pytest.raises(EditError, match="Cannot replace line 999: line does not exist"):
        # Test code that should raise specific error
```

## Debugging Failed Tests

### Common Debugging Techniques

```bash
# Run single failing test with maximum verbosity
pytest tests/unit/test_pipeline.py::test_failing_test -vvv

# Drop into debugger on failures
pytest --pdb tests/unit/test_pipeline.py

# Print output from tests (pytest captures by default)
pytest -s tests/unit/test_pipeline.py

# Show local variables in tracebacks
pytest --tb=long tests/unit/test_pipeline.py
```

### Test Isolation Issues

If tests pass individually but fail when run together:

```bash
# Run in random order to find order dependencies
pytest --random-order tests/

# Run specific test order that fails
pytest tests/unit/test_a.py tests/unit/test_b.py -v
```

## Continuous Integration

Tests run automatically on:

- Pull requests
- Pushes to main branch
- Scheduled daily runs

CI configuration ensures:

- All test categories pass
- Coverage thresholds met
- No network calls in unit tests
- Tests run in isolated environment

See `.github/workflows/` for CI configuration details.

## Future Testing Enhancements

Planned improvements:

1. **Property-based testing** with Hypothesis for edge case discovery
2. **Performance benchmarks** for core operations
3. **End-to-end tests** with real AI model integration
4. **Mutation testing** to verify test quality
5. **Visual regression testing** for CLI output formatting