## Cortex Agent IaC

Config-as-code / IaC workflow for a **Snowflake Cortex Agent**: export the agent config, semantic views, and procedures to version-controlled files, review changes in PRs, and redeploy everything back to Snowflake.

This repository manages **one agent** and all its dependencies. The agent config lives at `configs/agent_config.yaml`, semantic view YAML definitions in `configs/semantic_views/`, and procedure DDL in `configs/procedures/`. Environment variables provide defaults for local dev; CLI flags override them for CI pipelines.

> This repo manages the **Cortex Agent configuration and dev workflow**, not shared account-level components like Web Search or Cortex Search. Those may be integrated as future, shared dependencies but are **not part of the current release**.

### GitHub Actions & Workflows

The main way to work with this repo is through **GitHub Actions**. Dev workspaces are created from the Actions UI (no need to run scripts in CI yourself); developers then use a **feature branch** and only update **`.env`** locally to point at their dev schema and agent.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Create Dev Workspace** | Manual (`workflow_dispatch`) | Creates `DEV_<DEVELOPER>` schema, deploys semantic views + procedures + agent from repo files. Input: `developer` (required), `database` (optional). |
| **Cleanup Dev Workspace** | Manual | Drops the dev agent and `DEV_<DEVELOPER>` schema. Same inputs as create. |
| **Validate PR** | Pull request to `develop` / `main` (when `configs/` or `src/` change) | Validates `configs/agent_config.yaml` against the AgentConfig schema. |
| **Deploy Agent** | Push to `develop` / `main` (when `configs/agent_config.yaml` changes), or manual | Deploys semantic views, procedures, and agent to the **canonical** (production) schema. |

