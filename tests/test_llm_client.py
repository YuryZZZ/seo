"""
Comprehensive test suite for src/llm_client.py

Covers:
    - LLMConfig dataclass defaults
    - RateLimiter minimum-interval enforcement
    - retry_with_backoff success and exhaustion
    - LLMClient initialisation per provider (openai, anthropic, google, deepseek)
    - LLMClient MockGenAI fallback when google.genai unavailable
    - generate() routes to the correct provider method
    - generate_stream() routes correctly for each provider
    - MultiProviderLLMClient automatic fallback on primary failure
    - MultiProviderLLMClient.generate_stream fallback
    - get_llm_client convenience function
    - Edge cases: unknown provider, missing API key
"""

import os
import sys
import time
import types as stdlib_types
import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call

# ---------------------------------------------------------------------------
# Path setup – mirrors the convention used by the rest of the test suite
# ---------------------------------------------------------------------------
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
)

from llm_client import (
    LLMConfig,
    RateLimiter,
    retry_with_backoff,
    LLMClient,
    MultiProviderLLMClient,
    get_llm_client,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_openai_module():
    """Provide a fake openai module whose OpenAI class is a MagicMock."""
    mock_mod = stdlib_types.ModuleType("openai")
    mock_cls = MagicMock(name="OpenAI_class")
    mock_mod.OpenAI = mock_cls
    return mock_mod, mock_cls


@pytest.fixture
def mock_anthropic_module():
    """Provide a fake anthropic module whose Anthropic class is a MagicMock."""
    mock_mod = stdlib_types.ModuleType("anthropic")
    mock_cls = MagicMock(name="Anthropic_class")
    mock_mod.Anthropic = mock_cls
    return mock_mod, mock_cls


@pytest.fixture
def mock_google_genai_module():
    """Provide fake google.genai and google.genai.types modules."""
    # Build the module hierarchy: google → google.genai → google.genai.types
    google_pkg = stdlib_types.ModuleType("google")
    google_pkg.__path__ = []

    genai_mod = stdlib_types.ModuleType("google.genai")
    genai_client_cls = MagicMock(name="genai_Client")
    genai_mod.Client = genai_client_cls

    types_mod = stdlib_types.ModuleType("google.genai.types")
    types_mod.GenerateContentConfig = MagicMock(name="GenerateContentConfig")

    google_pkg.genai = genai_mod

    return {
        "google": google_pkg,
        "google.genai": genai_mod,
        "google.genai.types": types_mod,
        "client_cls": genai_client_cls,
    }


@pytest.fixture
def openai_client(mock_openai_module):
    """Return a fully-mocked LLMClient configured for the openai provider."""
    mock_mod, mock_cls = mock_openai_module
    with patch.dict("sys.modules", {"openai": mock_mod}):
        client = LLMClient(provider="openai", api_key="test-key")
    return client


@pytest.fixture
def anthropic_client(mock_anthropic_module):
    """Return a fully-mocked LLMClient configured for the anthropic provider."""
    mock_mod, mock_cls = mock_anthropic_module
    with patch.dict("sys.modules", {"anthropic": mock_mod}):
        client = LLMClient(provider="anthropic", api_key="test-key")
    return client


@pytest.fixture
def google_client(mock_google_genai_module):
    """Return a fully-mocked LLMClient configured for the google provider."""
    mods = mock_google_genai_module
    with patch.dict("sys.modules", {
        "google": mods["google"],
        "google.genai": mods["google.genai"],
        "google.genai.types": mods["google.genai.types"],
    }):
        client = LLMClient(provider="google", api_key="test-key")
    return client, mods


@pytest.fixture
def deepseek_client(mock_openai_module):
    """Return a fully-mocked LLMClient configured for the deepseek provider."""
    mock_mod, mock_cls = mock_openai_module
    with patch.dict("sys.modules", {"openai": mock_mod}):
        client = LLMClient(provider="deepseek", api_key="test-key")
    return client


# ======================================================================
# 1.  LLMConfig dataclass defaults
# ======================================================================

class TestLLMConfig:
    """Tests for the LLMConfig dataclass."""

    def test_default_values(self):
        """LLMConfig should populate sensible defaults for every optional field."""
        cfg = LLMConfig(provider="openai")
        assert cfg.provider == "openai"
        assert cfg.api_key is None
        assert cfg.model == ""
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.7
        assert cfg.timeout == 60
        assert cfg.max_retries == 3
        assert cfg.rate_limit_rpm == 60

    def test_custom_values(self):
        """LLMConfig should accept and store custom values for all fields."""
        cfg = LLMConfig(
            provider="anthropic",
            api_key="sk-test",
            model="claude-sonnet-4-5-20250514",
            max_tokens=2048,
            temperature=0.3,
            timeout=120,
            max_retries=5,
            rate_limit_rpm=30,
        )
        assert cfg.provider == "anthropic"
        assert cfg.api_key == "sk-test"
        assert cfg.model == "claude-sonnet-4-5-20250514"
        assert cfg.max_tokens == 2048
        assert cfg.temperature == 0.3
        assert cfg.timeout == 120
        assert cfg.max_retries == 5
        assert cfg.rate_limit_rpm == 30

    def test_equality(self):
        """Two LLMConfig instances with the same values should be equal (dataclass __eq__)."""
        a = LLMConfig(provider="openai", api_key="k")
        b = LLMConfig(provider="openai", api_key="k")
        assert a == b


# ======================================================================
# 2.  RateLimiter
# ======================================================================

class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_min_interval_calculation(self):
        """min_interval should equal 60 / requests_per_minute."""
        rl = RateLimiter(requests_per_minute=60)
        assert rl.min_interval == pytest.approx(1.0)

        rl2 = RateLimiter(requests_per_minute=120)
        assert rl2.min_interval == pytest.approx(0.5)

    def test_first_call_does_not_sleep(self):
        """The very first call to wait() should NOT sleep (last_call starts at 0)."""
        rl = RateLimiter(requests_per_minute=60)
        with patch("llm_client.time.sleep") as mock_sleep, \
             patch("llm_client.time.time", return_value=1000.0):
            rl.wait()
            mock_sleep.assert_not_called()

    def test_enforces_minimum_interval(self):
        """wait() should sleep when called faster than the rate limit allows."""
        rl = RateLimiter(requests_per_minute=60)  # 1 req/s → 1.0 s interval

        with patch("llm_client.time.sleep") as mock_sleep, \
             patch("llm_client.time.time") as mock_time:
            # First call at t=100 → sets last_call = 100
            mock_time.return_value = 100.0
            rl.wait()

            # Second call 0.3 s later → must sleep ~0.7 s
            mock_time.return_value = 100.3
            rl.wait()

            mock_sleep.assert_called_once()
            sleep_arg = mock_sleep.call_args[0][0]
            assert sleep_arg == pytest.approx(0.7, abs=0.05)

    def test_no_sleep_when_enough_time_passed(self):
        """wait() should NOT sleep when enough time has elapsed since the last call."""
        rl = RateLimiter(requests_per_minute=60)

        with patch("llm_client.time.sleep") as mock_sleep, \
             patch("llm_client.time.time") as mock_time:
            mock_time.return_value = 100.0
            rl.wait()

            mock_time.return_value = 102.0  # 2 s later – plenty of headroom
            rl.wait()

            mock_sleep.assert_not_called()


# ======================================================================
# 3.  retry_with_backoff
# ======================================================================

class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_succeeds_without_retry(self):
        """Should return immediately when the wrapped function succeeds on the first try."""
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def succeed():
            return "ok"

        assert succeed() == "ok"

    def test_succeeds_after_retries(self):
        """Should return the value after transient failures followed by a success."""
        call_count = {"n": 0}

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("transient")
            return "recovered"

        with patch("llm_client.time.sleep"):  # skip real sleeps
            result = flaky()

        assert result == "recovered"
        assert call_count["n"] == 3

    def test_raises_after_max_retries(self):
        """Should raise the last exception after all retry attempts are exhausted."""
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_fail():
            raise ValueError("permanent")

        with patch("llm_client.time.sleep"):
            with pytest.raises(ValueError, match="permanent"):
                always_fail()

    def test_exponential_delay(self):
        """Should sleep with exponentially increasing delays between retries."""
        @retry_with_backoff(max_retries=4, base_delay=1.0)
        def fail():
            raise RuntimeError("boom")

        with patch("llm_client.time.sleep") as mock_sleep:
            with pytest.raises(RuntimeError):
                fail()

        # 3 sleeps for 4 attempts: 1*2^0, 1*2^1, 1*2^2
        expected = [1.0, 2.0, 4.0]
        actual = [c[0][0] for c in mock_sleep.call_args_list]
        assert actual == expected


# ======================================================================
# 4.  LLMClient initialisation
# ======================================================================

class TestLLMClientInit:
    """Tests for LLMClient.__init__ and _init_client per provider."""

    def test_unknown_provider_raises(self):
        """Passing an unsupported provider name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClient(provider="cohere", api_key="x")

    def test_missing_api_key_raises(self):
        """Must raise ValueError when no API key supplied and no env var set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                LLMClient(provider="openai")

    def test_openai_init(self, mock_openai_module):
        """Should import and construct an OpenAI client for the openai provider."""
        mock_mod, mock_cls = mock_openai_module
        with patch.dict("sys.modules", {"openai": mock_mod}):
            client = LLMClient(provider="openai", api_key="sk-test")

        assert client.provider == "openai"
        assert client.model == "gpt-4o-mini"
        mock_cls.assert_called_once_with(api_key="sk-test")

    def test_anthropic_init(self, mock_anthropic_module):
        """Should import and construct an Anthropic client for the anthropic provider."""
        mock_mod, mock_cls = mock_anthropic_module
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            client = LLMClient(provider="anthropic", api_key="sk-ant")

        assert client.provider == "anthropic"
        assert client.model == "claude-sonnet-4-5-20250514"
        mock_cls.assert_called_once_with(api_key="sk-ant")

    def test_google_init(self, mock_google_genai_module):
        """Should import and construct a google.genai.Client for the google provider."""
        mods = mock_google_genai_module
        with patch.dict("sys.modules", {
            "google": mods["google"],
            "google.genai": mods["google.genai"],
            "google.genai.types": mods["google.genai.types"],
        }):
            client = LLMClient(provider="google", api_key="goog-key")

        assert client.provider == "google"
        assert client.model == "gemini-2.5-flash"
        mods["client_cls"].assert_called_once_with(api_key="goog-key")

    def test_deepseek_init(self, mock_openai_module):
        """Deepseek should use the OpenAI SDK with a custom base_url."""
        mock_mod, mock_cls = mock_openai_module
        with patch.dict("sys.modules", {"openai": mock_mod}):
            client = LLMClient(provider="deepseek", api_key="ds-key")

        assert client.provider == "deepseek"
        assert client.model == "deepseek-chat"
        mock_cls.assert_called_once_with(
            api_key="ds-key", base_url="https://api.deepseek.com/v1"
        )

    def test_env_var_api_key(self, mock_openai_module):
        """Should pick up the API key from the corresponding environment variable."""
        mock_mod, mock_cls = mock_openai_module
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}), \
             patch.dict("sys.modules", {"openai": mock_mod}):
            client = LLMClient(provider="openai")

        assert client.api_key == "env-key"

    def test_custom_model_overrides_default(self, mock_openai_module):
        """An explicit model= should override the provider's default model."""
        mock_mod, _ = mock_openai_module
        with patch.dict("sys.modules", {"openai": mock_mod}):
            client = LLMClient(provider="openai", api_key="k", model="gpt-4-turbo")

        assert client.model == "gpt-4-turbo"

    def test_config_kwargs_pass_through(self, mock_openai_module):
        """Extra kwargs (max_tokens, temperature, …) should land in client.config."""
        mock_mod, _ = mock_openai_module
        with patch.dict("sys.modules", {"openai": mock_mod}):
            client = LLMClient(
                provider="openai", api_key="k",
                max_tokens=1024, temperature=0.2, timeout=30,
                max_retries=5, rate_limit_rpm=10,
            )

        assert client.config.max_tokens == 1024
        assert client.config.temperature == 0.2
        assert client.config.timeout == 30
        assert client.config.max_retries == 5
        assert client.config.rate_limit_rpm == 10

    def test_openai_import_error(self):
        """Should raise ImportError with a helpful message when openai is not installed."""
        # Ensure openai is NOT in sys.modules and importing it will fail
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai package required"):
                LLMClient(provider="openai", api_key="k")

    def test_anthropic_import_error(self):
        """Should raise ImportError with a helpful message when anthropic is not installed."""
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic package required"):
                LLMClient(provider="anthropic", api_key="k")


