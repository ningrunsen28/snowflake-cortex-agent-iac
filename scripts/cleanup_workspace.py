#!/usr/bin/env python3
"""Tear down a development workspace created by create_workspace.py.

Drops the dev agent and then the entire DEV_<DEVELOPER> schema
(CASCADE), removing all cloned semantic views and procedures.

Usage:
    python scripts/cleanup_workspace.py --developer runsen

    python scripts/cleanup_workspace.py \
        --developer runsen \
        --database SNOWFLAKE_AI_DEMO
"""

from __future__ import annotations

import argparse

from cortex_agent.snowflake.rest_client import (
    agent_name_from_env,
    canonical_db_schema_from_env,
    client_from_env,
)


def _dev_schema(developer: str) -> str:
    return f"DEV_{developer.upper()}"


def _dev_agent_name(canonical_name: str, developer: str) -> str:
    return f"{canonical_name}_DEV_{developer.upper()}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tear down a dev workspace (agent + schema).",
    )
    parser.add_argument(
        "--developer",
        required=True,
        help="Developer username (maps to DEV_<DEVELOPER> schema).",
    )
    parser.add_argument(
        "--database",
        help="Target database (default: SNOWFLAKE_DATABASE env var).",
    )
    args = parser.parse_args()

    canonical_db, _ = canonical_db_schema_from_env()
    target_db = args.database or canonical_db
    dev_schema = _dev_schema(args.developer)

    client = client_from_env(database=target_db, schema=dev_schema)

    # ---- 1. Drop the dev agent ---------------------------------------
    canonical_agent = agent_name_from_env()
    dev_agent = _dev_agent_name(canonical_agent, args.developer)

    print(f"Dropping agent '{dev_agent}' ...")
    try:
        client.delete(dev_agent, if_exists=True)
        print("  -> deleted")
    except RuntimeError as exc:
        print(f"  Warning: {exc}")

    # ---- 2. Drop the dev schema (cascade) ----------------------------
    print(f"Dropping schema {target_db}.{dev_schema} CASCADE ...")
    try:
        client.execute_sql(
            f"DROP SCHEMA IF EXISTS {target_db}.{dev_schema} CASCADE",
            database=target_db,
        )
        print("  -> dropped")
    except RuntimeError as exc:
        print(f"  Warning: {exc}")

    print("Done.")


if __name__ == "__main__":
    main()
