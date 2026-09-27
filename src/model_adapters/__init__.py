"""
Model adapters for Matibhrom.

Adapter modules for external providers (litellm, vllm, hf) pull in heavy
optional dependencies (litellm, torch, vllm, transformers). Those are lazily
imported only when the corresponding adapter is actually requested, so that
code paths using only the `dummy` adapter (tests, CI, dry runs) don't require
every optional dependency to be installed.
"""

from importlib import import_module

from .base import ModelAdapter, GenerationResult
from .dummy import DummyAdapter

__all__ = [
    "ModelAdapter",
    "GenerationResult",
    "DummyAdapter",
    "LiteLLMAdapter",
    "VLLMAdapter",
    "HFAdapter",
    "get_adapter_class",
]

# Adapter registry for dynamic loading: adapter name -> (module path, class name)
_ADAPTER_MODULES = {
    "dummy": (None, None),  # already imported eagerly above
    "litellm": (".litellm_adapter", "LiteLLMAdapter"),
    "vllm": (".vllm_adapter", "VLLMAdapter"),
    "hf": (".hf_adapter", "HFAdapter"),
}

_ADAPTER_CACHE: dict[str, type] = {"dummy": DummyAdapter}


def get_adapter_class(adapter_name: str):
    """Get adapter class by name, importing its module lazily."""
    if adapter_name in _ADAPTER_CACHE:
        return _ADAPTER_CACHE[adapter_name]

    if adapter_name not in _ADAPTER_MODULES:
        raise ValueError(
            f"Unknown adapter: {adapter_name}. Available: {list(_ADAPTER_MODULES.keys())}"
        )

    module_path, class_name = _ADAPTER_MODULES[adapter_name]
    try:
        module = import_module(module_path, package=__name__)
    except ImportError as exc:
        raise ImportError(
            f"Adapter '{adapter_name}' requires optional dependencies that are not "
            f"installed ({exc}). Install them (see requirements-*.txt) to use this adapter."
        ) from exc

    adapter_cls = getattr(module, class_name)
    _ADAPTER_CACHE[adapter_name] = adapter_cls
    return adapter_cls


def __getattr__(name: str):
    # Support `from src.model_adapters import LiteLLMAdapter` etc. lazily.
    lazy_names = {"LiteLLMAdapter": "litellm", "VLLMAdapter": "vllm", "HFAdapter": "hf"}
    if name in lazy_names:
        return get_adapter_class(lazy_names[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
