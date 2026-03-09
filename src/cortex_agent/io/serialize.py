"""YAML / JSON serialization with deterministic formatting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def _represent_str(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    """Use literal block style for multi-line strings so they diff nicely."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def write_yaml(data: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    dumper = yaml.Dumper
    dumper.add_representer(str, _represent_str)

    with p.open("w") as f:
        yaml.dump(
            data,
            f,
            Dumper=dumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def read_yaml(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_json(data: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
