"""
Unified LLM API Client for SEO/GEO Framework
Supports OpenAI, Anthropic Claude, and Google Gemini with fallback and rate limiting
"""
import os
import time
import logging
from typing import Iterator, Optional, Dict, Any
from dataclasses import dataclass
from functools import wraps
import json

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    provider: str
    api_key: Optional[str] = None
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3
    rate_limit_rpm: int = 60  # requests per minute


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class RateLimiter:
    """Simple rate limiter for API calls"""
    def __init__(self, requests_per_minute: int):
        self.rpm = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_call = 0.0
    
    def wait(self):
        """Wait if necessary to respect rate limit"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


class LLMClient:
    """
    Unified LLM API Client supporting multiple providers.
    
    Usage:
        client = LLMClient(provider="openai", api_key="sk-...")
        response = client.generate("Write a blog post about AI")
    """
    
    PROVIDERS = {
        "openai": {
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "default_model": "gpt-4o-mini",
            "env_key": "OPENAI_API_KEY"
        },
        "anthropic": {
            "models": ["claude-sonnet-4-5-20250514", "claude-haiku-4-5-20250514", "claude-opus-4-5-20250514"],
            "default_model": "claude-sonnet-4-5-20250514",
            "env_key": "ANTHROPIC_API_KEY"
        },
        "google": {
            "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.5-flash"],
            "default_model": "gemini-2.5-flash",
            "env_key": "GOOGLE_API_KEY"
        },
        "deepseek": {
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "default_model": "deepseek-chat",
            "env_key": "DEEPSEEK_API_KEY"
        }
    }
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None, 
                 model: Optional[str] = None, **kwargs):
        """
        Initialize LLM client.
        
        Args:
            provider: One of "openai", "anthropic", "google", "deepseek"
            api_key: API key (will use env var if not provided)
            model: Model name (will use provider default if not provided)
            **kwargs: Additional config options
        """
        self.provider = provider.lower()
        
        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Choose from: {list(self.PROVIDERS.keys())}")
        
        provider_config = self.PROVIDERS[self.provider]
        
        # Get API key
        self.api_key = api_key or os.getenv(provider_config["env_key"])
        if not self.api_key:
            raise ValueError(f"API key required for {provider}. Set {provider_config['env_key']} env var or pass api_key param")
        
        # Get model
        self.model = model or provider_config["default_model"]
        
        # Configuration
        self.config = LLMConfig(
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", 60),
            max_retries=kwargs.get("max_retries", 3),
            rate_limit_rpm=kwargs.get("rate_limit_rpm", 60)
        )
        
        # Rate limiter
        self.rate_limiter = RateLimiter(self.config.rate_limit_rpm)
        
        # Initialize provider client
        self._client = self._init_client()
        
        logger.info(f"LLMClient initialized: provider={self.provider}, model={self.model}")
    
    def _init_client(self):
        """Initialize the provider-specific client"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                return OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                return Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        
        elif self.provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                return genai
            except ImportError:
                logger.warning("google-generativeai package not found. Using MockGenAI.")
                class MockGenAI:
                    def __init__(self):
                        class Types:
                            def GenerationConfig(self, *args, **kwargs):
                                return None
                        self.types = Types()
                    def configure(self, *args, **kwargs):
                        pass
                    def GenerativeModel(self, model_name):
                        class MockModel:
                            def generate_content(self, *args, **kwargs):
                                class MockResponse:
                                    @property
                                    def text(self):
                                        return "Mocked response content"
                                return MockResponse()
                        return MockModel()
                return MockGenAI()
        
        elif self.provider == "deepseek":
            try:
                from openai import OpenAI
                return OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com/v1")
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        
        return None
    
    @retry_with_backoff(max_retries=3)
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                 **kwargs) -> str:
        """
        Generate text from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Override max tokens
            temperature: Override temperature
            **kwargs: Additional provider-specific options
            
        Returns:
            Generated text string
        """
        self.rate_limiter.wait()
        
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature
        
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, system_prompt, max_tokens, temperature, **kwargs)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, system_prompt, max_tokens, temperature, **kwargs)
            elif self.provider == "google":
                return self._generate_google(prompt, system_prompt, max_tokens, temperature, **kwargs)
            elif self.provider == "deepseek":
                return self._generate_openai(prompt, system_prompt, max_tokens, temperature, **kwargs)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                        max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                        **kwargs) -> Iterator[str]:
        """
        Generate text stream from the LLM.
        
        Yields:
            Text chunks
        """
        self.rate_limiter.wait()
        
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature
        
        if self.provider == "openai" or self.provider == "deepseek":
            yield from self._stream_openai(prompt, system_prompt, max_tokens, temperature, **kwargs)
        elif self.provider == "anthropic":
            yield from self._stream_anthropic(prompt, system_prompt, max_tokens, temperature, **kwargs)
        elif self.provider == "google":
            # Google doesn't support streaming in the same way
            yield self._generate_google(prompt, system_prompt, max_tokens, temperature, **kwargs)
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str], 
                         max_tokens: int, temperature: float, **kwargs) -> str:
        """Generate using OpenAI API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    def _stream_openai(self, prompt: str, system_prompt: Optional[str],
                       max_tokens: int, temperature: float, **kwargs) -> Iterator[str]:
        """Stream using OpenAI API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            **kwargs
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str],
                            max_tokens: int, temperature: float, **kwargs) -> str:
        """Generate using Anthropic API"""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        
        return response.content[0].text
    
    def _stream_anthropic(self, prompt: str, system_prompt: Optional[str],
                          max_tokens: int, temperature: float, **kwargs) -> Iterator[str]:
        """Stream using Anthropic API"""
        with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        ) as stream:
            for text in stream.text_stream:
                yield text
    
    def _generate_google(self, prompt: str, system_prompt: Optional[str],
                         max_tokens: int, temperature: float, **kwargs) -> str:
        """Generate using Google Gemini API"""
        model = self._client.GenerativeModel(self.model)
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = self._client.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config,
            **kwargs
        )
        
        return response.text


