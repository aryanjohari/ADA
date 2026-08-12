"""HUD session auth — mesh enough for Observe; password for Agent/Plan.

Secrets live under ADA_SECRETS_DIR/hud.env (never git), same family as gemini.env.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response
from starlette.responses import JSONResponse

from ada.secrets.load import _parse_dotenv, secrets_dir

ENV_SESSION_SECRET = "ADA_HUD_SESSION_SECRET"
ENV_PASSWORD = "ADA_HUD_PASSWORD"
ENV_COOKIE_SECURE = "ADA_HUD_COOKIE_SECURE"
HUD_ENV_FILENAME = "hud.env"
COOKIE_NAME = "ada_hud_session"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


class HudAuthError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class HudSecrets:
    session_secret: str
    password: str


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def cookie_secure() -> bool:
    """Secure cookie when behind HTTPS Serve (default true)."""
    return _env_truthy(ENV_COOKIE_SECURE, default=True)


def load_hud_secrets() -> HudSecrets:
    """Load session secret + password from env or hud.env. Fail closed if missing."""
    env_secret = os.environ.get(ENV_SESSION_SECRET, "").strip()
    env_password = os.environ.get(ENV_PASSWORD, "").strip()
    file_vals: dict[str, str] = {}
    path = secrets_dir() / HUD_ENV_FILENAME
    if path.is_file():
        try:
            file_vals = _parse_dotenv(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise HudAuthError(f"cannot read secrets file at {path}") from exc

    secret = env_secret or (file_vals.get(ENV_SESSION_SECRET) or "").strip()
    password = env_password or (file_vals.get(ENV_PASSWORD) or "").strip()
    if not secret or not password:
        raise HudAuthError(
            f"{ENV_SESSION_SECRET} / {ENV_PASSWORD} not set "
            f"(env or {path})"
        )
    return HudSecrets(session_secret=secret, password=password)


def _sign(secret: str, payload: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def mint_session_token(secret: str, *, now: float | None = None) -> str:
    ts = int(now if now is not None else time.time())
    nonce = secrets.token_hex(8)
    payload = f"{ts}:{nonce}"
    return f"{payload}.{_sign(secret, payload)}"


def verify_session_token(
    secret: str,
    token: str | None,
    *,
    now: float | None = None,
    max_age: int = TOKEN_MAX_AGE_SECONDS,
) -> bool:
    if not token or "." not in token:
        return False
    payload, _, sig = token.rpartition(".")
    if not payload or not sig:
        return False
    expected = _sign(secret, payload)
    if not hmac.compare_digest(expected, sig):
        return False
    try:
        ts_s, _, _nonce = payload.partition(":")
        ts = int(ts_s)
    except ValueError:
        return False
    current = now if now is not None else time.time()
    if current - ts > max_age or ts > current + 60:
        return False
    return True


def passwords_match(expected: str, provided: str) -> bool:
    a = hashlib.sha256(expected.encode("utf-8")).digest()
    b = hashlib.sha256(provided.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def session_authenticated(request: Request) -> bool:
    """True when valid session cookie present and secrets loadable."""
    try:
        secrets_cfg = load_hud_secrets()
    except HudAuthError:
        return False
    token = request.cookies.get(COOKIE_NAME)
    return verify_session_token(secrets_cfg.session_secret, token)


def auth_label(request: Request) -> str:
    return "session" if session_authenticated(request) else "mesh"


def require_agent_session(request: Request, mode: str) -> JSONResponse | None:
    """Return 401 JSONResponse if mode needs session and cookie missing."""
    mode_l = (mode or "observe").lower().strip()
    if mode_l == "observe":
        return None
    if session_authenticated(request):
        return None
    return JSONResponse(
        status_code=401,
        content={
            "error": "session_required",
            "message": f"mode={mode_l} requires HUD session login (auth.session)",
            "auth": "mesh",
        },
    )


def set_session_cookie(response: Response, secret: str) -> None:
    token = mint_session_token(secret)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        max_age=TOKEN_MAX_AGE_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def tailscale_user(request: Request) -> str | None:
    """Soft display of Serve-injected identity header (not Agent authority)."""
    raw = request.headers.get("tailscale-user-login") or request.headers.get(
        "Tailscale-User-Login"
    )
    if raw:
        return raw.strip() or None
    return None


def mode_payload(request: Request, *, mode: str, last_denials: list[Any]) -> dict[str, Any]:
    return {
        "mode": mode,
        "auth": auth_label(request),
        "last_denials": list(last_denials)[-10:],
        "tailscale_user": tailscale_user(request),
        "agent_armed": session_authenticated(request),
    }
