# tests/unit/test_basic_validation.py
# Basic validation test to verify test infrastructure works correctly

import pytest
import json
from pathlib import Path


def test_pytest_working():
    # basic test to verify pytest is functional
    assert True

# * verify test fixtures are accessible & contain expected data
def test_fixtures_accessible(sample_resume_content, sample_job_description):
    assert "John Doe" in sample_resume_content
    assert "Software Engineer" in sample_resume_content
    assert "Python developer" in sample_job_description
    assert "Requirements:" in sample_job_description


def test_config_isolation(isolate_config):
    # verify config isolation is working
    config_file = isolate_config / ".loom" / "config.json"
    assert config_file.exists()
    
    # check config contains test defaults
    with open(config_file) as f:
        config = json.load(f)
    
    assert config["model"] == "gpt-4o-mini"
    assert config["data_dir"] == "data"


def test_temp_dirs_isolation(temp_output_dirs):
    # verify temporary directories are properly isolated
    assert temp_output_dirs["data_dir"].exists()
    assert temp_output_dirs["output_dir"].exists()
    assert temp_output_dirs["loom_dir"].exists()
    
    # verify dirs are writable
    test_file = temp_output_dirs["data_dir"] / "test.txt"
    test_file.write_text("test content")
    assert test_file.read_text() == "test content"


def test_env_vars_isolated(mock_env_vars):
    # verify environment variables are properly set for tests
    import os
    assert os.getenv("OPENAI_API_KEY") == "test-openai-key-12345"
    assert os.getenv("ANTHROPIC_API_KEY") == "test-anthropic-key-12345"


@pytest.mark.slow
def test_slow_marker():
    # test marked as slow for testing marker functionality
    import time
    time.sleep(0.1)
    assert True


def test_sample_fixtures_loadable():
    # verify sample fixture files can be loaded
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    
    sections_file = fixtures_dir / "sample_sections" / "basic_resume_sections.json"
    assert sections_file.exists()
    
    with open(sections_file) as f:
        sections = json.load(f)
    assert "sections" in sections
    assert len(sections["sections"]) > 0
    
    edits_file = fixtures_dir / "sample_edits" / "basic_tailoring_edits.json"
    assert edits_file.exists()
    
    with open(edits_file) as f:
        edits = json.load(f)
    assert "edits" in edits
    assert len(edits["edits"]) > 0