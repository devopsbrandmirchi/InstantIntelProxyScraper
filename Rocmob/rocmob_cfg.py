# rocmob_cfg.py
import os
from functools import lru_cache
from pathlib import Path

from supabase import Client, create_client

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "For local runs, copy .env.example to .env and fill in values. "
            "For GitHub Actions, add repository secrets SUPABASE_URL and SUPABASE_KEY "
            "(or set SUPABASE_SERVICE_ROLE_KEY instead of SUPABASE_KEY)."
        )
    return str(value).strip()


def _supabase_key() -> str:
    for name in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY"):
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise RuntimeError(
        "Missing SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY. "
        "Use the Supabase service_role key (not the anon key) for server-side upserts."
    )


@lru_cache(maxsize=1)
def _client() -> Client:
    return create_client(_require_env("SUPABASE_URL"), _supabase_key())


class _SupabaseLazy:
    """Defer create_client until first use so `scrapy list` works without credentials."""

    def __getattr__(self, name: str):
        return getattr(_client(), name)


supabase: Client = _SupabaseLazy()  # type: ignore[assignment]
