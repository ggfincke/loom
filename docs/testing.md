# Loom Testing Architecture

This document outlines the testing architecture for Loom, providing a comprehensive guide for writing, running, and maintaining tests. Our goal is to ensure correctness, stability, and performance through a multi-layered and automated testing strategy.

## Core Principles

Our testing philosophy is built on these core principles:

- **Isolation**: Tests run in an isolated environment. Network access is blocked by default, and file system operations are restricted to temporary directories, preventing interference with the user's local setup.
- **Speed**: The test suite is optimized for speed. Fast tests (unit and integration) are the default, while slower, more intensive tests are opt-in. This ensures a rapid feedback loop for developers.
- **Automation**: Tests are executed automatically on every push and pull request via our CI pipeline, ensuring that no code is merged without passing all checks.
- **Comprehensiveness**: We use a mix of test types—unit, integration, and stress—to cover everything from individual functions to complex user workflows.

## Test Organization

The `tests/` directory is structured to clearly separate different types of tests and support code:

-   `tests/unit/`: Contains unit tests that verify individual components in complete isolation. These tests rely heavily on mocking and should never perform real I/O operations.
-   `tests/integration/`: Houses integration tests that check the interaction between different modules. These tests are allowed limited and controlled I/O to test file handling and other integrated behaviors.
-   `tests/stress/`: Includes stress and performance tests designed to push the limits of the application with large inputs or high-frequency operations. These are always marked as `slow`.
-   `tests/fixtures/`: Stores static test data, such as sample resumes, job descriptions, and mock API responses.
-   `tests/test_support/`: Provides testing utilities and helpers, most notably mock AI clients that simulate responses from external services.
-   `tests/conftest.py`: Defines global fixtures and hooks available to all tests, such as configuration for network isolation.

## Running Tests

You can run tests using either `make` (recommended for simplicity) or `pytest` (for more granular control).

### Using `make` (Recommended)

The `Makefile` provides convenient targets for common testing scenarios:

-   `make test`: Runs the complete test suite (excluding slow tests).
-   `make test-fast`: An alias for `make test`, explicitly running tests not marked `slow`.
-   `make test-unit`: Runs only the unit tests.
-   `make test-integration`: Runs only the integration tests.
-   `make test-coverage`: Runs the test suite and generates a coverage report in the terminal and as an HTML file in `htmlcov/`.
-   `make test-mutation`: Performs mutation testing on the core application logic.

### Using `pytest` (Advanced)

For more control, you can invoke `pytest` directly:

-   **Run all fast tests**: `pytest`
-   **Run slow tests**: `pytest --runslow`
-   **Run tests by path**: `pytest tests/unit/test_pipeline.py`
-   **Run tests by marker**: `pytest -m integration`
-   **Run tests in parallel**: `pytest -n auto` (requires `pytest-xdist`)
-   **Filter tests by name**: `pytest -k "pipeline and not slow"`

## Key Architectural Components

### Test Runner: Pytest

We use [Pytest](https://pytest.org) as our test runner. Its configuration is managed in `pytest.ini`, which defines default options, markers, and coverage settings.

### Markers

Markers are used to categorize tests. Key markers include:

-   `unit`, `integration`: For test types.
-   `slow`: For long-running stress or performance tests. These are excluded by default.
-   `enable_socket`: Allows a test to bypass the default network block.

### Fixtures

Fixtures are used to provide a fixed baseline for tests, ensuring they are repeatable. Global fixtures are defined in `tests/conftest.py`, while test data is stored in `tests/fixtures/`.

### Mocking and Isolation

-   **Network Isolation**: The `pytest-socket` plugin blocks all network access by default. Tests that require network access must be explicitly marked with `@pytest.mark.enable_socket`.
-   **Filesystem Isolation**: Tests that write files use a temporary directory provided by Pytest's `tmp_path` fixture, ensuring no artifacts are left on the user's file system.
-   **AI Client Mocking**: To avoid dependencies on external AI services, we use mock clients located in `tests/test_support/mock_ai.py`. These mocks return predictable responses, making AI-dependent logic testable.

### Coverage Analysis

Code coverage is measured using `pytest-cov`. A minimum coverage threshold is enforced in `pytest.ini` and checked during CI runs. To view the full coverage report, run `make test-coverage` and open the `htmlcov/index.html` file.

### Mutation Testing

We use `mutmut` to perform mutation testing, which helps validate the quality of our tests. It modifies the source code in small ways and checks if the test suite "kills" (detects) the change. Configuration is in `mutmut.ini`.

## Writing Tests

-   **Structure**: Follow the Arrange-Act-Assert pattern for clarity.
-   **Parametrization**: Use `@pytest.mark.parametrize` to test multiple scenarios with a single test function.
-   **Assertions**: Write specific and clear assertions. Use `pytest.raises` to check for expected exceptions.
-   **Speed**: Keep tests fast. Unit tests should be sub-second. Mock any expensive operations.

## Continuous Integration (CI)

Our CI pipeline, defined in `.github/workflows/test.yml`, runs on GitHub Actions for every push and pull request. It executes the full suite of fast tests against Python 3.12 and enforces the coverage threshold.

## Debugging Tests

-   **Drop into PDB**: `pytest --pdb`
-   **Increase Verbosity**: `pytest -vv`
-   **Show Print Statements**: `pytest -s`
-   **Longer Tracebacks**: `pytest --tb=long`

## Policies

-   **Adding Stress Tests**: New stress tests should be placed in `tests/stress/` and marked with `@pytest.mark.slow`. They should target performance-critical code paths.
-   **Updating Coverage**: To raise the coverage threshold, first improve the tests to meet the new target locally, then update the `--cov-fail-under` value in `pytest.ini`.

## Future Directions

We are continuously looking to improve our testing architecture. Potential enhancements include:

-   **Property-based testing** with Hypothesis for more robust data-driven tests.
-   **Performance benchmarking** to track performance over time.
-   **Visual regression testing** for CLI output to prevent unintended UI changes.