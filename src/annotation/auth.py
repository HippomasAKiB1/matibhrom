"""
Token auth for the annotation UI (README §14.4, P1 fix).

- Auth is required by default (`auth.enabled: true` in configs/annotation.yaml).
- Tokens live in configs/annotation_tokens.json (gitignored), mapping
  token -> annotator_id.
- If auth is disabled, the caller (src/annotation/app.py) MUST refuse to bind
  to a non-localhost address — enforced here via `assert_safe_to_disable_auth`
  so that check lives in one place rather than being reimplemented per entry
  point.
"""

import json
from pathlib import Path


class AuthError(Exception):
    """Raised when a token is missing, invalid, or auth config is unsafe."""


def load_tokens(tokens_path: str | Path = "configs/annotation_tokens.json") -> dict[str, str]:
    """Load token -> annotator_id mapping. Returns {} if the file doesn't
    exist yet (e.g. a fresh checkout before tokens have been provisioned)."""
    path = Path(tokens_path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AuthError(f"{tokens_path} must be a JSON object of token -> annotator_id")
    return data


def authenticate(
    token: str | None,
    auth_config: dict,
    tokens_path: str | Path = "configs/annotation_tokens.json",
) -> str:
    """Validate `token` against configs/annotation_tokens.json and return the
    resolved annotator_id. Raises AuthError on any failure.

    `auth_config` is the `auth:` block from configs/annotation.yaml, e.g.
    {"enabled": True, "provider": "token"}.
    """
    if not auth_config.get("enabled", True):
        raise AuthError(
            "Auth is disabled in configs/annotation.yaml (auth.enabled: false). "
            "Per README §14.4, the UI must refuse to bind to a non-localhost "
            "address in this mode — see assert_safe_to_disable_auth()."
        )

    provider = auth_config.get("provider", "token")
    if provider != "token":
        raise AuthError(f"Unsupported auth provider: {provider!r} (only 'token' is implemented)")

    if not token:
        raise AuthError("No token provided.")

    tokens = load_tokens(tokens_path)
    if not tokens:
        raise AuthError(
            f"No tokens provisioned in {tokens_path}. Create it (gitignored) as "
            f'{{"<token>": "<annotator_id>"}} before annotators can log in.'
        )

    annotator_id = tokens.get(token)
    if annotator_id is None:
        raise AuthError("Invalid token.")

    return annotator_id


def assert_safe_to_disable_auth(bind_address: str, auth_config: dict) -> None:
    """Per README §14.4: if auth.enabled is false, refuse to bind to
    anything other than localhost. Call this before starting the server."""
    if auth_config.get("enabled", True):
        return  # auth is on; no restriction needed

    localhost_hosts = {"127.0.0.1", "localhost", "::1"}
    host = bind_address.split(":")[0]
    if host not in localhost_hosts:
        raise AuthError(
            f"Refusing to bind the annotation UI to {bind_address!r} with auth "
            f"disabled — this would expose it on the network with no auth layer. "
            f"Either set auth.enabled: true in configs/annotation.yaml, or bind "
            f"to localhost only."
        )
