#!/usr/bin/env python3
"""Create a development workspace for Cortex Agent development.

Creates a dev schema (DEV_<DEVELOPER>) in the target database, deploys
semantic views and procedures from the repo config files, and deploys
the agent config with references rewritten to the dev schema.

All objects are created from the repo files -- no Snowflake-to-Snowflake
cloning is needed.

Usage:
    python scripts/create_workspace.py --developer runsen

    python scripts/create_workspace.py \
        --developer runsen \
        --database SNOWFLAKE_AI_DEMO
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cortex_agent.deploy import deploy_dependencies
from cortex_agent.io.serialize import read_yaml
from cortex_agent.model.agent_config import AgentConfig, rewrite_references
from cortex_agent.snowflake.rest_client import (
    agent_name_from_env,
    canonical_db_schema_from_env,
    client_from_env,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
DEFAULT_CONFIG = CONFIGS_DIR / "agent_config.yaml"


def _dev_schema(developer: str) -> str:
    return f"DEV_{developer.upper()}"


def _dev_agent_name(canonical_name: str, developer: str) -> str:
    return f"{canonical_name}_DEV_{developer.upper()}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a dev workspace (schema + semantic views + procedures + agent).",
    )
    parser.add_argument(
        "--developer",
        required=True,
        help="Developer username (becomes DEV_<DEVELOPER> schema).",
    )
    parser.add_argument(
        "--database",
        help="Target database (default: SNOWFLAKE_DATABASE env var).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Agent config YAML to deploy into the workspace.",
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Error: config not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    canonical_db, canonical_schema = canonical_db_schema_from_env()
    target_db = args.database or canonical_db
    dev_schema = _dev_schema(args.developer)

    client = client_from_env(database=target_db, schema=dev_schema)

    # ---- 1. Create dev schema ----------------------------------------
    print(f"Creating schema {target_db}.{dev_schema} ...")
    client.execute_sql(
        f"CREATE SCHEMA IF NOT EXISTS {target_db}.{dev_schema}",
        database=target_db,
    )

    # ---- 2. Deploy dependencies from repo files ----------------------
    print("Deploying dependencies ...")
    deploy_dependencies(
        client,
        CONFIGS_DIR,
        target_db,
        dev_schema,
        canonical_db,
        canonical_schema,
    )

    # ---- 3. Deploy agent with rewritten references -------------------
    spec = read_yaml(args.config)
    data = rewrite_references(
        spec,
        canonical_db,
        canonical_schema,
        target_db,
        dev_schema,
    )
    dev_config = AgentConfig.model_validate(data)

    canonical_agent = agent_name_from_env()
    dev_config.name = _dev_agent_name(canonical_agent, args.developer)

    body = dev_config.to_create_body()
    print(f"Deploying dev agent '{dev_config.name}' ...")
    result = client.create(body, create_mode="orReplace")
    print(f"  -> {result}")

    print(f"\nWorkspace ready:  {target_db}.{dev_schema}")
    print(f"Dev agent:        {dev_config.name}")
    print("Done.")


if __name__ == "__main__":
    main()
