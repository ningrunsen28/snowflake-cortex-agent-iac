#!/usr/bin/env python3
"""Export a Cortex Agent config, semantic views, and procedures from Snowflake.

Exports:
  - Agent config         -> configs/agent_config.yaml
  - Semantic view YAMLs  -> configs/semantic_views/<NAME>.yaml
  - Procedure DDLs       -> configs/procedures/<NAME>.sql

All flags fall back to environment variables when omitted, so local dev
needs no args while CI pipelines can override everything explicitly.

When --database / --schema point to a non-canonical (e.g. dev) schema,
the exported agent config is automatically normalized: all fully-qualified
references are rewritten back to the canonical database/schema so the
files in git stay environment-agnostic.

Usage:
    python scripts/export_agent.py

    python scripts/export_agent.py --agent MY_AGENT_DEV --database DEV_DB --schema DEV_SCHEMA
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cortex_agent.io.serialize import write_yaml
from cortex_agent.model.agent_config import AgentConfig, normalize, rewrite_references
from cortex_agent.snowflake.rest_client import (
    CortexAgentClient,
    agent_name_from_env,
    canonical_db_schema_from_env,
    client_from_env,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
CONFIG_PATH = CONFIGS_DIR / "agent_config.yaml"
SV_DIR = CONFIGS_DIR / "semantic_views"
PROC_DIR = CONFIGS_DIR / "procedures"


def _export_semantic_views(
    client: CortexAgentClient,
    config: AgentConfig,
    source_db: str,
    source_schema: str,
) -> None:
    """Export each semantic view referenced in tool_resources as a YAML file."""
    if not config.tool_resources:
        return

    SV_DIR.mkdir(parents=True, exist_ok=True)

    for tool_name, resource in config.tool_resources.items():
        if not resource.semantic_view:
            continue

        fq_name = resource.semantic_view
        obj_name = fq_name.rsplit(".", 1)[-1]
        out_path = SV_DIR / f"{obj_name}.yaml"

        print(f"  Exporting semantic view '{obj_name}' ...")
        try:
            yaml_str = client.query_scalar(
                f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{fq_name}')",
                database=source_db,
                schema=source_schema,
            )
            out_path.write_text(yaml_str, encoding="utf-8")
            print(f"    -> {out_path}")
        except RuntimeError as exc:
            print(f"    Warning: export failed ({exc})")


def _export_procedures(
    client: CortexAgentClient,
    config: AgentConfig,
    source_db: str,
    source_schema: str,
) -> None:
    """Export each procedure referenced in tool_resources as a SQL file."""
    if not config.tool_resources:
        return

    PROC_DIR.mkdir(parents=True, exist_ok=True)

    for tool_name, resource in config.tool_resources.items():
        if not resource.identifier:
            continue

        resource_dict = resource.model_dump(exclude_none=True)
        fq_name = resource.identifier
        obj_name = fq_name.rsplit(".", 1)[-1]
        out_path = PROC_DIR / f"{obj_name}.sql"

        name_with_sig = resource_dict.get("name", "")
        if "(" in name_with_sig:
            sig = name_with_sig[name_with_sig.index("(") :]
            get_ddl_ref = f"{fq_name}{sig}"
        else:
            get_ddl_ref = fq_name

        print(f"  Exporting procedure '{obj_name}' ...")
        try:
            ddl = client.query_scalar(
                f"SELECT GET_DDL('PROCEDURE', '{get_ddl_ref}')",
                database=source_db,
                schema=source_schema,
            )
            out_path.write_text(ddl, encoding="utf-8")
            print(f"    -> {out_path}")
        except RuntimeError as exc:
            print(f"    Warning: export failed ({exc})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Cortex Agent config, semantic views, and procedures.",
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

    canonical_db, canonical_schema = canonical_db_schema_from_env()
    source_db = args.database or canonical_db
    source_schema = args.schema or canonical_schema

    agent_name = args.agent or agent_name_from_env()
    client = client_from_env(database=args.database, schema=args.schema)

    # ---- 1. Export agent config --------------------------------------
    print(f"Exporting agent '{agent_name}' ...")
    raw = client.describe(agent_name)
    config = AgentConfig.from_describe_response(raw)
    data = normalize(config)
    data = rewrite_references(
        data, source_db, source_schema, canonical_db, canonical_schema
    )

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(data, CONFIG_PATH)
    print(f"  -> {CONFIG_PATH}")

    # ---- 2. Export semantic views ------------------------------------
    _export_semantic_views(client, config, source_db, source_schema)

    # ---- 3. Export procedures ----------------------------------------
    _export_procedures(client, config, source_db, source_schema)

    print("Done.")


if __name__ == "__main__":
    main()