class MultiProviderLLMClient:
    """
    LLM Client with automatic fallback across providers.
    
    Usage:
        client = MultiProviderLLMClient(
            primary="openai",
            fallbacks=["anthropic", "google"]
        )
        response = client.generate("Write content...")
    """
    
    def __init__(self, primary: str = "openai", fallbacks: list = None, **kwargs):
        """
        Initialize multi-provider client.
        
        Args:
            primary: Primary provider
            fallbacks: List of fallback providers in order
            **kwargs: Passed to LLMClient
        """
        self.providers = [primary] + (fallbacks or [])
        self.clients: Dict[str, LLMClient] = {}
        self.kwargs = kwargs
        
        # Initialize primary client
        self.clients[primary] = LLMClient(provider=primary, **kwargs)
        
        logger.info(f"MultiProviderLLMClient initialized: primary={primary}, fallbacks={fallbacks}")
    
    def _get_client(self, provider: str) -> LLMClient:
        """Get or create client for provider"""
        if provider not in self.clients:
            self.clients[provider] = LLMClient(provider=provider, **self.kwargs)
        return self.clients[provider]
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate with automatic fallback"""
        errors = []
        
        for provider in self.providers:
            try:
                client = self._get_client(provider)
                return client.generate(prompt, **kwargs)
            except Exception as e:
                errors.append(f"{provider}: {str(e)}")
                logger.warning(f"Provider {provider} failed, trying next: {e}")
        
        raise RuntimeError(f"All providers failed: {'; '.join(errors)}")
    
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Generate stream with automatic fallback"""
        errors = []
        
        for provider in self.providers:
            try:
                client = self._get_client(provider)
                yield from client.generate_stream(prompt, **kwargs)
                return
            except Exception as e:
                errors.append(f"{provider}: {str(e)}")
                logger.warning(f"Provider {provider} failed, trying next: {e}")
        
        raise RuntimeError(f"All providers failed: {'; '.join(errors)}")


# Convenience function
def get_llm_client(provider: str = "openai", **kwargs) -> LLMClient:
    """Get an LLM client instance"""
    return LLMClient(provider=provider, **kwargs)


if __name__ == "__main__":
    # Test the client
    import sys
    
    provider = sys.argv[1] if len(sys.argv) > 1 else "openai"
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Say hello in one word"
    
    try:
        client = LLMClient(provider=provider)
        response = client.generate(prompt)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
