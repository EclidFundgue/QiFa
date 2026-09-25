"""平台路径解析：配置目录、缓存目录、venv、工作区默认位置。

规范（与 README 一致）：
  Windows  %APPDATA%\\qifa\\config.yaml        %LOCALAPPDATA%\\qifa\\venv
  macOS    ~/Library/Application Support/qifa/config.yaml   ~/Library/Caches/qifa/venv
  Linux    $XDG_CONFIG_HOME/qifa/config.yaml（默认 ~/.config）  $XDG_CACHE_HOME/qifa/venv（默认 ~/.cache）
可用 QIFA_CONFIG / QIFA_VENV 覆盖。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"


def skill_dir() -> Path:
    """skills/qifa/ 目录（本文件位于 skills/qifa/scripts/lib/）。"""
    return Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """仓库根（skills/qifa/scripts/lib -> 上溯 4 层）；用于定位 tests/ 与 .venv。"""
    return Path(__file__).resolve().parents[4]


def config_file() -> Path:
    override = os.environ.get("QIFA_CONFIG")
    if override:
        return Path(override).expanduser()
    return config_dir() / "config.yaml"


def config_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif IS_MACOS:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "qifa"


def cache_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
    elif IS_MACOS:
        base = Path.home() / "Library" / "Caches"
    else:
        base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(base) / "qifa"


def venv_dir() -> Path:
    """依赖 venv：QIFA_VENV -> 仓库 .venv（开发时存在则用）-> 平台缓存目录。"""
    override = os.environ.get("QIFA_VENV")
    if override:
        return Path(override).expanduser()
    repo_venv = repo_root() / ".venv"
    if repo_venv.is_dir():
        return repo_venv
    return cache_dir() / "venv"


def venv_python(venv: Path | None = None) -> Path:
    base = venv or venv_dir()
    if IS_WINDOWS:
        return base / "Scripts" / "python.exe"
    return base / "bin" / "python"


def default_output() -> Path:
    return Path.cwd() / "qifa-output"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "course") -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or fallback
