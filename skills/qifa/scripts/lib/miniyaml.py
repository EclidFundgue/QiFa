"""最小 YAML 读写实现（零第三方依赖）。

定位：QiFa 自产 YAML（project.yaml、run-state.yaml、cases、presets）的确定性
读写。**支持子集**：嵌套 map、list（含 `- key: value` 的映射项）、行内 `[a, b]`
与 `{k: v}`、引号字符串、布尔/null/整数/浮点。不支持锚点、多行块标量（|、>）、
多文档。若系统装了 PyYAML，`lib.io.load_yaml` 会优先使用它读取外部文件。
"""

from __future__ import annotations

import re
from typing import Any

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\- ]*$")
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_BOOLS = {"true": True, "false": False}
_NULLS = {"null", "~", "none"}


class MiniYamlError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# 读取
# --------------------------------------------------------------------------- #

def loads(text: str) -> Any:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if "\t" in stripped[:indent]:
            raise MiniYamlError("缩进不能使用 Tab")
        lines.append((indent, stripped.strip()))
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise MiniYamlError(f"第 {index + 1} 个有效行无法解析：{lines[index][1]!r}")
    return value


def load(path) -> Any:
    return loads(open(path, "r", encoding="utf-8").read())


def _strip_comment(line: str) -> str:
    quote: str | None = None
    for i, ch in enumerate(line):
        if quote:
            if ch == "\\" and quote == '"':
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _parse_block(lines: list[tuple[int, str]], i: int, indent: int):
    if lines[i][1].startswith("-"):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines: list[tuple[int, str]], i: int, indent: int):
    result: dict[str, Any] = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("-"):
        key, sep, rest = lines[i][1].partition(":")
        if not sep:
            raise MiniYamlError(f"缺少冒号的映射行：{lines[i][1]!r}")
        key = _unquote(key.strip())
        rest = rest.strip()
        if rest:
            result[key] = _parse_scalar(rest)
            i += 1
        else:
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                result[key], i = _parse_block(lines, i, lines[i][0])
            else:
                result[key] = None
    return result, i


def _parse_list(lines: list[tuple[int, str]], i: int, indent: int):
    result: list[Any] = []
    while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("-"):
        rest = lines[i][1][1:].strip()
        if not rest:
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                item, i = _parse_block(lines, i, lines[i][0])
            else:
                item = None
            result.append(item)
        elif _is_map_entry(rest):
            sub: list[tuple[int, str]] = [(indent + 2, rest)]
            i += 1
            while i < len(lines) and lines[i][0] > indent:
                sub.append(lines[i])
                i += 1
            item, _ = _parse_map(sub, 0, indent + 2)
            result.append(item)
        else:
            result.append(_parse_scalar(rest))
            i += 1
    return result, i


def _is_map_entry(text: str) -> bool:
    key, sep, rest = text.partition(":")
    if not sep or not _KEY_RE.match(key.strip()):
        return False
    if rest.startswith("//"):
        return False
    return rest == "" or rest.startswith(" ") or rest.startswith("{") or rest.startswith("[")


# --------------------------------------------------------------------------- #
# 标量
# --------------------------------------------------------------------------- #

def _parse_scalar(text: str) -> Any:
    text = text.strip()
    if text.startswith('"'):
        return _parse_double_quoted(text)
    if text.startswith("'"):
        if not text.endswith("'") or len(text) < 2:
            raise MiniYamlError(f"单引号字符串未闭合：{text!r}")
        return text[1:-1].replace("''", "'")
    if text.startswith("["):
        return _parse_inline_list(text)
    if text.startswith("{"):
        return _parse_inline_map(text)
    low = text.lower()
    if low in _BOOLS:
        return _BOOLS[low]
    if low in _NULLS:
        return None
    if _INT_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return text


def _parse_double_quoted(text: str) -> str:
    if len(text) < 2 or not text.endswith('"'):
        raise MiniYamlError(f"双引号字符串未闭合：{text!r}")
    body = text[1:-1]
    out: list[str] = []
    i = 0
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(escapes.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    current: list[str] = []
    for ch in text:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
        elif ch in "[{":
            depth += 1
            current.append(ch)
        elif ch in "]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def _parse_inline_list(text: str) -> list[Any]:
    if not text.endswith("]"):
        raise MiniYamlError(f"行内列表未闭合：{text!r}")
    return [_parse_scalar(part) for part in _split_top_level(text[1:-1])]


def _parse_inline_map(text: str) -> dict[str, Any]:
    if not text.endswith("}"):
        raise MiniYamlError(f"行内映射未闭合：{text!r}")
    result: dict[str, Any] = {}
    for part in _split_top_level(text[1:-1]):
        key, sep, value = part.partition(":")
        if not sep:
            raise MiniYamlError(f"行内映射缺少冒号：{part!r}")
        result[_unquote(key.strip())] = _parse_scalar(value.strip()) if value.strip() else None
    return result


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return _parse_double_quoted(text) if text[0] == '"' else text[1:-1]
    return text


# --------------------------------------------------------------------------- #
# 写出
# --------------------------------------------------------------------------- #

def dumps(data: Any) -> str:
    return "\n".join(_dump_block(data, 0)) + "\n"


def dump(data: Any, path) -> None:
    path = str(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(dumps(data))


def _dump_block(value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return [pad + "{}"]
        lines: list[str] = []
        for key, item in value.items():
            lines.extend(_dump_key(key, item, indent))
        return lines
    if isinstance(value, list):
        if not value:
            return [pad + "[]"]
        lines = []
        for item in value:
            lines.extend(_dump_item(item, indent))
        return lines
    return [pad + _format_scalar(value)]


def _dump_key(key: str, value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return [f"{pad}{key}: {{}}"]
        return [f"{pad}{key}:"] + _dump_block(value, indent + 2)
    if isinstance(value, list):
        if not value:
            return [f"{pad}{key}: []"]
        return [f"{pad}{key}:"] + _dump_block(value, indent + 2)
    return [f"{pad}{key}: {_format_scalar(value)}"]


def _dump_item(value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return [pad + "- {}"]
        inner = _dump_block(value, indent + 2)
        first = inner[0].strip()
        rest = inner[1:]
        return [f"{pad}- {first}"] + rest
    if isinstance(value, list):
        if not value:
            return [pad + "- []"]
        inner = _dump_block(value, indent + 2)
        return [pad + "-"] + inner
    return [f"{pad}- {_format_scalar(value)}"]


_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-/ ]*$")


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    if text and _PLAIN_SAFE.match(text):
        low = text.lower()
        if low not in _BOOLS and low not in _NULLS and not _INT_RE.match(text) and not _FLOAT_RE.match(text):
            return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
