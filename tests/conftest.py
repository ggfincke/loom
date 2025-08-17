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
    # patch Path.home() to isolated temp directory
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    
    # create isolated .loom directory
    loom_dir = fake_home / ".loom"
    loom_dir.mkdir()
    
    # create minimal config.json w/ test defaults
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
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "risk": "ask",
        "theme": "deep_blue"
    }
    
    config_file = loom_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    # patch Path.home() to return fake home
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    
    return fake_home


@pytest.fixture(autouse=True)
def block_network():
    # block all network calls by default using pytest-socket
    # tests requiring network must explicitly enable w/ pytest.mark.enable_socket
    pytest_socket = pytest.importorskip("pytest_socket")
    pytest_socket.disable_socket()


@pytest.fixture
def temp_output_dirs(tmp_path):
    # provide isolated temp directories for all file operations
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
        "base": tmp_path
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    # seed test environment w/ required API keys & settings
    test_env = {
        "OPENAI_API_KEY": "test-openai-key-12345",
        "ANTHROPIC_API_KEY": "test-anthropic-key-12345", 
        "OLLAMA_HOST": "http://localhost:11434"
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
def mock_ai_client():
    # create mock AI client for testing w/o real API calls
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="mock response"))]
    )
    return mock_client


@pytest.fixture
def sample_resume_content():
    # provide sample resume text for testing
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
    # provide sample job posting for testing
    return """Senior Python Developer
Tech Company is seeking an experienced Python developer to join our team.

Requirements:
• 5+ years Python experience
• Experience w/ web frameworks
• Strong problem-solving skills
• AWS/cloud experience preferred"""


@pytest.fixture
def sample_sections_data():
    # provide expected section parsing output
    return {
        "sections": [
            {
                "name": "HEADER",
                "heading_text": "John Doe",
                "start_line": 1,
                "end_line": 2,
                "confidence": 0.95,
                "subsections": []
            },
            {
                "name": "SUMMARY", 
                "heading_text": "PROFESSIONAL SUMMARY",
                "start_line": 4,
                "end_line": 5,
                "confidence": 0.99,
                "subsections": []
            },
            {
                "name": "SKILLS",
                "heading_text": "SKILLS", 
                "start_line": 7,
                "end_line": 9,
                "confidence": 0.98,
                "subsections": []
            }
        ]
    }


@pytest.fixture
def sample_edits_data():
    # provide expected edit operations output
    return {
        "edits": [
            {
                "operation": "replace_line",
                "line_number": 5,
                "content": "Experienced Python developer w/ 5+ years building scalable applications.",
                "reasoning": "Emphasize Python experience & scalability"
            },
            {
                "operation": "insert_after",
                "line_number": 9,
                "content": "• AWS, Lambda, CloudFormation",
                "reasoning": "Add cloud experience mentioned in job requirements"
            }
        ]
    }