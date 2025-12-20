# tests/test_support/mock_ai.py
# Deterministic AI mock for predictable test responses across all providers

import json
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from unittest.mock import Mock

from src.ai.types import GenerateResult
from src.ai.utils import strip_markdown_code_blocks


# * Mock AI client returning predictable responses by provider & prompt kind
class DeterministicMockAI:

    def __init__(self, fixtures_dir: Optional[Path] = None):
        if fixtures_dir is None:
            # default to fixtures directory relative to this file
            fixtures_dir = Path(__file__).parent.parent / "fixtures" / "mock_responses"

        self.fixtures_dir = fixtures_dir
        self._fixture_cache: Dict[Tuple[str, str], Any] = {}
        self._load_fixtures()

    # * Load all fixture files into memory for fast access
    def _load_fixtures(self):
        for provider in ["openai", "anthropic", "ollama"]:
            provider_dir = self.fixtures_dir / provider
            if provider_dir.exists():
                for fixture_file in provider_dir.glob("*.json"):
                    fixture_name = fixture_file.stem
                    try:
                        with open(fixture_file, "r") as f:
                            fixture_data = json.load(f)
                        self._fixture_cache[(provider, fixture_name)] = fixture_data
                    except Exception as e:
                        # store error info for debugging
                        self._fixture_cache[(provider, fixture_name)] = {
                            "error": f"Failed to load fixture: {str(e)}"
                        }

    # * Detect prompt type based on content patterns
    def _detect_prompt_kind(self, prompt: str) -> str:
        if "section parser" in prompt.lower() or "analyze a resume" in prompt.lower():
            return "sectionize"
        elif "resume editor" in prompt.lower() or "tailor" in prompt.lower():
            return "tailor"
        elif "fix validation errors" in prompt.lower():
            return "edit_fix"
        else:
            return "unknown"

    # * Get fixture data for provider & fixture name
    def _get_fixture(self, provider: str, fixture_name: str) -> Any:
        key = (provider, fixture_name)
        if key in self._fixture_cache:
            fixture_data = self._fixture_cache[key]
            # check if fixture loading failed
            if (
                isinstance(fixture_data, dict)
                and "error" in fixture_data
                and len(fixture_data) == 1
            ):
                return fixture_data
            return fixture_data
        else:
            return {
                "error": {
                    "type": "connection_error",
                    "message": f"Fixture not found: {provider}/{fixture_name}",
                }
            }

    # * Simulate OpenAI Responses API response format
    def _simulate_openai_response(self, fixture_data: Dict) -> GenerateResult:
        if "error" in fixture_data:
            error_info = fixture_data["error"]
            error_type = error_info.get("type", "unknown")

            # map error types to expected test messages
            if error_type == "connection_error":
                return GenerateResult(success=False, error="Connection error.")
            elif error_type == "permission_error":
                return GenerateResult(
                    success=False, error="Permission denied: unable to write file."
                )
            else:
                return GenerateResult(
                    success=False,
                    error=f"OpenAI API error: {error_info.get('message', 'Unknown error')}",
                )

        raw_text = fixture_data.get("output_text", "")

        # simulate potential JSON parsing
        try:
            data = json.loads(raw_text)
            return GenerateResult(
                success=True, data=data, raw_text=raw_text, json_text=raw_text
            )
        except json.JSONDecodeError as e:
            return GenerateResult(
                success=False,
                raw_text=raw_text,
                json_text=raw_text,
                error=f"AI failed to generate valid JSON: JSON parsing failed: {str(e)}",
            )

    # * Simulate Anthropic Messages API response format
    def _simulate_anthropic_response(self, fixture_data: Dict) -> GenerateResult:
        if "error" in fixture_data:
            error_info = fixture_data["error"]
            error_type = error_info.get("type", "unknown")

            # map error types to expected test messages
            if error_type == "connection_error":
                return GenerateResult(success=False, error="Connection error.")
            elif error_type == "permission_error":
                return GenerateResult(
                    success=False, error="Permission denied: unable to write file."
                )
            else:
                return GenerateResult(
                    success=False,
                    error=f"Anthropic API error: {error_info.get('message', 'Unknown error')}",
                )

        # extract text from content blocks (matching actual client behavior)
        raw_text = ""
        for content_block in fixture_data.get("content", []):
            if content_block.get("type") == "text":
                raw_text += content_block.get("text", "")

        # simulate markdown code block stripping (matching actual client)
        json_text = self._strip_markdown_code_blocks(raw_text)

        try:
            data = json.loads(json_text)
            return GenerateResult(
                success=True, data=data, raw_text=raw_text, json_text=json_text
            )
        except json.JSONDecodeError as e:
            return GenerateResult(
                success=False,
                raw_text=raw_text,
                json_text=json_text,
                error=f"AI failed to generate valid JSON: JSON parsing failed: {str(e)}",
            )

    # * Simulate Ollama chat API response format
    def _simulate_ollama_response(self, fixture_data: Dict) -> GenerateResult:
        if "error" in fixture_data:
            error_info = fixture_data["error"]
            error_type = error_info.get("type", "unknown")

            # map error types to expected test messages
            if error_type == "connection_error":
                return GenerateResult(success=False, error="Connection error.")
            elif error_type == "permission_error":
                return GenerateResult(
                    success=False, error="Permission denied: unable to write file."
                )
            else:
                return GenerateResult(
                    success=False,
                    error=f"Ollama error: {error_info.get('message', 'Unknown error')}",
                )

        raw_text = fixture_data.get("message", {}).get("content", "")

        # simulate thinking token & code block stripping (matching actual client)
        json_text = self._strip_thinking_and_code_blocks(raw_text)

        try:
            data = json.loads(json_text)
            return GenerateResult(
                success=True, data=data, raw_text=raw_text, json_text=json_text
            )
        except json.JSONDecodeError as e:
            return GenerateResult(
                success=False,
                raw_text=raw_text,
                json_text=json_text,
                error=f"AI failed to generate valid JSON: JSON parsing failed: {str(e)}",
            )

    # * Strip markdown/thinking tokens using centralized util (from ai/utils.py)
    def _strip_markdown_code_blocks(self, text: str) -> str:
        # ! use centralized strip_markdown_code_blocks from ai/utils.py
        return strip_markdown_code_blocks(text)

    # * Strip thinking tokens & code blocks (matching Ollama client behavior)
    def _strip_thinking_and_code_blocks(self, text: str) -> str:
        # ! centralized strip_markdown_code_blocks already handles both
        return strip_markdown_code_blocks(text)

    # * Generate response based on model & scenario
    def generate(
        self, prompt: str, model: str, scenario: str = "success"
    ) -> GenerateResult:
        # determine provider from model
        if model.startswith("gpt-"):
            provider = "openai"
        elif model.startswith("claude-"):
            provider = "anthropic"
        else:
            provider = "ollama"

        # detect prompt kind if scenario is success
        if scenario == "success":
            prompt_kind = self._detect_prompt_kind(prompt)
            if prompt_kind == "unknown":
                # default to sectionize fallback
                prompt_kind = "sectionize"
            fixture_name = f"{prompt_kind}_success"
        else:
            fixture_name = scenario

        # get fixture data
        fixture_data = self._get_fixture(provider, fixture_name)

        # simulate provider-specific response handling
        if provider == "openai":
            return self._simulate_openai_response(fixture_data)
        elif provider == "anthropic":
            return self._simulate_anthropic_response(fixture_data)
        elif provider == "ollama":
            return self._simulate_ollama_response(fixture_data)
        else:
            return GenerateResult(success=False, error=f"Unknown provider: {provider}")


