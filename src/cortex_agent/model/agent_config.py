"""Pydantic models for the Snowflake Cortex Agent spec.

These mirror the REST API schema so we get validation for free on both
export (parsing the Describe response) and deploy (building a request body).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


# ------------------------------------------------------------------
# Nested models
# ------------------------------------------------------------------


class AgentProfile(BaseModel):
    display_name: str | None = None


class ModelConfig(BaseModel):
    orchestration: str | None = None


class BudgetConfig(BaseModel):
    seconds: int | None = None
    tokens: int | None = None


class OrchestrationConfig(BaseModel):
    budget: BudgetConfig | None = None


class AgentInstructions(BaseModel):
    response: str | None = None
    orchestration: str | None = None
    system: str | None = None
    sample_questions: list[dict[str, Any]] | None = None


class ToolInputSchema(BaseModel):
    type: str | None = None
    description: str | None = None
    properties: dict[str, Any] | None = None
    items: dict[str, Any] | None = None
    required: list[str] | None = None


class ToolSpec(BaseModel):
    type: str
    name: str
    description: str | None = None
    input_schema: ToolInputSchema | None = None


class Tool(BaseModel):
    tool_spec: ToolSpec


class ExecutionEnvironment(BaseModel):
    type: str | None = None
    warehouse: str | None = None
    query_timeout: int | None = None


class ToolResource(BaseModel, extra="allow"):
    """Tool resources vary by tool type so we allow extra fields."""

    type: str | None = None
    execution_environment: ExecutionEnvironment | None = None
    identifier: str | None = None
    semantic_model_file: str | None = None
    semantic_view: str | None = None
    search_service: str | None = None
    title_column: str | None = None
    id_column: str | None = None
    filter: dict[str, Any] | None = None
    max_results: int | None = None


# ------------------------------------------------------------------
# Top-level agent config
# ------------------------------------------------------------------


class AgentConfig(BaseModel, extra="allow"):
    """Canonical representation of a Cortex Agent spec.

    Maps 1:1 to the JSON body used in the Create / Update REST endpoints,
    plus `name` (used in Create).
    """

    name: str
    comment: str | None = None
    profile: AgentProfile | None = None
    models: ModelConfig | None = None
    instructions: AgentInstructions | None = None
    orchestration: OrchestrationConfig | None = None
    tools: list[Tool] | None = None
    tool_resources: dict[str, ToolResource] | None = None
    tool_unable_to_answer: str | None = None

    # --- helpers ---

    def to_create_body(self) -> dict[str, Any]:
        """Serialize to the JSON body expected by POST /agents."""
        return self.model_dump(exclude_none=True)

    def to_update_body(self) -> dict[str, Any]:
        """Serialize to the JSON body expected by PUT /agents/{name} (no name field)."""
        return self.model_dump(exclude_none=True, exclude={"name"})

    @classmethod
    def from_describe_response(cls, data: dict[str, Any]) -> "AgentConfig":
        """Parse the Describe endpoint response into an AgentConfig.

        The Describe response has `agent_spec` as a JSON *string* plus
        top-level `name`, `database_name`, `schema_name`, etc.
        """
        raw_spec = data.get("agent_spec", "{}")
        spec = json.loads(raw_spec) if isinstance(raw_spec, str) else raw_spec
        spec["name"] = data["name"]
        return cls.model_validate(spec)


# ------------------------------------------------------------------
# Normalization
# ------------------------------------------------------------------


def normalize(config: AgentConfig) -> dict[str, Any]:
    """Return a dict with stable key ordering for deterministic YAML output.

    Strips None values so exported files stay clean.
    """
    KEY_ORDER = [
        "name",
        "comment",
        "profile",
        "models",
        "instructions",
        "orchestration",
        "tools",
        "tool_resources",
        "tool_unable_to_answer",
    ]
    raw = config.model_dump(exclude_none=True)
    ordered: dict[str, Any] = {}
    for key in KEY_ORDER:
        if key in raw:
            ordered[key] = raw[key]
    for key in sorted(raw.keys()):
        if key not in ordered:
            ordered[key] = raw[key]
    return ordered


# ------------------------------------------------------------------
# Reference rewriting
# ------------------------------------------------------------------


def rewrite_references(
    data: dict[str, Any],
    source_db: str,
    source_schema: str,
    target_db: str,
    target_schema: str,
) -> dict[str, Any]:
    """Swap fully-qualified ``DB.SCHEMA`` prefixes in every string value.

    Walks the entire config dict recursively and replaces occurrences of
    ``SOURCE_DB.SOURCE_SCHEMA`` with ``TARGET_DB.TARGET_SCHEMA``.  This
    rewrites ``semantic_view``, ``identifier``, ``semantic_model_file``,
    and any other field that contains a fully-qualified Snowflake name.

    Returns a **new** dict; the original is not mutated.
    """
    src = f"{source_db.upper()}.{source_schema.upper()}"
    tgt = f"{target_db.upper()}.{target_schema.upper()}"

    if src == tgt:
        return data

    def _walk(obj: Any) -> Any:
        if isinstance(obj, str):
            return obj.replace(src, tgt)
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(item) for item in obj]
        return obj

    return _walk(data)
