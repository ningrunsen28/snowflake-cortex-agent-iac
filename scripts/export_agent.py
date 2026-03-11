#!/usr/bin/env python3
"""Export a Cortex Agent config from Snowflake to configs/agent_config.yaml.

All flags fall back to environment variables when omitted, so local dev
needs no args while CI pipelines can override everything explicitly.

When --database / --schema point to a non-canonical (e.g. dev) schema,
the exported YAML is automatically normalized: all fully-qualified
references are rewritten back to the canonical database/schema so the
file in git stays environment-agnostic.

Usage:
    # Local dev — uses env vars / .env
    python scripts/export_agent.py

    # Export from a dev schema, normalizing refs back to canonical
    python scripts/export_agent.py --agent MY_AGENT_DEV --database DEV_DB --schema DEV_SCHEMA
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cortex_agent.io.serialize import write_yaml
from cortex_agent.model.agent_config import AgentConfig, normalize, rewrite_references
from cortex_agent.snowflake.rest_client import (
    agent_name_from_env,
    canonical_db_schema_from_env,
    client_from_env,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "agent_config.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Cortex Agent config to YAML.",
    )
    parser.add_argument(
        "--agent",
        help="Agent name in Snowflake (default: CORTEX_AGENT_NAME env var).",
    )
    parser.add_argument(
        "--database",
        help="Source database (default: SNOWFLAKE_DATABASE env var).",
    )
    parser.add_argument(
        "--schema",
        help="Source schema (default: SNOWFLAKE_SCHEMA env var).",
    )
    args = parser.parse_args()

    agent_name = args.agent or agent_name_from_env()
    client = client_from_env(database=args.database, schema=args.schema)

    print(f"Exporting agent '{agent_name}' ...")
    raw = client.describe(agent_name)
    config = AgentConfig.from_describe_response(raw)
    data = normalize(config)

    canonical_db, canonical_schema = canonical_db_schema_from_env()
    source_db = args.database or canonical_db
    source_schema = args.schema or canonical_schema
    data = rewrite_references(
        data, source_db, source_schema, canonical_db, canonical_schema
    )

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(data, CONFIG_PATH)
    print(f"  -> {CONFIG_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
