"""Shared Supabase API key resolution for Hootprocess scripts."""

from __future__ import annotations

import base64
import json
import os
from typing import Optional, Tuple


def supabase_jwt_role(api_key: str) -> Optional[str]:
    """Read JWT `role` claim (anon vs service_role). No crypto verify — local hint only."""
    try:
        parts = api_key.strip().split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        pad = "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64 + pad)
        payload = json.loads(raw.decode("utf-8"))
        return payload.get("role")
    except Exception:
        return None


def is_supabase_secret_key(api_key: str) -> bool:
    """New platform secret key (elevated; bypasses RLS) — not a JWT."""
    return api_key.strip().startswith("sb_secret_")


def is_supabase_publishable_key(api_key: str) -> bool:
    """Low-privilege browser key — wrong for server jobs."""
    return api_key.strip().startswith("sb_publishable_")


def resolve_supabase_api_key() -> Tuple[str, str]:
    """
    Returns (key, env_var_name) for Supabase client.
    Prefer HOOT_SUPABASE_SECRET_KEY so Hoot jobs do not depend on SUPABASE_SERVICE_ROLE_KEY used elsewhere.
    """
    hoot = (os.environ.get("HOOT_SUPABASE_SECRET_KEY") or "").strip()
    if hoot:
        return hoot, "HOOT_SUPABASE_SECRET_KEY"
    legacy = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return legacy, "SUPABASE_SERVICE_ROLE_KEY"
