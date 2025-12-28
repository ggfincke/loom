# src/ai/clients/base.py
# Template-method base client for AI providers w/ cache support & credential validation

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import ClassVar

from ..types import GenerateResult
from ..utils import APICallContext, parse_json
from ..cache import get_response_cache
from ...config.settings import settings_manager
from ...config.env_validator import validate_provider_env, get_missing_env_message
from ...core.exceptions import AIError, ConfigurationError
from ...core.verbose import vlog, vlog_ai_request, vlog_ai_response, vlog_think

# * Abstract base class for AI provider clients using template-method pattern
# Orchestrates: cache check -> preflight -> validate_model -> make_call -> parse -> cache store
# Always returns GenerateResult, never raises exceptions to callers
class BaseClient(ABC):

    # * Subclasses must set this to their canonical provider ID
    provider_name: str = ""

    # * Required environment variables for this provider (empty for Ollama)
    required_env_vars: ClassVar[list[str]] = []

    # * Template method - orchestrate AI generation w/ caching & error handling
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

    # pre-call setup hook (default: validate credentials, override for additional setup)
    def preflight(self) -> None:
        self.validate_credentials()

    # validate API credentials using required_env_vars
    def validate_credentials(self) -> None:
        if self.required_env_vars and self.provider_name:
            if not validate_provider_env(self.provider_name):
                raise ConfigurationError(get_missing_env_message(self.provider_name))

    # validate & resolve model name (override in subclasses for custom validation)
    def validate_model(self, model: str) -> str:
        return model

    # * Make provider-specific API call (subclasses must implement)
    @abstractmethod
    def make_call(self, prompt: str, model: str) -> APICallContext:
        pass

    # convert API response to GenerateResult w/ JSON parsing
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
