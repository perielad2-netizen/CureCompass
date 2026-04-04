"""OpenAI Responses API `json_schema` + `strict: true` requires every object `properties` key in `required`."""

from __future__ import annotations

from typing import Any


def patch_json_schema_for_openai_strict(node: Any) -> None:
    """Recursively set `required` to all keys in `properties` and `additionalProperties: false` for objects."""
    if isinstance(node, dict):
        if node.get("type") == "object" and isinstance(node.get("properties"), dict):
            props = node["properties"]
            node["required"] = list(props.keys())
            node.setdefault("additionalProperties", False)
        defs = node.get("$defs")
        if isinstance(defs, dict):
            for defn in defs.values():
                patch_json_schema_for_openai_strict(defn)
        for k, v in node.items():
            if k == "$defs":
                continue
            patch_json_schema_for_openai_strict(v)
    elif isinstance(node, list):
        for x in node:
            patch_json_schema_for_openai_strict(x)
