# src/ai/clients/base.py
# Template-method base client for AI providers
#
# This class provides the shared run_generate() orchestration.
# Subclasses implement:
# - validate_credentials() - check API key / server availability
# - make_call() - provider-specific API call

from abc import ABC, abstractmethod

from ..types import GenerateResult
from ..utils import APICallContext, parse_json
from ...core.exceptions import AIError, ConfigurationError


class BaseClient(ABC):
    """Abstract base class for AI provider clients.

    Implements template-method pattern for run_generate():
    1. preflight() - credential check & setup (overridable)
    2. validate_model() - model validation (overridable)
    3. make_call() - provider-specific API call (abstract)
    4. parse & return GenerateResult

    Always returns GenerateResult, never raises exceptions to callers.
    """

    # * Subclasses must set this to their canonical provider ID
    provider_name: str = ""

    def run_generate(self, prompt: str, model: str) -> GenerateResult:
        """Template method - always returns GenerateResult, never raises.

        Orchestrates: preflight -> validate_model -> make_call -> parse
        """
        try:
            self.preflight()
            validated_model = self.validate_model(model)
            ctx = self.make_call(prompt, validated_model)
            return self._process_response(ctx)
        except ConfigurationError as e:
            return GenerateResult(success=False, error=str(e))
        except AIError as e:
            return GenerateResult(success=False, error=str(e))
        except Exception as e:
            return GenerateResult(
                success=False, error=f"Unexpected error in {self.provider_name}: {e}"
            )

    def preflight(self) -> None:
        """Pre-call setup hook. Default: validate credentials.

        Override in subclasses for additional setup (e.g., Ollama server check).
        """
        self.validate_credentials()

    @abstractmethod
    def validate_credentials(self) -> None:
        """Check if required credentials are available.

        Raises:
            ConfigurationError: if credentials are missing
        """
        pass

    def validate_model(self, model: str) -> str:
        """Validate & resolve model name. Default: pass through.

        Override in subclasses that need custom model validation
        (e.g., Ollama checking against dynamic model list).

        Args:
            model: Model name to validate

        Returns:
            Validated model name (may be resolved from alias)

        Raises:
            AIError: if model is invalid
        """
        return model

    @abstractmethod
    def make_call(self, prompt: str, model: str) -> APICallContext:
        """Make provider-specific API call.

        Args:
            prompt: The prompt to send
            model: Validated model name

        Returns:
            APICallContext with raw response

        Raises:
            AIError: on API errors
        """
        pass

    def _process_response(self, ctx: APICallContext) -> GenerateResult:
        """Convert API response to GenerateResult."""
        data, json_text, error = parse_json(ctx.raw_text)

        if data is not None:
            return GenerateResult(
                success=True, data=data, raw_text=ctx.raw_text, json_text=json_text
            )
        else:
            return GenerateResult(
                success=False, raw_text=ctx.raw_text, json_text=json_text, error=error
            )
