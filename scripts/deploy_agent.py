#!/usr/bin/env python3
"""Deploy the Cortex Agent config from configs/agent_config.yaml to Snowflake.

Usage:
    python scripts/deploy_agent.py
    python scripts/deploy_agent.py --mode orReplace
"""

from __future__ import annotations

# import argparse
import sys
from pathlib import Path

from cortex_agent.io.serialize import read_yaml
from cortex_agent.model.agent_config import AgentConfig
from cortex_agent.snowflake.rest_client import client_from_env
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "agent_config.yaml"
Mode = Literal["orReplace", "ifNotExists", "errorIfExists"]


def deploy_agent(mode: Mode = "orReplace") -> None:
    if not CONFIG_PATH.exists():
        print(f"Error: config file not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading config: {CONFIG_PATH}")
    spec = read_yaml(CONFIG_PATH)

    config = AgentConfig.model_validate(spec)
    body = config.to_create_body()

    print(f"Deploying agent '{config.name}' (mode={mode}) ...")
    client = client_from_env()
    result = client.create(body, create_mode=mode)
    print(f"  -> {result}")
    print("Done.")


# def main() -> None:
#     parser = argparse.ArgumentParser(
#         description="Deploy Cortex Agent config to Snowflake."
#     )
#     parser.add_argument(
#         "--mode",
#         default="ifNotExists",
#         choices=["orReplace", "ifNotExists", "errorIfExists"],
#         help="Create mode (default: ifNotExists).",
#     )
#     args = parser.parse_args()

#     if not CONFIG_PATH.exists():
#         print(f"Error: config file not found: {CONFIG_PATH}", file=sys.stderr)
#         sys.exit(1)

#     print(f"Loading config: {CONFIG_PATH}")
#     spec = read_yaml(CONFIG_PATH)

#     config = AgentConfig.model_validate(spec)
#     body = config.to_create_body()

#     print(f"Deploying agent '{config.name}' (mode={args.mode}) ...")
#     client = client_from_env()
#     result = client.create(body, create_mode=args.mode)
#     print(f"  -> {result}")
#     print("Done.")


if __name__ == "__main__":
    deploy_agent()
