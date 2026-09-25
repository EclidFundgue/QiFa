"""Python 依赖自举（可选增强）。

QiFa 的所有脚本在纯标准库下即可运行（内置最小 YAML 与 JSON Schema 实现），
这是**默认路径**：脚本始终在调用方解释器下运行，本模块创建的 venv 不会自动
接管后续命令。若需要完整 jsonschema 语义，需先激活该 venv、再用其 python
运行 pipeline.py。失败不阻塞：返回 failed 状态，由调用方写入报告。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from . import paths

PACKAGES = ("pyyaml", "jsonschema")


def deps_available() -> bool:
    return all(importlib.util.find_spec(name) is not None for name in PACKAGES)


def ensure(no_install: bool = False, timeout: int = 180) -> dict:
    """返回 {status, detail, python}；status ∈ current|skipped|created|failed。"""
    if deps_available():
        return {"status": "current", "detail": "当前解释器已具备 pyyaml 与 jsonschema", "python": sys.executable}
    if no_install:
        return {"status": "skipped", "detail": "--no-install：使用内置最小实现", "python": None}

    venv = paths.venv_dir()
    python = paths.venv_python(venv)
    try:
        if not python.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv)],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        result = subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-q", *PACKAGES],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return {
                "status": "failed",
                "detail": (result.stderr or result.stdout or "").strip()[-500:] or "pip install 失败",
                "python": str(python),
            }
        return {
            "status": "created",
            "detail": (
                f"已安装 {', '.join(PACKAGES)} 到 {venv}（可选环境；"
                f"需激活后重新运行 pipeline.py 才生效，默认仍用调用方解释器与内置实现）"
            ),
            "python": str(python),
        }
    except Exception as exc:  # noqa: BLE001 - 降级路径必须吞掉所有失败
        return {"status": "failed", "detail": f"{type(exc).__name__}: {exc}", "python": str(python)}
