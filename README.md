## Cortex Agent

Config-as-code workflow for **Snowflake Cortex Agents**: export existing agents to YAML, review them in version control, and redeploy changes back to Snowflake.

This repository provides:

- **Typed models** (`AgentConfig`) that mirror the Cortex Agent REST schema.
- **CLI-style scripts** to export and deploy agents:
  - `scripts/export_agent.py`
  - `scripts/deploy_agent.py`

### Features

- **Export agents to YAML** for audit, review, and change tracking.
- **Normalize and validate configs** using Pydantic models.
- **Deploy agents from YAML** to Snowflake via the Cortex Agents REST API.
- **Environment-based configuration** via `.env` and key pair auth.

### Requirements

- Python **3.10+**
- Network access to your Snowflake account
- A Snowflake user configured for **key pair authentication**

Python dependencies are defined in `pyproject.toml` (Pydantic, PyYAML, requests, cryptography, python-dotenv, PyJWT).

### Installation

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or, if you are using `uv`:

```bash
uv sync
```

### Snowflake Configuration

This project expects **key pair authentication** and a Cortex Agents–enabled Snowflake account.

1. **Create a key pair** and upload the public key to the Snowflake user used for the agent:
   - Follow Snowflake’s key pair auth docs to generate an RSA key pair.
   - Save the **private key** (e.g. `rsa_key.pem`) on the machine running these scripts.

2. **Set environment variables** (e.g. via `.env` in the project root):

```bash
SNOWFLAKE_ACCOUNT="your_account_identifier"
SNOWFLAKE_USER="your_user"
SNOWFLAKE_PRIVATE_KEY_PATH="rsa_key.pem"
SNOWFLAKE_ROLE="YOUR_ROLE"                 # optional but recommended
SNOWFLAKE_WAREHOUSE="YOUR_WAREHOUSE"       # optional
SNOWFLAKE_DATABASE="YOUR_DATABASE"
SNOWFLAKE_SCHEMA="YOUR_SCHEMA"
```

`cortex_agent.snowflake.rest_client.client_from_env` loads these values using `python-dotenv`.

### Directory Layout

- `configs/agents/` – YAML definitions for agents (exported and ready to deploy).
- `scripts/export_agent.py` – Export existing Cortex Agents to YAML.
- `scripts/deploy_agent.py` – Deploy a YAML agent definition to Snowflake.
- `src/cortex_agent/model/agent_config.py` – Pydantic models for the agent spec.
- `src/cortex_agent/snowflake/rest_client.py` – Thin REST client for the Cortex Agents API.

### Exporting Agents to YAML

Activate your virtual environment, then export an agent:

```bash
python scripts/export_agent.py --agent MY_AGENT
```

By default this writes a **timestamped** YAML file under `configs/agents/`, for example:

- `configs/agents/my_agent_20260310-153045.yaml`

This avoids overwriting previous exports, which is especially helpful when you tweak configs in the Snowflake UI and re‑export multiple times.

The script uses `AgentConfig.from_describe_response` to parse the `DESCRIBE` response and `normalize` to produce clean, deterministic YAML.

To export to a custom path (no timestamp added):

```bash
python scripts/export_agent.py --agent MY_AGENT --out path/to/agent.yaml
```

To export **all agents** in the configured database/schema:

```bash
python scripts/export_agent.py --all
```

YAML files are normalized (stable key order, `None` values stripped) for clean diffs.

### Deploying Agents from YAML

Given a YAML file like `configs/agents/bigbangbev.yaml`, you can deploy it as a Cortex Agent.
The agent name is read from the `name` field inside the YAML file.

```bash
python scripts/deploy_agent.py configs/agents/bigbangbev.yaml
```

This:

- Validates the YAML against `AgentConfig`.
- Reads the agent name from the `name` field in the config.
- Calls `CortexAgentClient.create` with the resulting JSON body.

#### Create modes

The `--mode` flag controls how Snowflake handles existing agents (default: `ifNotExists`):

- `orReplace` – create or replace the agent.
- `ifNotExists` – only create if the agent does **not** already exist.
- `errorIfExists` – fail if the agent already exists.

Example:

```bash
python scripts/deploy_agent.py configs/agents/bigbangbev.yaml --mode orReplace
```

### Working with Agent Configs

Agent configs are modeled by `AgentConfig` in `src/cortex_agent/model/agent_config.py`. A typical YAML file (e.g. `bigbangbev.yaml`) includes:

- **name** – the agent name in Snowflake.
- **models.orchestration** – underlying model (e.g. `openai-gpt-4.1`).
- **instructions** – response/orchestration/system instructions and sample questions.
- **tools** – tool specs (e.g. `cortex_analyst_text_to_sql`, `generic` tools).
- **tool_resources** – execution environments, semantic views, and procedure identifiers.

You can edit these YAML files directly, commit them to version control, and redeploy.

### Example: BIGBANGBEV Agent

The sample config `configs/agents/bigbangbev.yaml` defines a **sales analytics assistant** for Big Bang Beverages that:

- Uses an LLM (`openai-gpt-4.1`) orchestrated by Cortex Agents.
- Connects to Snowflake semantic views for sales, promotions, and inventory.
- Provides RGM-style insights and can send summary emails via a `send_email` stored procedure.

Use it as a template when creating new agents for your own data models.

### Development Notes

- The client in `rest_client.py` is intentionally **thin** and raises an error if the Snowflake REST API responds with a non-2xx status (showing up to 500 characters of the response body).
- Extra fields in `ToolResource` are allowed (`extra="allow"`) so you can extend tool metadata without changing the model.

### License

Internal / proprietary. Do not distribute without permission.

