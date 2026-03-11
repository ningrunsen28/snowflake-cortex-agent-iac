#!/usr/bin/env python3
"""Export the Cortex Agent config from Snowflake to configs/agent_config.yaml.

The agent name is read from the CORTEX_AGENT_NAME environment variable.

Usage:
    python scripts/export_agent.py
"""

from __future__ import annotations

from pathlib import Path

from cortex_agent.io.serialize import write_yaml
from cortex_agent.model.agent_config import AgentConfig, normalize
from cortex_agent.snowflake.rest_client import agent_name_from_env, client_from_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "agent_config.yaml"


def export_agent() -> None:
    agent_name = agent_name_from_env()
    client = client_from_env()

    print(f"Exporting agent '{agent_name}' ...")
    raw = client.describe(agent_name)
    config = AgentConfig.from_describe_response(raw)
    data = normalize(config)

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(data, CONFIG_PATH)
    print(f"  -> {CONFIG_PATH}")
    print("Done.")


# def main() -> None:
#     agent_name = agent_name_from_env()
#     client = client_from_env()

#     print(f"Exporting agent '{agent_name}' ...")
#     raw = client.describe(agent_name)
#     config = AgentConfig.from_describe_response(raw)
#     data = normalize(config)

#     CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
#     write_yaml(data, CONFIG_PATH)
#     print(f"  -> {CONFIG_PATH}")
#     print("Done.")


if __name__ == "__main__":
    export_agent()
