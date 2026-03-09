#!/usr/bin/env python3
"""Export a Cortex Agent config from Snowflake to a local YAML file.

Usage:
    python scripts/export_agent.py --agent MY_AGENT
    python scripts/export_agent.py --agent MY_AGENT --out configs/agents/my_agent.yaml
    python scripts/export_agent.py --all
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cortex_agent.io.serialize import write_yaml
from cortex_agent.model.agent_config import AgentConfig, normalize
from cortex_agent.snowflake.rest_client import client_from_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def export_one(client, agent_name: str, out_path: Path) -> None:
    print(f"Exporting agent '{agent_name}' ...")
    raw = client.describe(agent_name)
    config = AgentConfig.from_describe_response(raw)
    data = normalize(config)
    write_yaml(data, out_path)
    print(f"  -> {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Cortex Agent config to YAML.")
    parser.add_argument("--agent", help="Name of the agent to export.")
    parser.add_argument(
        "--out", help="Output YAML path (default: configs/agents/<name>.yaml)."
    )
    parser.add_argument(
        "--all", action="store_true", help="Export all agents in the database/schema."
    )
    args = parser.parse_args()

    if not args.agent and not args.all:
        parser.error("Provide --agent <name> or --all.")

    client = client_from_env()
    default_dir = PROJECT_ROOT / "configs" / "agents"

    if args.all:
        agents = client.list_agents()
        if not agents:
            print("No agents found.")
            return
        for entry in agents:
            name = entry["name"]
            out = default_dir / f"{name.lower()}.yaml"
            export_one(client, name, out)
    else:
        out = Path(args.out) if args.out else default_dir / f"{args.agent.lower()}.yaml"
        export_one(client, args.agent, out)

    print("Done.")


if __name__ == "__main__":
    main()