# ======================================================================
# 5.  LLMClient MockGenAI fallback
# ======================================================================

class TestMockGenAIFallback:
    """When google.genai cannot be imported the client should silently
    fall back to the built-in MockGenAI stub."""

    def test_uses_mock_genai_when_import_fails(self):
        """LLMClient(provider='google') should NOT raise when google.genai is missing."""
        # Setting the module entry to None makes `import google.genai` raise ImportError
        with patch.dict("sys.modules", {"google": None, "google.genai": None}):
            client = LLMClient(provider="google", api_key="g-key")

        # The internal client should be an instance of the inline MockGenAI class
        assert client._client is not None
        assert type(client._client).__name__ == "MockGenAI"


# ======================================================================
# 6.  generate() routes to the correct provider method
# ======================================================================

class TestGenerateRouting:
    """Tests that generate() dispatches to the right _generate_* method."""

    def _patch_rate_limiter(self, client):
        """Neuter the rate limiter so it doesn't interfere with tests."""
        client.rate_limiter = MagicMock()

    def test_openai_routing(self, openai_client):
        """generate() on an openai client should call _generate_openai."""
        self._patch_rate_limiter(openai_client)
        with patch.object(openai_client, "_generate_openai", return_value="hi") as m:
            result = openai_client.generate("prompt")
        assert result == "hi"
        m.assert_called_once()

    def test_anthropic_routing(self, anthropic_client):
        """generate() on an anthropic client should call _generate_anthropic."""
        self._patch_rate_limiter(anthropic_client)
        with patch.object(anthropic_client, "_generate_anthropic", return_value="hello") as m:
            result = anthropic_client.generate("prompt")
        assert result == "hello"
        m.assert_called_once()

    def test_google_routing(self, google_client):
        """generate() on a google client should call _generate_google."""
        client, mods = google_client
        self._patch_rate_limiter(client)
        with patch.object(client, "_generate_google", return_value="hey") as m:
            result = client.generate("prompt")
        assert result == "hey"
        m.assert_called_once()

    def test_deepseek_routing(self, deepseek_client):
        """Deepseek should reuse _generate_openai (same underlying SDK)."""
        self._patch_rate_limiter(deepseek_client)
        with patch.object(deepseek_client, "_generate_openai", return_value="ds") as m:
            result = deepseek_client.generate("prompt")
        assert result == "ds"
        m.assert_called_once()


