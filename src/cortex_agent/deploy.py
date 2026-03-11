"""Deploy semantic views and procedures from repo config files.

Shared by ``deploy_agent.py`` and ``create_workspace.py`` so the same
logic runs for both production deploys and dev workspace creation.
"""

from __future__ import annotations

from pathlib import Path

from cortex_agent.snowflake.rest_client import CortexAgentClient


def deploy_semantic_views(
    client: CortexAgentClient,
    sv_dir: Path,
    target_db: str,
    target_schema: str,
) -> None:
    """Create semantic views from YAML files using SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML."""
    if not sv_dir.is_dir():
        return

    yaml_files = sorted(sv_dir.glob("*.yaml"))
    if not yaml_files:
        return

    for yaml_path in yaml_files:
        name = yaml_path.stem
        yaml_content = yaml_path.read_text(encoding="utf-8")

        fq_schema = f"{target_db}.{target_schema}"
        stmt = (
            f"CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML("
            f"'{fq_schema}', $${yaml_content}$$)"
        )

        print(f"  Deploying semantic view '{name}' to {fq_schema} ...")
        try:
            client.execute_sql(stmt, database=target_db, schema=target_schema)
            print(f"    -> {fq_schema}.{name}")
        except RuntimeError as exc:
            print(f"    Warning: deploy failed ({exc})")


def deploy_procedures(
    client: CortexAgentClient,
    proc_dir: Path,
    canonical_db: str,
    canonical_schema: str,
    target_db: str,
    target_schema: str,
) -> None:
    """Execute procedure DDL files, fully-qualifying the procedure name."""
    if not proc_dir.is_dir():
        return

    sql_files = sorted(proc_dir.glob("*.sql"))
    if not sql_files:
        return

    src = f"{canonical_db}.{canonical_schema}".upper()
    tgt = f"{target_db}.{target_schema}".upper()

    for sql_path in sql_files:
        name = sql_path.stem
        ddl = sql_path.read_text(encoding="utf-8")

        if src != tgt:
            ddl = ddl.replace(src, tgt)

        # GET_DDL returns: CREATE OR REPLACE PROCEDURE "NAME"(...)
        # The SQL API needs the name fully-qualified. The file stem matches
        # the procedure name, so one simple replace is enough.
        ddl = ddl.replace(
            f'PROCEDURE "{name}"',
            f'PROCEDURE {target_db}.{target_schema}."{name}"',
            1,
        )

        print(f"  Deploying procedure '{name}' to {target_db}.{target_schema} ...")
        try:
            client.execute_sql(ddl, database=target_db, schema=target_schema)
            print(f"    -> {target_db}.{target_schema}.{name}")
        except RuntimeError as exc:
            print(f"    Warning: deploy failed ({exc})")


def deploy_dependencies(
    client: CortexAgentClient,
    configs_dir: Path,
    target_db: str,
    target_schema: str,
    canonical_db: str,
    canonical_schema: str,
) -> None:
    """Deploy all semantic views and procedures from the configs directory.

    Semantic views are created via SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML.
    Procedures are created by executing the DDL with schema rewriting.
    """
    sv_dir = configs_dir / "semantic_views"
    proc_dir = configs_dir / "procedures"

    deploy_semantic_views(client, sv_dir, target_db, target_schema)
    deploy_procedures(
        client,
        proc_dir,
        canonical_db,
        canonical_schema,
        target_db,
        target_schema,
    )
