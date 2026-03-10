#!/usr/bin/env python3
"""Deploy a Cortex Agent config from a local YAML file to Snowflake.

Usage:
    python scripts/deploy_agent.py configs/agents/bigbangbev.yaml
    python scripts/deploy_agent.py configs/agents/bigbangbev.yaml --mode orReplace
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cortex_agent.io.serialize import read_yaml
from cortex_agent.model.agent_config import AgentConfig
from cortex_agent.snowflake.rest_client import client_from_env


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy Cortex Agent config to Snowflake."
    )
    parser.add_argument("config", type=Path, help="Path to the YAML config file.")
    parser.add_argument(
        "--mode",
        default="ifNotExists",
        choices=["orReplace", "ifNotExists", "errorIfExists"],
        help="Create mode (default: ifNotExists).",
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading config: {args.config}")
    spec = read_yaml(args.config)

    config = AgentConfig.model_validate(spec)
    body = config.to_create_body()

    print(f"Deploying agent '{config.name}' (mode={args.mode}) ...")
    client = client_from_env()
    result = client.create(body, create_mode=args.mode)
    print(f"  -> {result}")
    print("Done.")


if __name__ == "__main__":
    main()