# ======================================================================
# 7.  _generate_openai internals
# ======================================================================

class TestGenerateOpenAI:
    """Tests for the OpenAI code-path of generate()."""

    def test_builds_messages_without_system(self, openai_client):
        """When no system_prompt is given, messages should contain only the user msg."""
        openai_client.rate_limiter = MagicMock()

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "response_text"
        openai_client._client.chat.completions.create.return_value = mock_response

        result = openai_client.generate("hello")

        create_call = openai_client._client.chat.completions.create
        create_call.assert_called_once()
        msgs = create_call.call_args[1].get("messages") or create_call.call_args[0][0]
        # If kwargs-style, messages is in kwargs
        if "messages" in create_call.call_args.kwargs:
            msgs = create_call.call_args.kwargs["messages"]
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert result == "response_text"

    def test_builds_messages_with_system(self, openai_client):
        """When system_prompt is provided it should prepend a system message."""
        openai_client.rate_limiter = MagicMock()

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "resp"
        openai_client._client.chat.completions.create.return_value = mock_response

        openai_client.generate("user msg", system_prompt="be helpful")

        msgs = openai_client._client.chat.completions.create.call_args.kwargs["messages"]
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "be helpful"}
        assert msgs[1] == {"role": "user", "content": "user msg"}


# ======================================================================
# 8.  _generate_anthropic internals
# ======================================================================

