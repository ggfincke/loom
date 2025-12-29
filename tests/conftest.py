# tests/conftest.py
# Pytest configuration w/ isolation fixtures for deterministic test runs

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    # Patch Path.home() to isolated temp directory
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()

    # Create isolated .loom directory
    loom_dir = fake_home / ".loom"
    loom_dir.mkdir()

    # Create minimal config.json w/ test defaults
    config_data = {
        "data_dir": "data",
        "output_dir": "output",
        "resume_filename": "resume.docx",
        "job_filename": "job.txt",
        "sections_filename": "sections.json",
        "edits_filename": "edits.json",
        "base_dir": ".loom",
        "warnings_filename": "edits.warnings.txt",
        "diff_filename": "diff.patch",
        "plan_filename": "plan.txt",
        "model": "gpt-5-mini",
        "temperature": 0.2,
        "risk": "ask",
        "theme": "deep_blue",
        "interactive": True,
        "dev_mode": False,
    }

    config_file = loom_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    # Patch Path.home() to return fake home
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # ! reset global settings_manager state & patch its config_path to use isolated location
    from src.config.settings import settings_manager, SettingsManager

    settings_manager._settings = None
    settings_manager.config_path = fake_home / ".loom" / "config.json"

    # ! reset LoomColors cache to pick up isolated settings
    from src.ui.theming.theme_engine import reset_color_cache

    reset_color_cache()

    # ! reset dev mode cache to pick up isolated settings
    from src.config.dev_mode import reset_dev_mode_cache

    reset_dev_mode_cache()

    # ! reset & disable response cache to prevent caching during tests
    from src.ai.cache import reset_response_cache, disable_cache_for_invocation

    reset_response_cache()
    disable_cache_for_invocation()

    # ! reset output manager to NullOutputManager for test isolation
    from src.core.output import reset_output_manager

    reset_output_manager()

    return fake_home


@pytest.fixture(autouse=True)
def block_network():
    # Block all network calls by default w/ pytest-socket
    # tests requiring network must explicitly enable w/ pytest.mark.enable_socket
    try:
        pytest_socket = pytest.importorskip("pytest_socket")
        pytest_socket.disable_socket()
    except pytest.skip.Exception:
        # Pytest-socket not installed, skip network blocking
        pass


@pytest.fixture
def temp_output_dirs(tmp_path):
    # Provide isolated temp directories for all file operations
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    loom_dir = tmp_path / ".loom"

    data_dir.mkdir()
    output_dir.mkdir()
    loom_dir.mkdir()

    return {
        "data_dir": data_dir,
        "output_dir": output_dir,
        "loom_dir": loom_dir,
        "base": tmp_path,
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    # Seed test environment w/ required API keys & settings
    test_env = {
        "OPENAI_API_KEY": "test-openai-key-12345",
        "ANTHROPIC_API_KEY": "test-anthropic-key-12345",
        "OLLAMA_HOST": "http://localhost:11434",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def mock_ai_client():
    # Create mock AI client for testing w/o real API calls
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="mock response"))]
    )
    return mock_client


@pytest.fixture
def sample_resume_content():
    # Provide sample resume text for testing
    return """John Doe
Software Engineer

PROFESSIONAL SUMMARY
Experienced software engineer w/ 5+ years developing web applications.

SKILLS
• Python, JavaScript, React
• Docker, AWS, CI/CD

EXPERIENCE
Senior Developer | Tech Corp | 2020-2024
• Built scalable web applications
• Led team of 3 developers"""


@pytest.fixture
def sample_job_description():
    # Provide sample job posting for testing
    return """Software Engineer - Python developer

We are looking for a Python developer to join our team.

Requirements:
• 3+ years experience w/ Python
• Experience w/ REST APIs
• AWS knowledge preferred"""


@pytest.fixture
def sample_sections_data():
    # Provide expected section parsing output
    return {
        "sections": [
            {
                "name": "HEADER",
                "heading_text": "John Doe",
                "start_line": 1,
                "end_line": 2,
                "confidence": 0.95,
                "subsections": [],
            },
            {
                "name": "SUMMARY",
                "heading_text": "PROFESSIONAL SUMMARY",
                "start_line": 4,
                "end_line": 5,
                "confidence": 0.99,
                "subsections": [],
            },
            {
                "name": "SKILLS",
                "heading_text": "SKILLS",
                "start_line": 7,
                "end_line": 9,
                "confidence": 0.98,
                "subsections": [],
            },
        ]
    }


@pytest.fixture
def sample_edits_data():
    # Provide expected edit operations output
    return {
        "edits": [
            {
                "operation": "replace_line",
                "line_number": 5,
                "content": "Experienced Python developer w/ 5+ years building scalable applications.",
                "reasoning": "Emphasize Python experience & scalability",
            },
            {
                "operation": "insert_after",
                "line_number": 9,
                "content": "• AWS, Lambda, CloudFormation",
                "reasoning": "Add cloud experience mentioned in job requirements",
            },
        ]
    }


@pytest.fixture
def sample_lines_dict():
    # Lines dict for core pipeline testing
    return {
        1: "John Doe",
        2: "Software Engineer",
        3: "",
        4: "PROFESSIONAL SUMMARY",
        5: "Experienced software engineer w/ 5+ years developing web applications.",
        6: "",
        7: "SKILLS",
        8: "• Python, JavaScript, React",
        9: "• Docker, AWS, CI/CD",
        10: "",
        11: "EXPERIENCE",
        12: "Senior Developer | Tech Corp | 2020-2024",
        13: "• Built scalable web applications",
        14: "• Led team of 3 developers",
    }


@pytest.fixture
def valid_edits_v1():
    # Valid edits dict w/ version 1 format for pipeline testing
    return {
        "version": 1,
        "meta": {"model": "gpt-4o", "created_at": "2024-01-01T00:00:00Z"},
        "ops": [
            {
                "op": "replace_line",
                "line": 5,
                "text": "Experienced Python developer w/ 5+ years building scalable applications.",
            }
        ],
    }


@pytest.fixture
def mock_ai_success_response():
    # Mock successful AI response for testing
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.data = {
        "version": 1,
        "meta": {"model": "gpt-5"},
        "ops": [{"op": "replace_line", "line": 5, "text": "Updated summary"}],
    }
    return mock_response


@pytest.fixture
def mock_ai_failure_response():
    # Mock failed AI response for testing
    mock_response = MagicMock()
    mock_response.success = False
    mock_response.error = "Invalid JSON syntax"
    mock_response.json_text = '{"invalid": json}'
    mock_response.raw_text = None
    return mock_response


@pytest.fixture
def isolate_output():
    from src.core.output import reset_output_manager

    reset_output_manager()
    yield
    reset_output_manager()


@pytest.fixture
def dev_mode_enabled(isolate_config):
    # Enable dev_mode for tests that require it
    config_file = isolate_config / ".loom" / "config.json"

    with open(config_file, "r") as f:
        config_data = json.load(f)

    config_data["dev_mode"] = True

    with open(config_file, "w") as f:
        json.dump(config_data, f)

    # Reset caches to pick up new settings
    from src.config.settings import settings_manager

    settings_manager._settings = None

    from src.config.dev_mode import reset_dev_mode_cache

    reset_dev_mode_cache()

    return isolate_config
