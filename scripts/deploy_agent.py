#!/usr/bin/env python3
"""Deploy a Cortex Agent config from YAML to Snowflake.

All flags fall back to environment variables / config defaults when omitted,
so local dev needs minimal args while CI pipelines can override everything.

When --database / --schema differ from the canonical env vars, all
fully-qualified object references in the config (semantic views,
procedures, etc.) are rewritten to the target database/schema
automatically.

Usage:
    # Local dev — uses env defaults, config from configs/agent_config.yaml
    python scripts/deploy_agent.py

    # CI — deploy feature-branch config to a dev schema under a different name
    python scripts/deploy_agent.py \
        --config configs/agent_config.yaml \
        --agent MY_AGENT_DEV \
        --database DEV_DB \
        --schema DEV_SCHEMA \
        --mode orReplace
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cortex_agent.io.serialize import read_yaml
from cortex_agent.model.agent_config import AgentConfig, rewrite_references
from cortex_agent.snowflake.rest_client import (
    canonical_db_schema_from_env,
    client_from_env,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "agent_config.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy Cortex Agent config to Snowflake.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to the YAML config file (default: {DEFAULT_CONFIG.relative_to(PROJECT_ROOT)}).",
    )
    parser.add_argument(
        "--agent",
        help="Override the agent name (default: name field in config YAML).",
    )
    parser.add_argument(
        "--database",
        help="Target database (default: SNOWFLAKE_DATABASE env var).",
    )
    parser.add_argument(
        "--schema",
        help="Target schema (default: SNOWFLAKE_SCHEMA env var).",
    )
    parser.add_argument(
        "--mode",
        default="orReplace",
        choices=["orReplace", "ifNotExists", "errorIfExists"],
        help="Create mode (default: orReplace).",
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading config: {args.config}")
    spec = read_yaml(args.config)

    canonical_db, canonical_schema = canonical_db_schema_from_env()
    target_db = args.database or canonical_db
    target_schema = args.schema or canonical_schema

    spec = rewrite_references(
        spec, canonical_db, canonical_schema, target_db, target_schema
    )
    config = AgentConfig.model_validate(spec)

    if args.agent:
        config.name = args.agent

    body = config.to_create_body()

    client = client_from_env(database=args.database, schema=args.schema)
    print(
        f"Deploying agent '{config.name}' to {target_db}.{target_schema} (mode={args.mode}) ..."
    )
    result = client.create(body, create_mode=args.mode)
    print(f"  -> {result}")
    print("Done.")


if __name__ == "__main__":
    main()