class TestGenerateAnthropic:
    """Tests for the Anthropic code-path of generate()."""

    def test_calls_messages_create(self, anthropic_client):
        """Should call self._client.messages.create with the correct args."""
        anthropic_client.rate_limiter = MagicMock()

        mock_response = MagicMock()
        mock_response.content[0].text = "claude says"
        anthropic_client._client.messages.create.return_value = mock_response

        result = anthropic_client.generate("ask claude", system_prompt="sys")

        anthropic_client._client.messages.create.assert_called_once()
        kwargs = anthropic_client._client.messages.create.call_args.kwargs
        assert kwargs["system"] == "sys"
        assert kwargs["messages"] == [{"role": "user", "content": "ask claude"}]
        assert result == "claude says"

    def test_default_empty_system_prompt(self, anthropic_client):
        """When no system_prompt is given, system should be an empty string."""
        anthropic_client.rate_limiter = MagicMock()

        mock_response = MagicMock()
        mock_response.content[0].text = "ok"
        anthropic_client._client.messages.create.return_value = mock_response

        anthropic_client.generate("question")

        kwargs = anthropic_client._client.messages.create.call_args.kwargs
        assert kwargs["system"] == ""


# ======================================================================
# 9.  _generate_google internals
# ======================================================================

class TestGenerateGoogle:
    """Tests for the Google Gemini code-path of generate()."""

    def test_calls_models_generate_content(self, google_client):
        """Should call client.models.generate_content with the correct params."""
        client, mods = google_client
        client.rate_limiter = MagicMock()

        mock_response = MagicMock()
        mock_response.text = "gemini says"
        client._client.models.generate_content.return_value = mock_response

        # Ensure google.genai.types is importable inside _generate_google
        with patch.dict("sys.modules", {
            "google": mods["google"],
            "google.genai": mods["google.genai"],
            "google.genai.types": mods["google.genai.types"],
        }):
            result = client.generate("test prompt")

        assert result == "gemini says"
        client._client.models.generate_content.assert_called_once()

    def test_prepends_system_prompt(self, google_client):
        """Google path should concatenate system_prompt + prompt into a single string."""
        client, mods = google_client
        client.rate_limiter = MagicMock()

        mock_response = MagicMock()
        mock_response.text = "ok"
        client._client.models.generate_content.return_value = mock_response

        with patch.dict("sys.modules", {
            "google": mods["google"],
            "google.genai": mods["google.genai"],
            "google.genai.types": mods["google.genai.types"],
        }):
            client.generate("question", system_prompt="be brief")

        call_kwargs = client._client.models.generate_content.call_args.kwargs
        contents = call_kwargs.get("contents")
        assert "be brief" in contents
        assert "question" in contents


