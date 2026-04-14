#!/usr/bin/env python3
"""
Run Supabase RPC public.run_inventory_from_hoot(p_date).

Mirrors the old Django "delete then insert from hoot_inventory" flow:
- deletes inventorydata rows for target date + eligible clients
- inserts rows from hoot_inventory for same date + eligible clients

Eligibility is enforced inside the SQL function:
  is_active=true, active_pull=true, scrap_feed=false, inventory_api non-empty

Environment:
  SUPABASE_URL
  HOOT_SUPABASE_SECRET_KEY   Preferred (Secret sb_secret_... or legacy service_role JWT)
  SUPABASE_SERVICE_ROLE_KEY  Used if HOOT_SUPABASE_SECRET_KEY is unset

Optional:
  HOOT_TRANSFER_DATE         YYYY-MM-DD (defaults to today)

Usage:
  python Hootprocess/hoot_inventorydata.py
"""

from __future__ import annotations

import os
import sys
from datetime import date

from postgrest.exceptions import APIError
from supabase import create_client

from supabase_key import (
    is_supabase_publishable_key,
    is_supabase_secret_key,
    resolve_supabase_api_key,
    supabase_jwt_role,
)


def parse_target_date() -> str:
    v = (os.environ.get("HOOT_TRANSFER_DATE") or "").strip()
    if not v:
        return date.today().isoformat()
    date.fromisoformat(v)
    return v


def main() -> None:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key, key_env = resolve_supabase_api_key()
    if not url or not key:
        print(
            "Set SUPABASE_URL and an elevated key: HOOT_SUPABASE_SECRET_KEY (preferred) or "
            "SUPABASE_SERVICE_ROLE_KEY (fallback).",
            file=sys.stderr,
        )
        sys.exit(1)

    if is_supabase_publishable_key(key):
        print(
            f"Wrong key: {key_env} is a publishable key; cannot run backend transfer.",
            file=sys.stderr,
        )
        sys.exit(1)
    role = supabase_jwt_role(key)
    if role == "anon":
        print("Wrong key: anon key cannot run backend transfer.", file=sys.stderr)
        sys.exit(1)
    if is_supabase_secret_key(key):
        print("API key: Supabase secret key (sb_secret_...)")
    elif role == "service_role":
        print("API key: legacy service_role JWT")
    elif role:
        print(f"API key JWT role: {role}")

    target_date = parse_target_date()
    print(f"Run inventory transfer from hoot for date: {target_date}")

    supabase = create_client(url, key)
    try:
        res = supabase.rpc("run_inventory_from_hoot", {"p_date": target_date}).execute()
        payload = res.data
        print(f"Function result: {payload}")
    except APIError as e:
        code = ""
        msg = ""
        if isinstance(getattr(e, "args", None), tuple) and e.args:
            maybe = e.args[0]
            if isinstance(maybe, dict):
                code = str(maybe.get("code") or "")
                msg = str(maybe.get("message") or "")
        if code == "PGRST202":
            print(
                "\nRPC function not found in Supabase schema cache.\n"
                "Apply migration that defines `public.run_inventory_from_hoot` in your Supabase project, "
                "then re-run.\n"
                "If already applied, wait ~30–60s and retry (schema cache refresh).",
                file=sys.stderr,
            )
        else:
            print(f"RPC call failed: {msg or str(e)}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
