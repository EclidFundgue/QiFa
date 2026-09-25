#!/usr/bin/env python3
"""课程校验：目标覆盖、章节/页面结构、讲稿锚点、视觉登记、时长与术语一致性。

用法：python3 validate_course.py <workspace> [--stage <stage>] [--json]
作为库：from validate_course import check; check(Workspace, stage="curriculum")
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.workbench import STAGES, Workspace, problem  # noqa: E402
from estimate_duration import estimate  # noqa: E402

DEEP_STAGES = {"narrative", "visual-storyboard", "web-generation", "automated-review", "package"}


def check(ws: Workspace, stage: str = "curriculum") -> list[dict]:
    problems: list[dict] = []
    outline = ws.load_outline()
    if outline is None:
        return []

    objective_ids = _check_objectives(outline, problems)
    chapter_ids = _check_chapters(outline, objective_ids, problems)
    plans = _check_chapter_plans(ws, outline, chapter_ids, stage, problems)
    _check_scripts(ws, plans, stage, problems)
    slide_ids = _all_slide_ids(plans)
    _check_visual_plan(ws, slide_ids, problems)
    _check_glossary(ws, problems)
    _check_duration(ws, outline, problems)
    return problems


def _check_objectives(outline: dict, problems: list[dict]) -> set[str]:
    ids: set[str] = set()
    for index, objective in enumerate(outline.get("objectives") or []):
        target = f"objectives[{index}]"
        obj_id = str(objective.get("id", ""))
        if obj_id in ids:
            problems.append(problem("pedagogy", "PED-OBJ-DUP", "blocker", "curriculum", target, f"目标 id 重复：{obj_id}"))
        ids.add(obj_id)
        if not (objective.get("chapter_ids") or []):
            problems.append(
                problem("pedagogy", "PED-OBJ-COVER", "blocker", "curriculum", target, f"目标 {obj_id} 没有任何章节承接")
            )
    return ids


def _check_chapters(outline: dict, objective_ids: set[str], problems: list[dict]) -> set[str]:
    ids: set[str] = set()
    for index, chapter in enumerate(outline.get("chapters") or []):
        target = f"chapters[{index}]"
        chapter_id = str(chapter.get("id", ""))
        if chapter_id in ids:
            problems.append(problem("chapter", "CHAP-DUP", "blocker", "curriculum", target, f"章节 id 重复：{chapter_id}"))
        ids.add(chapter_id)
        if not (chapter.get("objective_ids") or []):
            problems.append(
                problem("chapter", "CHAP-OBJ", "blocker", "curriculum", target, f"章节 {chapter_id} 未承接任何目标")
            )
        for obj_id in chapter.get("objective_ids") or []:
            if obj_id not in objective_ids:
                problems.append(
                    problem("chapter", "CHAP-OBJ", "blocker", "curriculum", target, f"引用了不存在的目标：{obj_id}")
                )
        slides = chapter.get("slides") or []
        if not slides:
            problems.append(problem("chapter", "CHAP-SLIDES", "blocker", "curriculum", target, f"章节 {chapter_id} 没有页面"))
    for index, objective in enumerate(outline.get("objectives") or []):
        for chapter_id in objective.get("chapter_ids") or []:
            if chapter_id not in ids:
                problems.append(
                    problem(
                        "pedagogy",
                        "PED-OBJ-COVER",
                        "blocker",
                        "curriculum",
                        f"objectives[{index}]",
                        f"目标引用了不存在的章节：{chapter_id}",
                    )
                )
    return ids


def _check_chapter_plans(
    ws: Workspace, outline: dict, chapter_ids: set[str], stage: str, problems: list[dict]
) -> dict[str, dict]:
    plans: dict[str, dict] = {}
    for path, data in ws.load_chapter_plans():
        if data is None:
            problems.append(problem("structure", "CHAP-PARSE", "blocker", stage, ws.rel(path), "无法解析章节计划"))
            continue
        chapter_id = str(data.get("chapter_id", ""))
        plans[chapter_id] = data
        if chapter_id not in chapter_ids:
            problems.append(
                problem("chapter", "CHAP-UNKNOWN", "blocker", stage, ws.rel(path), f"章节计划引用了不存在的章节：{chapter_id}")
            )

    outline_slides = {
        str(chapter.get("id")): [str(slide.get("id")) for slide in chapter.get("slides") or []]
        for chapter in outline.get("chapters") or []
    }
    for chapter_id, expected in outline_slides.items():
        if chapter_id not in plans:
            severity = "blocker" if stage in DEEP_STAGES else "warning"
            problems.append(
                problem("chapter", "CHAP-MISSING", severity, stage, chapter_id, f"缺少章节计划：{chapter_id}")
            )
            continue
        actual = [str(slide.get("id")) for slide in plans[chapter_id].get("slides") or []]
        if actual != expected:
            problems.append(
                problem(
                    "chapter",
                    "CHAP-SLIDES",
                    "blocker",
                    stage,
                    chapter_id,
                    f"章节计划页面与大纲不一致：大纲 {expected}，计划 {actual}",
                )
            )
        for slide in plans[chapter_id].get("slides") or []:
            points = slide.get("points") or []
            if not points:
                problems.append(
                    problem("chapter", "CHAP-EMPTY", "warning", stage, f"{chapter_id}/{slide.get('id')}", "页面没有讲点")
                )
            if slide.get("kind") == "code-walkthrough" and not any(p.get("source_refs") for p in points):
                problems.append(
                    problem(
                        "chapter",
                        "CHAP-CODE",
                        "warning",
                        stage,
                        f"{chapter_id}/{slide.get('id')}",
                        "代码走读页没有代码引用",
                    )
                )
    return plans


def _check_scripts(ws: Workspace, plans: dict[str, dict], stage: str, problems: list[dict]) -> None:
    scripts = ws.load_scripts()
    for chapter_id, plan in plans.items():
        if chapter_id not in scripts:
            if stage in DEEP_STAGES:
                problems.append(
                    problem("narrative", "NARR-MISSING", "blocker", stage, chapter_id, f"缺少讲稿：script/*-{chapter_id}.md")
                )
            continue
        script = scripts[chapter_id]
        expected = [str(slide.get("id")) for slide in plan.get("slides") or []]
        if script["anchors"] != expected:
            problems.append(
                problem(
                    "narrative",
                    "NARR-ANCHORS",
                    "blocker",
                    stage,
                    ws.rel(script["path"]),
                    f"讲稿锚点与页面不一致：讲稿 {script['anchors']}，计划 {expected}",
                )
            )
        blocks = _split_script_blocks(script["text"])
        for slide_id in expected:
            if not blocks.get(slide_id, "").strip():
                problems.append(
                    problem(
                        "narrative",
                        "NARR-EMPTY",
                        "warning",
                        stage,
                        f"{ws.rel(script['path'])}:{slide_id}",
                        "该页讲稿为空",
                    )
                )


def _split_script_blocks(text: str) -> dict[str, str]:
    import re

    blocks: dict[str, str] = {}
    matches = list(re.finditer(r"^##\s+(S\d+)\b.*$", text, re.MULTILINE))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.end():end]
    return blocks


def _all_slide_ids(plans: dict[str, dict]) -> set[str]:
    ids: set[str] = set()
    for plan in plans.values():
        for slide in plan.get("slides") or []:
            ids.add(str(slide.get("id")))
    return ids


def _check_visual_plan(ws: Workspace, slide_ids: set[str], problems: list[dict]) -> None:
    visual = ws.load_visual_plan()
    if visual is None:
        return
    for index, item in enumerate(visual.get("items") or []):
        target = f"visual-plan.items[{index}]"
        slide_id = str(item.get("slide_id", ""))
        if slide_id not in slide_ids:
            problems.append(
                problem("visual", "VIS-SLIDE", "blocker", "visual-storyboard", target, f"登记了不存在的页面：{slide_id}")
            )
        if not str(item.get("purpose", "")).strip():
            problems.append(
                problem("visual", "VIS-PURPOSE", "blocker", "visual-storyboard", target, "缺失教学目的")
            )
        asset = str(item.get("asset", "")).strip()
        if asset and ("/" in asset or "." in asset):
            candidates = [
                ws.root / asset,
                ws.root / "source" / "media" / Path(asset).name,
                ws.root / "presentation" / "public" / asset.lstrip("/"),
            ]
            if not any(path.exists() for path in candidates):
                problems.append(
                    problem(
                        "visual",
                        "VIS-ASSET",
                        "blocker",
                        "visual-storyboard",
                        target,
                        f"素材不存在：{asset}",
                        "把素材放到 source/media/ 并更新 visual-plan",
                    )
                )


def _check_glossary(ws: Workspace, problems: list[dict]) -> None:
    model = ws.load_source_model()
    if not model:
        return
    glossary = model.get("glossary") or []
    if not glossary:
        return
    text = "\n".join(script["text"] for script in ws.load_scripts().values())
    for index, entry in enumerate(glossary):
        term = str(entry.get("term", ""))
        if term and text and term not in text and str(entry.get("translation", "")) not in text:
            problems.append(
                problem("narrative", "NARR-GLOSSARY", "info", "narrative", f"glossary[{index}]", f"术语未在讲稿中出现：{term}")
            )


def _check_duration(ws: Workspace, outline: dict, problems: list[dict]) -> None:
    result = estimate(ws)
    declared_total = float(outline.get("duration_estimate") or 0)
    if declared_total and result["total"] and abs(declared_total - result["total"]) > 1.5:
        problems.append(
            problem(
                "pedagogy",
                "PED-DURATION",
                "warning",
                "narrative",
                "plan/course-outline.json",
                f"大纲声明 {declared_total:.0f} 分钟，讲稿换算 {result['total']:.0f} 分钟，差异超过 1.5 分钟",
                "按讲稿重算每章 duration_estimate",
            )
        )
    project = ws.load_project() or {}
    target = ((project.get("duration") or {}).get("target_minutes")) or 0
    tolerance = ((project.get("policies") or {}).get("duration_tolerance")) or 0.3
    if target and result["total"]:
        deviation = abs(result["total"] - float(target)) / float(target)
        if deviation > float(tolerance):
            problems.append(
                problem(
                    "pedagogy",
                    "PED-DURATION",
                    "warning",
                    "narrative",
                    "script/",
                    f"讲稿换算 {result['total']:.0f} 分钟，目标 {target} 分钟，偏差 {deviation:.0%} 超过容差 {float(tolerance):.0%}",
                )
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="校验课程结构、讲稿与视觉登记")
    parser.add_argument("workspace")
    parser.add_argument("--stage", default="curriculum", choices=STAGES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problems = check(Workspace(args.workspace), stage=args.stage)
    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        for item in problems:
            print(f"[{item['severity']}] {item['rule_id']} {item['target']}: {item['message']}")
        print(f"{len(problems)} 个问题（{sum(1 for p in problems if p['severity'] == 'blocker')} 个 blocker）")
    return 1 if any(item["severity"] == "blocker" for item in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