# ======================================================================
# 10.  generate_stream() routing
# ======================================================================

class TestGenerateStreamRouting:
    """Tests for generate_stream() dispatch and iteration."""

    def test_openai_stream(self, openai_client):
        """generate_stream on openai should yield from _stream_openai."""
        openai_client.rate_limiter = MagicMock()
        with patch.object(openai_client, "_stream_openai", return_value=iter(["a", "b"])):
            chunks = list(openai_client.generate_stream("prompt"))
        assert chunks == ["a", "b"]

    def test_deepseek_stream(self, deepseek_client):
        """generate_stream on deepseek should yield from _stream_openai."""
        deepseek_client.rate_limiter = MagicMock()
        with patch.object(deepseek_client, "_stream_openai", return_value=iter(["x"])):
            chunks = list(deepseek_client.generate_stream("prompt"))
        assert chunks == ["x"]

    def test_anthropic_stream(self, anthropic_client):
        """generate_stream on anthropic should yield from _stream_anthropic."""
        anthropic_client.rate_limiter = MagicMock()
        with patch.object(anthropic_client, "_stream_anthropic", return_value=iter(["c"])):
            chunks = list(anthropic_client.generate_stream("prompt"))
        assert chunks == ["c"]

    def test_google_stream_falls_back_to_generate(self, google_client):
        """Google provider streams by yielding a single _generate_google result."""
        client, mods = google_client
        client.rate_limiter = MagicMock()
        with patch.object(client, "_generate_google", return_value="full") as m, \
             patch.dict("sys.modules", {
                 "google": mods["google"],
                 "google.genai": mods["google.genai"],
                 "google.genai.types": mods["google.genai.types"],
             }):
            chunks = list(client.generate_stream("prompt"))
        assert chunks == ["full"]


