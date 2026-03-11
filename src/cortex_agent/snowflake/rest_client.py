"""Thin HTTP client for the Snowflake Cortex Agents REST API."""

from __future__ import annotations

from typing import Any

import requests

from cortex_agent.snowflake.auth import generate_jwt


class CortexAgentClient:
    """Wraps the /api/v2/databases/{db}/schemas/{schema}/agents endpoints."""

    def __init__(
        self,
        account: str,
        user: str,
        private_key_path: str,
        database: str,
        schema: str,
        role: str | None = None,
        warehouse: str | None = None,
    ):
        self._account = account
        self._user = user
        self._private_key_path = private_key_path
        self._database = database
        self._schema = schema
        self._role = role
        self._warehouse = warehouse

        self._base_url = (
            f"https://{account}.snowflakecomputing.com"
            f"/api/v2/databases/{database}/schemas/{schema}/agents"
        )

    def _headers(self) -> dict[str, str]:
        token = generate_jwt(self._account, self._user, self._private_key_path)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
            "Content-Type": "application/json",
        }
        if self._role:
            headers["X-Snowflake-Role"] = self._role
        return headers

    def _raise_for_status(self, resp: requests.Response) -> None:
        if not resp.ok:
            detail = resp.text[:500] if resp.text else "(no body)"
            raise RuntimeError(f"Snowflake API error {resp.status_code}: {detail}")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def describe(self, agent_name: str) -> dict[str, Any]:
        """GET /agents/{name} — export a single agent's full spec."""
        resp = requests.get(
            f"{self._base_url}/{agent_name}",
            headers=self._headers(),
        )
        self._raise_for_status(resp)
        return resp.json()

    def list_agents(self) -> list[dict[str, Any]]:
        """GET /agents — list all agents in the database/schema."""
        resp = requests.get(self._base_url, headers=self._headers())
        self._raise_for_status(resp)
        return resp.json()

    def create(
        self,
        spec: dict[str, Any],
        create_mode: str = "orReplace",
    ) -> dict[str, Any]:
        """POST /agents — create (or replace) an agent.

        Args:
            spec: Full agent body (name, models, instructions, tools, etc.).
            create_mode: "errorIfExists", "orReplace", or "ifNotExists".
        """
        resp = requests.post(
            self._base_url,
            headers=self._headers(),
            json=spec,
            params={"createMode": create_mode},
        )
        self._raise_for_status(resp)
        return resp.json()

    def update(self, agent_name: str, spec: dict[str, Any]) -> dict[str, Any]:
        """PUT /agents/{name} — update an existing agent."""
        resp = requests.put(
            f"{self._base_url}/{agent_name}",
            headers=self._headers(),
            json=spec,
        )
        self._raise_for_status(resp)
        return resp.json()

    def delete(self, agent_name: str, if_exists: bool = True) -> dict[str, Any]:
        """DELETE /agents/{name} — delete an agent."""
        resp = requests.delete(
            f"{self._base_url}/{agent_name}",
            headers=self._headers(),
            params={"ifExists": str(if_exists).lower()},
        )
        self._raise_for_status(resp)
        return resp.json()

    # ------------------------------------------------------------------
    # SQL execution (Snowflake SQL API)
    # ------------------------------------------------------------------

    def execute_sql(
        self,
        statement: str,
        *,
        database: str | None = None,
        schema: str | None = None,
    ) -> dict[str, Any]:
        """Execute a SQL statement via the Snowflake SQL API.

        Uses the client's database/schema/warehouse by default; callers
        can override database and schema per call.
        """
        url = f"https://{self._account}.snowflakecomputing.com/api/v2/statements"
        body: dict[str, Any] = {
            "statement": statement,
            "timeout": 60,
            "database": database or self._database,
            "schema": schema or self._schema,
        }
        if self._warehouse:
            body["warehouse"] = self._warehouse

        resp = requests.post(url, headers=self._headers(), json=body)
        self._raise_for_status(resp)
        return resp.json()

    def query_scalar(
        self,
        statement: str,
        *,
        database: str | None = None,
        schema: str | None = None,
    ) -> str:
        """Execute a SQL query and return the first column of the first row."""
        result = self.execute_sql(
            statement,
            database=database,
            schema=schema,
        )
        rows = result.get("data", [])
        if not rows or not rows[0]:
            raise RuntimeError(f"Query returned no data: {statement[:120]}")
        return rows[0][0]


def _load_env() -> tuple:
    """Load .env file and return ``(os_module, require_fn)``."""
    import os

    from dotenv import load_dotenv

    load_dotenv()

    def _require(key: str) -> str:
        val = os.environ.get(key)
        if not val:
            raise ValueError(f"Missing required env var: {key}")
        return val

    return os, _require


def agent_name_from_env() -> str:
    """Read the agent name from the CORTEX_AGENT_NAME env var."""
    _, _require = _load_env()
    return _require("CORTEX_AGENT_NAME")


def canonical_db_schema_from_env() -> tuple[str, str]:
    """Return the canonical ``(database, schema)`` from env vars.

    These represent the *production* database and schema that the YAML
    in git is written against.  Used by deploy/export to detect when
    reference rewriting is needed.
    """
    _, _require = _load_env()
    return _require("SNOWFLAKE_DATABASE"), _require("SNOWFLAKE_SCHEMA")


def client_from_env(
    *,
    database: str | None = None,
    schema: str | None = None,
) -> CortexAgentClient:
    """Build a CortexAgentClient from environment variables / .env file.

    *database* and *schema* override the corresponding env vars when
    provided (e.g. from CLI args in a CI pipeline).
    """
    os, _require = _load_env()

    return CortexAgentClient(
        account=_require("SNOWFLAKE_ACCOUNT"),
        user=_require("SNOWFLAKE_USER"),
        private_key_path=_require("SNOWFLAKE_PRIVATE_KEY_PATH"),
        database=database or _require("SNOWFLAKE_DATABASE"),
        schema=schema or _require("SNOWFLAKE_SCHEMA"),
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
    )
