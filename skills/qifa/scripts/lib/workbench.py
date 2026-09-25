"""工作区读取与问题对象（所有校验器共享）。"""

from __future__ import annotations

import glob
import re
from pathlib import Path
from typing import Any, Iterable

from . import io

STAGES = [
    "intake",
    "source-analysis",
    "curriculum",
    "chapter-design",
    "narrative",
    "visual-storyboard",
    "web-generation",
    "automated-review",
    "package",
]

SEVERITIES = ("blocker", "warning", "info")

DEFAULT_SPEAKING_RATE = {"zh_chars_per_minute": 240, "en_words_per_minute": 130}

ANCHOR_RE = re.compile(r"^##\s+(S\d+)\b", re.MULTILINE)
CHAPTER_ID_RE = re.compile(r"C\d+")
CODE_LOCATOR_RE = re.compile(r"^(.+?):([A-Za-z_][\w.]*)$")


def problem(
    layer: str,
    rule_id: str,
    severity: str,
    stage: str,
    target: str,
    message: str,
    remediation: str = "",
) -> dict:
    return {
        "layer": layer,
        "rule_id": rule_id,
        "severity": severity,
        "stage": stage,
        "target": target,
        "message": message,
        "remediation": remediation,
        "status": "open",
    }


def blockers(problems: Iterable[dict]) -> list[dict]:
    return [item for item in problems if item["severity"] == "blocker"]


def warnings(problems: Iterable[dict]) -> list[dict]:
    return [item for item in problems if item["severity"] == "warning"]


# --------------------------------------------------------------------------- #
# 工作区读取
# --------------------------------------------------------------------------- #

class Workspace:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def rel(self, path: Path | str) -> str:
        try:
            return str(Path(path).resolve().relative_to(self.root))
        except ValueError:
            return str(path)

    def exists(self, *parts: str) -> bool:
        return (self.root.joinpath(*parts)).exists()

    # -- 已知文件 ---------------------------------------------------------- #
    @property
    def project_path(self) -> Path:
        return self.root / "project.yaml"

    @property
    def run_state_path(self) -> Path:
        return self.root / ".qifa" / "run-state.yaml"

    @property
    def source_model_path(self) -> Path:
        return self.root / "source" / "source-model.json"

    @property
    def outline_path(self) -> Path:
        return self.root / "plan" / "course-outline.json"

    @property
    def visual_plan_path(self) -> Path:
        return self.root / "plan" / "visual-plan.json"

    @property
    def qa_report_path(self) -> Path:
        return self.root / "review" / "qa-report.json"

    def chapter_plan_paths(self) -> list[Path]:
        return sorted(Path(p) for p in glob.glob(str(self.root / "plan" / "chapter-plan-C*.json")))

    def script_paths(self) -> list[Path]:
        return sorted(Path(p) for p in glob.glob(str(self.root / "script" / "*.md")))

    # -- 读取 -------------------------------------------------------------- #
    def load_project(self) -> dict | None:
        if not self.project_path.is_file():
            return None
        try:
            data = io.load_yaml(self.project_path)
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001 - 校验器负责报告
            return None

    def load_run_state(self) -> dict | None:
        if not self.run_state_path.is_file():
            return None
        try:
            data = io.load_yaml(self.run_state_path)
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001
            return None

    def load_source_model(self) -> dict | None:
        return _load_json(self.source_model_path)

    def load_outline(self) -> dict | None:
        return _load_json(self.outline_path)

    def load_visual_plan(self) -> dict | None:
        return _load_json(self.visual_plan_path)

    def load_chapter_plans(self) -> list[tuple[Path, dict | None]]:
        return [(path, _load_json(path)) for path in self.chapter_plan_paths()]

    def load_scripts(self) -> dict[str, dict]:
        """chapter_id -> {path, anchors, text}，文件名约定 script/NN-CXX.md。"""
        result: dict[str, dict] = {}
        for path in self.script_paths():
            match = CHAPTER_ID_RE.search(path.stem)
            if not match:
                continue
            text = path.read_text(encoding="utf-8")
            result[match.group(0)] = {
                "path": path,
                "anchors": ANCHOR_RE.findall(text),
                "text": text,
            }
        return result

    def speaking_rate(self) -> dict:
        project = self.load_project() or {}
        rate = project.get("speaking_rate")
        if isinstance(rate, dict):
            merged = dict(DEFAULT_SPEAKING_RATE)
            merged.update({k: v for k, v in rate.items() if isinstance(v, (int, float))})
            return merged
        return dict(DEFAULT_SPEAKING_RATE)


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = io.load_json(path)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# 引用遍历
# --------------------------------------------------------------------------- #

def iter_source_refs(data: Any) -> Iterable[dict]:
    """递归找出所有形如 {source_id, kind, locator} 的引用。"""
    if isinstance(data, dict):
        if {"source_id", "kind", "locator"} <= set(data.keys()):
            yield data
            return
        for value in data.values():
            yield from iter_source_refs(value)
    elif isinstance(data, list):
        for value in data:
            yield from iter_source_refs(value)


def strip_code_locator(locator: str) -> str:
    """`path/to/file.py:func` -> `path/to/file.py`；无冒号则原样返回。"""
    match = CODE_LOCATOR_RE.match(locator)
    if match and "/" in match.group(1):
        return match.group(1)
    return locator.split(":", 1)[0]
