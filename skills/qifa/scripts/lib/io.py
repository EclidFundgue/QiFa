"""统一读写 YAML/JSON 与 schema 校验入口。

读取 YAML 时优先用 PyYAML（若已安装），否则回落到内置 miniyaml（支持子集）。
写出 YAML 一律用 miniyaml，保证产物确定性。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import minischema, miniyaml, paths

try:  # pragma: no cover - 取决于环境
    import yaml as _pyyaml
except ImportError:  # pragma: no cover
    _pyyaml = None

try:  # pragma: no cover
    import jsonschema as _jsonschema
except ImportError:  # pragma: no cover
    _jsonschema = None


def load_yaml(path) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    if _pyyaml is not None:
        return _pyyaml.safe_load(text)
    return miniyaml.loads(text)


def dump_yaml(path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(miniyaml.dumps(data), encoding="utf-8")


def load_json(path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def schema_path(name: str) -> Path:
    return paths.skill_dir() / "references" / "schemas" / f"{name}.schema.json"


def load_schema(name: str) -> dict:
    return load_json(schema_path(name))


def validate_against_schema(instance: Any, schema_name: str) -> list[str]:
    """返回错误列表；schema_name 如 'source-model'。"""
    schema = load_schema(schema_name)
    if _jsonschema is not None:  # pragma: no cover - 取决于环境
        validator = _jsonschema.Draft202012Validator(schema)
        return [
            f"$.{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            if error.absolute_path
            else f"$: {error.message}"
            for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        ]
    return minischema.validate(instance, schema)
