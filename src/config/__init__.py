"""Configuration Management System for SEO/GEO Framework.

Expose a single compatible ``get_config()`` entrypoint from the ``src.config``
package even though the repo also contains a sibling ``src/config.py`` module
with the richer SEO/GEO settings model expected by the orchestrator.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Optional

try:
    from src.config.config_validator import ConfigValidator
    from src.config.env_config import ConfigLoader, EnvConfig
    from src.config.secret_manager import SecretManager
except ImportError:
    from .config_validator import ConfigValidator
    from .env_config import ConfigLoader, EnvConfig
    from .secret_manager import SecretManager

__all__ = [
    "ConfigLoader",
    "ConfigValidator",
    "EnvConfig",
    "SecretManager",
    "get_config",
    "get_env_config",
    "set_config",
]

_env_loader = ConfigLoader()
_legacy_module: Optional[ModuleType] = None


def _load_legacy_config_module() -> ModuleType:
    """Load the sibling ``src/config.py`` module under a private module name."""
    global _legacy_module
    if _legacy_module is not None:
        return _legacy_module

    config_path = Path(__file__).resolve().parents[1] / "config.py"
    spec = spec_from_file_location("src._legacy_config_module", config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load legacy config module from {config_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    _legacy_module = module
    return module


def get_env_config() -> EnvConfig:
    """Return the lightweight environment-only config surface."""
    return _env_loader.load()


def get_config():
    """Return the richer SEO/GEO config with env-compatible top-level aliases."""
    legacy = _load_legacy_config_module()
    config = legacy.get_config()
    env_config = get_env_config()

    # Preserve the old env-config convenience surface for callers that expect it.
    config.debug = env_config.debug
    config.log_level = env_config.log_level
    config.api_timeout = env_config.api_timeout
    config.max_retries = env_config.max_retries
    return config


def set_config(config) -> None:
    """Set the underlying shared SEO/GEO config instance."""
    legacy = _load_legacy_config_module()
    legacy.set_config(config)
