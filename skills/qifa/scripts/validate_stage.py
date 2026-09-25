#!/usr/bin/env python3
"""阶段结构校验：文件齐全 + schema 通过 + run-state 完整性。

用法：python3 validate_stage.py <workspace> --stage <stage> [--json]
作为库：from validate_stage import check; check(Workspace, "curriculum")
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io  # noqa: E402
from lib.workbench import STAGES, Workspace, problem  # noqa: E402

# stage -> 该阶段结束时应存在的文件（相对工作区）
STAGE_FILES: dict[str, list[str]] = {
    "intake": ["project.yaml", ".qifa/run-state.yaml", "00-intake.md", "source"],
    "source-analysis": ["source/source-model.json"],
    "curriculum": ["plan/course-outline.json"],
    "chapter-design": ["plan/chapter-plan-C01.json"],
    "narrative": ["script/01-C01.md"],
    "visual-storyboard": ["plan/visual-plan.json"],
    "web-generation": ["presentation/package.json", "presentation/src/content/course.json"],
    "automated-review": ["review/qa-report.json"],
    "package": ["README-learner.md", "start.sh", "start.command", "start.bat"],
}

SCHEMA_FILES: dict[str, str] = {
    "project.yaml": "project",
    ".qifa/run-state.yaml": "run-state",
    "source/source-model.json": "source-model",
    "plan/course-outline.json": "course-outline",
    "plan/visual-plan.json": "visual-plan",
    "review/qa-report.json": "qa-report",
}


def check(ws: Workspace, stage: str) -> list[dict]:
    problems: list[dict] = []
    if stage not in STAGES:
        return [problem("structure", "STRUCT-STAGE", "blocker", stage, stage, f"未知阶段 {stage}")]

    # 1) 到该阶段为止的所有文件要求
    index = STAGES.index(stage)
    for required_stage in STAGES[: index + 1]:
        for rel in STAGE_FILES.get(required_stage, []):
            if rel.endswith(".json") and rel == "plan/chapter-plan-C01.json":
                if not ws.chapter_plan_paths():
                    problems.append(
                        problem(
                            "structure",
                            "STRUCT-FILE",
                            "blocker",
                            stage,
                            rel,
                            "缺少章节计划文件 plan/chapter-plan-C*.json",
                            "按 chapter-design.md 生成章节计划",
                        )
                    )
                continue
            if rel == "script/01-C01.md":
                if not ws.script_paths():
                    problems.append(
                        problem(
                            "structure",
                            "STRUCT-FILE",
                            "blocker",
                            stage,
                            rel,
                            "缺少讲稿文件 script/NN-CXX.md",
                            "按 narrative-design.md 生成讲稿",
                        )
                    )
                continue
            if not ws.exists(*rel.split("/")):
                problems.append(
                    problem("structure", "STRUCT-FILE", "blocker", stage, rel, f"缺少必需文件 {rel}")
                )

    # 2) schema 校验（存在的文件）
    for rel, schema_name in SCHEMA_FILES.items():
        path = ws.root / rel
        if not path.is_file():
            continue
        data = ws.load_run_state() if schema_name == "run-state" else None
        if data is None:
            try:
                data = io.load_yaml(path) if path.suffix == ".yaml" else io.load_json(path)
            except Exception as exc:  # noqa: BLE001
                problems.append(
                    problem("structure", "STRUCT-PARSE", "blocker", stage, rel, f"无法解析：{exc}")
                )
                continue
        for err in io.validate_against_schema(data, schema_name):
            problems.append(
                problem("structure", "STRUCT-SCHEMA", "blocker", stage, rel, err, f"修正 {rel} 以符合 {schema_name}.schema.json")
            )

    for path, data in ws.load_chapter_plans():
        if data is None:
            problems.append(
                problem("structure", "STRUCT-PARSE", "blocker", stage, ws.rel(path), "无法解析章节计划")
            )
            continue
        for err in io.validate_against_schema(data, "chapter-plan"):
            problems.append(
                problem("structure", "STRUCT-SCHEMA", "blocker", stage, ws.rel(path), err)
            )

    # 3) run-state 完整性
    state = ws.load_run_state()
    if state is not None:
        if state.get("stage") not in STAGES:
            problems.append(
                problem("structure", "STRUCT-STATE", "blocker", stage, ".qifa/run-state.yaml", "stage 取值非法")
            )
        stages = state.get("stages") or {}
        missing = [name for name in STAGES if name not in stages]
        if missing:
            problems.append(
                problem(
                    "structure",
                    "STRUCT-STATE",
                    "blocker",
                    stage,
                    ".qifa/run-state.yaml",
                    f"stages 缺少条目：{', '.join(missing)}",
                )
            )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="校验工作区在指定阶段的结构完整性")
    parser.add_argument("workspace")
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problems = check(Workspace(args.workspace), args.stage)
    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        for item in problems:
            print(f"[{item['severity']}] {item['rule_id']} {item['target']}: {item['message']}")
        print(f"{len(problems)} 个问题（{sum(1 for p in problems if p['severity'] == 'blocker')} 个 blocker）")
    return 1 if any(item["severity"] == "blocker" for item in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
