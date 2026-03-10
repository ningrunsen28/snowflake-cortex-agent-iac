#!/usr/bin/env python3
"""Deploy a Cortex Agent config from a local YAML file to Snowflake.

Usage:
    python scripts/deploy_agent.py --agent my_agent
    python scripts/deploy_agent.py --agent my_agent --mode orReplace
    python scripts/deploy_agent.py --config path/to/agent.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cortex_agent.io.serialize import read_yaml
from cortex_agent.model.agent_config import AgentConfig
from cortex_agent.snowflake.rest_client import client_from_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy Cortex Agent config to Snowflake."
    )
    parser.add_argument(
        "--agent", help="Agent name (matches <name>.yaml in configs/agents/)."
    )
    parser.add_argument("--config", help="Explicit path to the YAML config file.")
    parser.add_argument(
        "--mode",
        default="ifNotExists",
        choices=["orReplace", "ifNotExists", "errorIfExists"],
        help="Create mode (default: orReplace).",
    )
    args = parser.parse_args()

    if not args.agent and not args.config:
        parser.error("Provide --agent <name> or --config <path>.")

    if args.config:
        config_path = Path(args.config)
    else:
        config_path = PROJECT_ROOT / "configs" / "agents" / f"{args.agent.lower()}.yaml"

    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading config: {config_path}")
    spec = read_yaml(config_path)

    config = AgentConfig.model_validate(spec)
    body = config.to_create_body()

    print(f"Deploying agent '{config.name}' (mode={args.mode}) ...")
    client = client_from_env()
    result = client.create(body, create_mode=args.mode)
    print(f"  -> {result}")
    print("Done.")


if __name__ == "__main__":
    main()