# ======================================================================
# 11.  MultiProviderLLMClient
# ======================================================================

class TestMultiProviderLLMClient:
    """Tests for the multi-provider fallback wrapper."""

    def _make_multi(self, mock_openai_module, primary="openai", fallbacks=None):
        """Helper to build a MultiProviderLLMClient with mocked providers."""
        mock_mod, _ = mock_openai_module
        with patch.dict("sys.modules", {"openai": mock_mod}):
            mp = MultiProviderLLMClient(
                primary=primary,
                fallbacks=fallbacks or [],
                api_key="test-key",
            )
        return mp

    def test_primary_success(self, mock_openai_module):
        """Should use the primary provider when it succeeds."""
        mp = self._make_multi(mock_openai_module)

        with patch.object(
            mp.clients["openai"], "generate", return_value="primary ok"
        ):
            result = mp.generate("prompt")

        assert result == "primary ok"

    def test_fallback_on_primary_failure(self, mock_openai_module, mock_anthropic_module):
        """Should try the fallback provider when primary raises."""
        mock_oai_mod, _ = mock_openai_module
        mock_ant_mod, _ = mock_anthropic_module

        with patch.dict("sys.modules", {
            "openai": mock_oai_mod,
            "anthropic": mock_ant_mod,
        }):
            mp = MultiProviderLLMClient(
                primary="openai",
                fallbacks=["anthropic"],
                api_key="test-key",
            )

        # Primary fails, fallback succeeds
        mp.clients["openai"].generate = MagicMock(side_effect=RuntimeError("down"))
        mp.clients["anthropic"] = MagicMock()
        mp.clients["anthropic"].generate.return_value = "fallback ok"

        result = mp.generate("prompt")
        assert result == "fallback ok"

    def test_all_providers_fail(self, mock_openai_module):
        """Should raise RuntimeError summarising errors when every provider fails."""
        mp = self._make_multi(mock_openai_module, fallbacks=[])

        mp.clients["openai"].generate = MagicMock(side_effect=RuntimeError("err"))

        with pytest.raises(RuntimeError, match="All providers failed"):
            mp.generate("prompt")

    def test_generate_stream_primary_success(self, mock_openai_module):
        """generate_stream should yield from the primary when it works."""
        mp = self._make_multi(mock_openai_module)

        mp.clients["openai"].generate_stream = MagicMock(return_value=iter(["a", "b"]))

        chunks = list(mp.generate_stream("prompt"))
        assert chunks == ["a", "b"]

    def test_generate_stream_fallback(self, mock_openai_module, mock_anthropic_module):
        """generate_stream should fall back when primary stream raises."""
        mock_oai_mod, _ = mock_openai_module
        mock_ant_mod, _ = mock_anthropic_module

        with patch.dict("sys.modules", {
            "openai": mock_oai_mod,
            "anthropic": mock_ant_mod,
        }):
            mp = MultiProviderLLMClient(
                primary="openai",
                fallbacks=["anthropic"],
                api_key="test-key",
            )

        def failing_stream(*a, **kw):
            raise ConnectionError("stream fail")

        mp.clients["openai"].generate_stream = failing_stream
        mp.clients["anthropic"] = MagicMock()
        mp.clients["anthropic"].generate_stream.return_value = iter(["fallback_chunk"])

        chunks = list(mp.generate_stream("prompt"))
        assert chunks == ["fallback_chunk"]

    def test_generate_stream_all_fail(self, mock_openai_module):
        """generate_stream should raise RuntimeError when all providers fail."""
        mp = self._make_multi(mock_openai_module, fallbacks=[])

        def failing_stream(*a, **kw):
            raise ConnectionError("nope")

        mp.clients["openai"].generate_stream = failing_stream

        with pytest.raises(RuntimeError, match="All providers failed"):
            list(mp.generate_stream("prompt"))

    def test_lazy_client_creation(self, mock_openai_module, mock_anthropic_module):
        """Fallback clients should only be created when actually needed."""
        mock_oai_mod, _ = mock_openai_module
        mock_ant_mod, _ = mock_anthropic_module

        with patch.dict("sys.modules", {
            "openai": mock_oai_mod,
            "anthropic": mock_ant_mod,
        }):
            mp = MultiProviderLLMClient(
                primary="openai",
                fallbacks=["anthropic"],
                api_key="test-key",
            )

        # Only primary should be initialised at construction time
        assert "openai" in mp.clients
        assert "anthropic" not in mp.clients


