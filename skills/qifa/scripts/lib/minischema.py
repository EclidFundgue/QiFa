"""最小 JSON Schema 校验实现（零第三方依赖）。

支持子集：type / enum / const / required / properties / additionalProperties /
items / $ref（仅本地 #/...）/ anyOf / allOf / oneOf / minItems / maxItems /
minLength / maxLength / pattern / minimum / maximum。

QiFa 的 schemas/*.schema.json 有意限制在该子集内。系统装了 jsonschema 时，
`lib.io.validate_against_schema` 会优先使用它。
"""

from __future__ import annotations

import re
from typing import Any

_TYPE_NAMES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def validate(instance: Any, schema: Any) -> list[str]:
    """返回错误信息列表；空列表表示通过。"""
    return list(_iter_errors(instance, schema, schema, "$"))


def _iter_errors(instance: Any, schema: Any, root: Any, path: str):
    if schema is True or schema == {}:
        return
    if schema is False:
        yield f"{path}: 不允许任何值"
        return
    if not isinstance(schema, dict):
        yield f"{path}: 非法 schema 节点 {schema!r}"
        return

    if "$ref" in schema:
        resolved = _resolve_ref(schema["$ref"], root)
        if resolved is None:
            yield f"{path}: 无法解析 {schema['$ref']}"
            return
        yield from _iter_errors(instance, resolved, root, path)
        return

    expected_type = schema.get("type")
    if expected_type is not None and not _check_type(instance, expected_type):
        yield f"{path}: 类型应为 {expected_type}，实际为 {_type_name(instance)}"
        return

    if "const" in schema and instance != schema["const"]:
        yield f"{path}: 应为 {schema['const']!r}，实际为 {instance!r}"

    if "enum" in schema and instance not in schema["enum"]:
        yield f"{path}: 取值必须是 {schema['enum']!r} 之一，实际为 {instance!r}"

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            yield f"{path}: 长度 {len(instance)} 小于 minLength {schema['minLength']}"
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            yield f"{path}: 长度 {len(instance)} 大于 maxLength {schema['maxLength']}"
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            yield f"{path}: 不匹配 pattern {schema['pattern']!r}"

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            yield f"{path}: {instance} 小于 minimum {schema['minimum']}"
        if "maximum" in schema and instance > schema["maximum"]:
            yield f"{path}: {instance} 大于 maximum {schema['maximum']}"

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            yield f"{path}: 元素数 {len(instance)} 小于 minItems {schema['minItems']}"
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            yield f"{path}: 元素数 {len(instance)} 大于 maxItems {schema['maxItems']}"
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(instance):
                yield from _iter_errors(item, item_schema, root, f"{path}[{index}]")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                yield f"{path}: 缺少必需字段 {key!r}"
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                yield from _iter_errors(value, properties[key], root, f"{path}.{key}")
            elif "additionalProperties" in schema:
                additional = schema["additionalProperties"]
                if additional is False:
                    yield f"{path}: 不允许额外字段 {key!r}"
                elif isinstance(additional, dict):
                    yield from _iter_errors(value, additional, root, f"{path}.{key}")

    if "anyOf" in schema:
        if not any(not _has_error(instance, sub, root) for sub in schema["anyOf"]):
            yield f"{path}: 不满足 anyOf 中任何一个分支"

    if "allOf" in schema:
        for sub in schema["allOf"]:
            yield from _iter_errors(instance, sub, root, path)

    if "oneOf" in schema:
        matches = sum(1 for sub in schema["oneOf"] if not _has_error(instance, sub, root))
        if matches != 1:
            yield f"{path}: oneOf 要求恰好匹配一个分支，实际匹配 {matches} 个"


def _has_error(instance: Any, schema: Any, root: Any) -> bool:
    return any(True for _ in _iter_errors(instance, schema, root, "$"))


def _resolve_ref(ref: str, root: Any) -> Any:
    if not ref.startswith("#/"):
        return None
    node = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _check_type(instance: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        if name == "boolean" and isinstance(instance, bool):
            return True
        if name == "integer" and isinstance(instance, int) and not isinstance(instance, bool):
            return True
        if name == "number" and isinstance(instance, (int, float)) and not isinstance(instance, bool):
            return True
        if name == "string" and isinstance(instance, str):
            return True
        if name == "array" and isinstance(instance, list):
            return True
        if name == "object" and isinstance(instance, dict):
            return True
        if name == "null" and instance is None:
            return True
    if expected == "boolean" and isinstance(instance, int):
        return False
    return False


def _type_name(instance: Any) -> str:
    for cls, name in _TYPE_NAMES.items():
        if cls is bool and isinstance(instance, bool):
            return "boolean"
        if cls is int and isinstance(instance, bool):
            continue
        if isinstance(instance, cls):
            return name
    return type(instance).__name__
