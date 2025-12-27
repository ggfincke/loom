# src/ai/clients/base.py
# Template-method base client for AI providers
#
# This class provides the shared run_generate() orchestration.
# Subclasses implement:
# - validate_credentials() - check API key / server availability
# - make_call() - provider-specific API call

import time
from abc import ABC, abstractmethod

from ..types import GenerateResult
from ..utils import APICallContext, parse_json
from ..response_cache import get_response_cache
from ...config.settings import settings_manager
from ...core.exceptions import AIError, ConfigurationError
from ...core.verbose import vlog, vlog_ai_request, vlog_ai_response, vlog_think


# abstract base class for AI provider clients
# implements template-method pattern for run_generate():
# 1. preflight() - credential check & setup (overridable)
# 2. validate_model() - model validation (overridable)
# 3. make_call() - provider-specific API call (abstract)
# 4. parse & return GenerateResult
# always returns GenerateResult, never raises exceptions to callers
class BaseClient(ABC):

    # * Subclasses must set this to their canonical provider ID
    provider_name: str = ""

    # template method - always returns GenerateResult, never raises
    # orchestrates: cache check -> preflight -> validate_model -> make_call -> parse -> cache store
    def run_generate(self, prompt: str, model: str) -> GenerateResult:
        # get cache & settings for temperature
        cache = get_response_cache()
        settings = settings_manager.load()
        temperature = settings.temperature

        # check cache first
        if cache.enabled:
            cached_result = cache.get(prompt, model, temperature)
            if cached_result is not None:
                vlog("CACHE", f"Cache hit for {self.provider_name}/{model}")
                return cached_result

        try:
            self.preflight()
            validated_model = self.validate_model(model)

            # log request before making call
            vlog_ai_request(
                provider=self.provider_name,
                model=validated_model,
                prompt_length=len(prompt),
                temperature=temperature,
            )

            start_time = time.time()
            ctx = self.make_call(prompt, validated_model)
            duration_ms = (time.time() - start_time) * 1000

            result = self._process_response(ctx)

            # log response after call completes
            vlog_ai_response(
                provider=self.provider_name,
                model=validated_model,
                response_length=len(ctx.raw_text) if ctx.raw_text else 0,
                success=result.success,
                duration_ms=duration_ms,
                error=result.error if not result.success else None,
            )

            # store successful results in cache
            if cache.enabled and result.success:
                cache.set(prompt, model, temperature, result)

            return result
        except ConfigurationError as e:
            vlog_think(f"Configuration error for {self.provider_name}: {e}")
            return GenerateResult(success=False, error=str(e))
        except AIError as e:
            vlog_ai_response(
                provider=self.provider_name,
                model=model,
                response_length=0,
                success=False,
                error=str(e),
            )
            return GenerateResult(success=False, error=str(e))
        except Exception as e:
            vlog_ai_response(
                provider=self.provider_name,
                model=model,
                response_length=0,
                success=False,
                error=f"Unexpected: {e}",
            )
            return GenerateResult(
                success=False, error=f"Unexpected error in {self.provider_name}: {e}"
            )

    # pre-call setup hook (default: validate credentials)
    # override in subclasses for additional setup (e.g., Ollama server check)
    def preflight(self) -> None:
        self.validate_credentials()

    @abstractmethod
    # check if required credentials are available
    # raises ConfigurationError if credentials are missing
    def validate_credentials(self) -> None:
        pass

    # validate & resolve model name (default: pass through)
    # override in subclasses that need custom model validation (e.g., Ollama checking against dynamic model list)
    # returns validated model name (may be resolved from alias)
    # raises AIError if model is invalid
    def validate_model(self, model: str) -> str:
        return model

    @abstractmethod
    # make provider-specific API call
    # returns APICallContext w/ raw response
    # raises AIError on API errors
    def make_call(self, prompt: str, model: str) -> APICallContext:
        pass

    # convert API response to GenerateResult
    def _process_response(self, ctx: APICallContext) -> GenerateResult:
        data, json_text, error = parse_json(ctx.raw_text)

        if data is not None:
            return GenerateResult(
                success=True, data=data, raw_text=ctx.raw_text, json_text=json_text
            )
        else:
            return GenerateResult(
                success=False, raw_text=ctx.raw_text, json_text=json_text, error=error
            )