# ======================================================================
# 12.  get_llm_client convenience function
# ======================================================================

class TestGetLLMClient:
    """Tests for the module-level get_llm_client helper."""

    def test_returns_llm_client(self, mock_openai_module):
        """get_llm_client should return an LLMClient instance."""
        mock_mod, _ = mock_openai_module
        with patch.dict("sys.modules", {"openai": mock_mod}):
            client = get_llm_client(provider="openai", api_key="k")
        assert isinstance(client, LLMClient)
        assert client.provider == "openai"


# ======================================================================
# 13.  Temperature / max_tokens override in generate()
# ======================================================================

class TestParameterOverrides:
    """Verifies that generate() correctly forwards overridden parameters."""

    def test_max_tokens_override(self, openai_client):
        """Explicit max_tokens in generate() should override config default."""
        openai_client.rate_limiter = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "ok"
        openai_client._client.chat.completions.create.return_value = mock_resp

        openai_client.generate("prompt", max_tokens=512)

        kwargs = openai_client._client.chat.completions.create.call_args.kwargs
        assert kwargs["max_tokens"] == 512

    def test_temperature_override(self, openai_client):
        """Explicit temperature in generate() should override config default."""
        openai_client.rate_limiter = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "ok"
        openai_client._client.chat.completions.create.return_value = mock_resp

        openai_client.generate("prompt", temperature=0.0)

        kwargs = openai_client._client.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.0

    def test_temperature_zero_is_not_none(self, openai_client):
        """temperature=0 (falsy but not None) should be used, not replaced by default."""
        openai_client.rate_limiter = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "ok"
        openai_client._client.chat.completions.create.return_value = mock_resp

        openai_client.generate("prompt", temperature=0)

        kwargs = openai_client._client.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0


# ======================================================================
# 14.  Provider metadata
# ======================================================================

class TestProviderMetadata:
    """Verify the PROVIDERS class-level dict is sane."""

    def test_all_known_providers_present(self):
        """The PROVIDERS dict should contain exactly the four supported providers."""
        assert set(LLMClient.PROVIDERS.keys()) == {
            "openai", "anthropic", "google", "deepseek"
        }

    @pytest.mark.parametrize("provider", ["openai", "anthropic", "google", "deepseek"])
    def test_provider_has_required_keys(self, provider):
        """Each provider entry should have models, default_model, and env_key."""
        info = LLMClient.PROVIDERS[provider]
        assert "models" in info
        assert "default_model" in info
        assert "env_key" in info
        assert info["default_model"] in info["models"]