# * Create simple mock that patches the main factory function directly
def create_simple_ai_mock(mock_ai: DeterministicMockAI, scenario: str = "success"):
    def run_generate_mock(prompt: str, model: str) -> GenerateResult:
        return mock_ai.generate(prompt, model, scenario)

    return run_generate_mock


# * Create mock patches for all AI clients (legacy)
def create_ai_client_mocks(
    mock_ai: DeterministicMockAI, scenario: str = "success"
) -> Dict[str, Mock]:
    def openai_mock(prompt: str, model: str = "gpt-5-mini") -> GenerateResult:
        return mock_ai.generate(prompt, model, scenario)

    def claude_mock(
        prompt: str, model: str = "claude-sonnet-4-20250514"
    ) -> GenerateResult:
        return mock_ai.generate(prompt, model, scenario)

    def ollama_mock(prompt: str, model: str = "llama3.2") -> GenerateResult:
        return mock_ai.generate(prompt, model, scenario)

    return {
        "openai_generate": Mock(side_effect=openai_mock),
        "claude_generate": Mock(side_effect=claude_mock),
        "ollama_generate": Mock(side_effect=ollama_mock),
    }


# * Create error-specific mock function for direct patching
def create_error_mock(mock_ai: DeterministicMockAI, scenario: str):
    def error_mock(prompt: str, model: str) -> GenerateResult:
        return mock_ai.generate(prompt, model, scenario)

    return error_mock


# * Get patch path for AI calls in specific command
def get_ai_patch_path(command: str) -> str:
    if command == "sectionize":
        return "src.cli.commands.sectionize.run_generate"
    elif command == "tailor":
        return "src.core.pipeline.run_generate"
    else:
        return "src.ai.clients.run_generate"