Workflows use repository **secrets** and **variables** (and the **development** / **production** environments). See [GitHub Actions Secrets](#github-actions-secrets) below.

### Features

- **Config-as-code for Cortex Agents** — treat your agent, semantic views, and procedures like application code with PR review, CI validation, and reproducible dev workspaces.
- **Export everything** — agent config, semantic view YAML (`SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW`), and procedure DDL (`GET_DDL`).
- **Deploy everything** — semantic views (`SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`), procedures, and the agent in one command.
- **Normalize and validate configs** using Pydantic models.
- **Reference rewriting** — deploy the same config to any database/schema; FQ names are rewritten at deploy time.
- **Dev workspaces** — isolated per-developer schemas created from repo files (no Snowflake-to-Snowflake cloning).
- **GitHub Actions** — automated validation, deployment, workspace creation, and cleanup.

### Requirements

- Python **3.10+**
- Network access to your Snowflake account
- A Snowflake user configured for **key pair authentication**, with:
  - Privileges to create/drop schemas, semantic views, and procedures in the target database
  - Access to Snowflake Cortex Agents in the account

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

### Quickstart

After creating a dev workspace via **Actions → Create Dev Workspace** (see [Developer Workflow](#developer-workflow-sop)) and setting `.env` to your dev schema/agent:

```bash
# 1) Install
uv sync  # or: python -m venv .venv && source .venv/bin/activate && pip install -e .

# 2) Export changes back from your dev copy (uses .env if set)
python scripts/export_agent.py
```

### Snowflake Configuration

This project expects **key pair authentication** and a Cortex Agents-enabled Snowflake account.

1. **Create a key pair** and upload the public key to the Snowflake user:
   - Follow Snowflake's key pair auth docs to generate an RSA key pair.
   - Save the **private key** (e.g. `rsa_key.pem`) on the machine running these scripts.

2. **Set environment variables** (e.g. via `.env` in the project root; `.env` is gitignored so each developer can point at their own dev schema):

```bash
CORTEX_AGENT_NAME="MY_AGENT"
SNOWFLAKE_ACCOUNT="your_account_identifier"
SNOWFLAKE_USER="your_user"
SNOWFLAKE_PRIVATE_KEY_PATH="rsa_key.pem"
SNOWFLAKE_ROLE="YOUR_ROLE"                 # optional but recommended
SNOWFLAKE_WAREHOUSE="YOUR_WAREHOUSE"       # optional
SNOWFLAKE_DATABASE="YOUR_DATABASE"
SNOWFLAKE_SCHEMA="YOUR_SCHEMA"
```

`CORTEX_AGENT_NAME` identifies which agent this repo manages. `SNOWFLAKE_DATABASE` and `SNOWFLAKE_SCHEMA` define the **canonical** (production) location. All values are loaded by `client_from_env` using `python-dotenv` and can be overridden by CLI flags.

### Directory Layout

```
configs/
  agent_config.yaml               # Agent config (single source of truth)
  semantic_views/                  # Semantic view YAML definitions
    BIG_BANG_BEVERAGES_SALES.yaml
    BIG_BANG_PROMO_CALENDAR.yaml
    BIG_BANG_INVENTORY.yaml
  procedures/                      # Procedure DDL (CREATE PROCEDURE ...)
    SEND_EMAIL.sql
scripts/
  export_agent.py                  # Export agent + semantic views + procedures
  deploy_agent.py                  # Deploy semantic views + procedures + agent
  create_workspace.py              # Create a dev workspace from repo files
  cleanup_workspace.py             # Tear down a dev workspace
.github/workflows/
  create-workspace.yml             # Manual: create dev workspace
  validate-pr.yml                  # On PR: validate agent config YAML
  deploy.yml                       # On merge: deploy to production
  cleanup.yml                      # Manual: cleanup dev workspace
src/cortex_agent/
  deploy.py                        # Shared deploy logic (semantic views + procedures)
  model/agent_config.py            # Pydantic models + reference rewriting
  snowflake/rest_client.py         # REST client (Agents API + SQL API)
  io/serialize.py                  # YAML/JSON helpers
```

### Developer Workflow (SOP)

#### Step 1: Create Dev Workspace (GitHub Actions)

In the repo, go to **Actions → Create Dev Workspace**, run the workflow, and enter your **developer** id (e.g. `alice`). Optionally set **database** if you override the default. The workflow creates `DEV_ALICE` schema, deploys semantic views and procedures from the repo, and deploys the agent with references rewritten to that schema. Shared components (e.g. Web Search, Cortex Search) are not copied into the dev workspace.

You can also run locally: `python scripts/create_workspace.py --developer ALICE`.

#### Step 2: Feature Branch and Local .env

Create a **feature branch** from `develop`. To run export (and other scripts) against **your** dev copy, you only need to point your local environment at it. Copy or edit **`.env`** in the project root (it is gitignored) so that it targets your dev schema and, if you like, the dev agent name:

```bash
# Example: work against DEV_ALICE workspace
SNOWFLAKE_SCHEMA=DEV_ALICE
# Optional: default export/deploy to use dev agent name
CORTEX_AGENT_NAME=BIGBANGBEV_DEV_ALICE
```

Other vars (`SNOWFLAKE_DATABASE`, `SNOWFLAKE_ACCOUNT`, etc.) stay the same. No code changes required — only `.env` for your copy.

#### Step 3: Modify and Test

Edit the agent configuration or semantic views in **Snowsight** in the `DEV_<DEVELOPER>` schema. Test queries and behavior there.

#### Step 4: Export Configuration

Export the tested config, semantic views, and procedures back into the repo. With `.env` set to your dev schema/agent, you can run (flags optional if env is set):

```bash
python scripts/export_agent.py
# Or explicitly:
python scripts/export_agent.py --agent BIGBANGBEV_DEV_ALICE --database SNOW_AI_DEMO_DB --schema DEV_ALICE
```

References in the exported files are normalized back to **canonical** DB/schema so git stays environment-agnostic.

#### Step 5: Review Changes

Open a pull request to `develop` (or `main`). The **Validate PR** workflow runs automatically on the changed config.

#### Step 6: Deploy

On merge to `develop` or `main`, the **Deploy Agent** workflow deploys to the canonical (production) schema.

#### Step 7: Cleanup

When done with the dev workspace, run **Actions → Cleanup Dev Workspace** with the same `developer` (and `database` if you used it). Or run `python scripts/cleanup_workspace.py --developer ALICE` locally.

### Reference Rewriting

The YAML in git always uses **canonical** database/schema names (from env vars). When deploying to a different target, all `DB.SCHEMA.*` references in `tool_resources` (semantic views, procedures, etc.) are rewritten automatically:

- **On deploy** (`deploy_agent.py`): canonical refs -> target refs
- **On export** (`export_agent.py`): source (dev) refs -> canonical refs

This keeps the config in git environment-agnostic while ensuring each deployment points to the correct objects.

Semantic view YAML files contain `base_table` references pointing to the underlying data tables. These are **not** rewritten during dev deploys because the data tables are shared -- only the semantic view object itself is created in the dev schema. Procedure DDL is rewritten to the target schema.

### Scripts Reference

#### export_agent.py

Exports the agent config, semantic view YAML definitions (via `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW`), and procedure DDL (via `GET_DDL`) to the `configs/` directory.

| Flag | Default | Description |
|------|---------|-------------|
| `--agent` | `CORTEX_AGENT_NAME` env var | Agent name to export from Snowflake |
| `--database` | `SNOWFLAKE_DATABASE` env var | Source database |
| `--schema` | `SNOWFLAKE_SCHEMA` env var | Source schema |

#### deploy_agent.py

Deploys semantic views (via `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`), procedures (DDL execution), and the agent config -- in that order.

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `configs/agent_config.yaml` | Path to the YAML config file |
| `--agent` | `name` field in config YAML | Override agent name for deployment |
| `--database` | `SNOWFLAKE_DATABASE` env var | Target database |
| `--schema` | `SNOWFLAKE_SCHEMA` env var | Target schema |
| `--mode` | `orReplace` | `orReplace`, `ifNotExists`, `errorIfExists` |

#### create_workspace.py

| Flag | Default | Description |
|------|---------|-------------|
| `--developer` | *(required)* | Developer username (becomes `DEV_<DEVELOPER>` schema) |
| `--database` | `SNOWFLAKE_DATABASE` env var | Target database |
| `--config` | `configs/agent_config.yaml` | Agent config to deploy into workspace |

#### cleanup_workspace.py

| Flag | Default | Description |
|------|---------|-------------|
| `--developer` | *(required)* | Developer username (maps to `DEV_<DEVELOPER>` schema) |
| `--database` | `SNOWFLAKE_DATABASE` env var | Target database |

### GitHub Actions Secrets

The following secrets must be configured in the repository:

| Secret | Description |
|--------|-------------|
| `CORTEX_AGENT_NAME` | Canonical agent name |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PRIVATE_KEY` | RSA private key contents (PEM) |
| `SNOWFLAKE_ROLE` | Snowflake role |
| `SNOWFLAKE_WAREHOUSE` | Snowflake warehouse |
| `SNOWFLAKE_DATABASE` | Canonical database |
| `SNOWFLAKE_SCHEMA` | Canonical schema |

Configure two GitHub Environments: **development** (for workspace create/cleanup) and **production** (for deploy, with required reviewers). These secrets are consumed by the workflows in `.github/workflows/` to validate configs, create/clean up dev workspaces, and deploy the agent to the canonical schema.

### Development Notes

- The client in `rest_client.py` is intentionally **thin** and raises on non-2xx status.
- Extra fields in `ToolResource` are allowed (`extra="allow"`) for extensibility.
- `rewrite_references` in `agent_config.py` does a recursive string replacement of `SOURCE_DB.SOURCE_SCHEMA` with `TARGET_DB.TARGET_SCHEMA` across the entire config dict.
- Semantic views are exported/deployed via Snowflake system functions (`SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW` / `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`), not stage files or CLONE.
- Procedure DDL is exported via `GET_DDL` and re-executed with schema rewriting on deploy.
- Future work: support shared components such as **Web Search** and **Cortex Search** that are managed once per account and **not copied into per-developer workspaces** during `create_workspace.py` / workspace Actions runs. This behavior is **not implemented in the current release** and is a possible future enhancement.

