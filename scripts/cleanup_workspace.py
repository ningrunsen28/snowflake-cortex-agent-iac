#!/usr/bin/env python3
"""Tear down a development workspace created by create_workspace.py.

Drops the dev agent and then the entire dev schema (CASCADE), removing
all cloned semantic views and procedures.

Usage:
    python scripts/cleanup_workspace.py --schema DEV_ADD_SALES_TOOL --agent BIGBANGBEV_DEV_ADD_SALES_TOOL

    python scripts/cleanup_workspace.py \
        --schema DEV_ADD_SALES_TOOL \
        --agent BIGBANGBEV_DEV_ADD_SALES_TOOL \
        --database MY_DATABASE
"""

from __future__ import annotations

import argparse

from cortex_agent.snowflake.rest_client import (
    canonical_db_schema_from_env,
    client_from_env,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tear down a dev workspace (agent + schema).",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Dev schema to drop (e.g. DEV_ADD_SALES_TOOL).",
    )
    parser.add_argument(
        "--agent",
        required=True,
        help="Dev agent name to drop (e.g. BIGBANGBEV_DEV_ADD_SALES_TOOL).",
    )
    parser.add_argument(
        "--database",
        help="Target database (default: SNOWFLAKE_DATABASE env var).",
    )
    args = parser.parse_args()

    canonical_db, _ = canonical_db_schema_from_env()
    target_db = args.database or canonical_db

    client = client_from_env(database=target_db, schema=args.schema)

    # ---- 1. Drop the dev agent ---------------------------------------
    print(f"Dropping agent '{args.agent}' ...")
    try:
        client.delete(args.agent, if_exists=True)
        print("  -> deleted")
    except RuntimeError as exc:
        print(f"  Warning: {exc}")

    # ---- 2. Drop the dev schema (cascade) ----------------------------
    print(f"Dropping schema {target_db}.{args.schema} CASCADE ...")
    try:
        client.execute_sql(
            f"DROP SCHEMA IF EXISTS {target_db}.{args.schema} CASCADE",
            database=target_db,
        )
        print("  -> dropped")
    except RuntimeError as exc:
        print(f"  Warning: {exc}")

    print("Done.")


if __name__ == "__main__":
    main()
