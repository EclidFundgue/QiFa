#!/usr/bin/env python3
"""从工作区 plan/script/素材生成课程站点（拷贝模板、生成数据、写入启动脚本）。

不负责 npm 构建（默认）；`--npm-build` 会尝试 npm install + npm run build。
涉及文件：
  presentation/                 <- assets/web-template
  presentation/src/content/course.json / narrations.json
  presentation/src/styles/tokens.css
  presentation/public/media/*
  start.sh / start.command / start.bat
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, paths  # noqa: E402
from lib.workbench import Workspace, problem  # noqa: E402

STAGE = "web-generation"

START_SH = """#!/usr/bin/env bash
# QiFa 课程启动脚本（Linux / macOS 终端：bash start.sh）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/presentation"
if ! command -v node >/dev/null 2>&1; then
  echo "需要 Node >= 18：https://nodejs.org/" >&2
  exit 1
fi
MAJOR="$(node -p "process.versions.node.split('.')[0]")"
if [ "$MAJOR" -lt 18 ]; then
  echo "Node 版本过低（当前 $(node -v)），需要 >= 18" >&2
  exit 1
fi
[ -d node_modules ] || npm install
exec npm run dev -- --open
"""

START_BAT = (
    "@echo off\r\n"
    "rem QiFa 课程启动脚本（Windows 双击运行）\r\n"
    "setlocal\r\n"
    "cd /d \"%~dp0presentation\"\r\n"
    "where node >nul 2>nul || (echo 需要 Node ^>= 18：https://nodejs.org/ & pause & exit /b 1)\r\n"
    "for /f \"delims=\" %%v in ('node -p \"process.versions.node.split('.')[0]\"') do set MAJOR=%%v\r\n"
    "if %MAJOR% LSS 18 (echo Node 版本过低，需要 ^>= 18 & pause & exit /b 1)\r\n"
    "if not exist node_modules (call npm install)\r\n"
    "call npm run dev -- --open\r\n"
    "pause\r\n"
)

ANCHOR_RE = re.compile(r"^##\s+(S\d+)\b.*$", re.MULTILINE)


def build(ws: Workspace, npm_build: bool = False) -> list[dict]:
    problems: list[dict] = []
    template = paths.skill_dir() / "assets" / "web-template"
    if not template.is_dir():
        return [problem("web", "WEB-TEMPLATE", "blocker", STAGE, "assets/web-template", "缺少站点模板")]

    presentation = ws.root / "presentation"
    custom_dir = presentation / "src" / "content" / "custom"

    def _ignore(directory: str, names: list[str]) -> list[str]:
        # 已生成的定制组件属于 Agent 的产物，重复 build 不得覆盖。
        if custom_dir.is_dir() and Path(directory) == template / "src" / "content":
            return ["custom"]
        return []

    shutil.copytree(template, presentation, dirs_exist_ok=True, ignore=_ignore)

    project = ws.load_project() or {}
    outline = ws.load_outline()
    if outline is None:
        problems.append(problem("web", "WEB-OUTLINE", "blocker", STAGE, "plan/course-outline.json", "缺少课程大纲"))
        return problems

    plan_by_chapter = {}
    for path, data in ws.load_chapter_plans():
        if data is None:
            problems.append(problem("web", "WEB-PLAN", "blocker", STAGE, ws.rel(path), "章节计划无法解析"))
            continue
        plan_by_chapter[str(data.get("chapter_id"))] = data

    scripts = ws.load_scripts()
    visual = ws.load_visual_plan() or {"items": []}
    visuals_by_slide: dict[str, list] = {}
    for item in visual.get("items") or []:
        visuals_by_slide.setdefault(str(item.get("slide_id")), []).append(item)

    theme_id = str(project.get("visual_style") or "scientific-editorial")
    theme_dir = paths.skill_dir() / "assets" / "themes" / theme_id
    if not (theme_dir / "tokens.css").is_file():
        problems.append(problem("web", "WEB-THEME", "blocker", STAGE, theme_id, f"主题不存在：{theme_id}"))
    else:
        target = presentation / "src" / "styles" / "tokens.css"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(theme_dir / "tokens.css", target)

    source_model = ws.load_source_model() or {"glossary": []}
    media_public = presentation / "public" / "media"
    media_public.mkdir(parents=True, exist_ok=True)

    chapters_out = []
    narrations: dict[str, dict[str, str]] = {}
    for chapter in outline.get("chapters") or []:
        chapter_id = str(chapter.get("id"))
        plan = plan_by_chapter.get(chapter_id)
        if plan is None:
            problems.append(problem("web", "WEB-PLAN", "blocker", STAGE, chapter_id, f"缺少章节计划：{chapter_id}"))
            continue
        script_blocks = _script_blocks(scripts.get(chapter_id, {}).get("text", ""))
        chapter_narrations: dict[str, str] = {}
        slides_out = []
        for slide in plan.get("slides") or []:
            slide_id = str(slide.get("id"))
            narration = script_blocks.get(slide_id, "").strip()
            chapter_narrations[slide_id] = narration
            visuals_out = []
            media_refs = []
            for item in visuals_by_slide.get(slide_id, []):
                asset = str(item.get("asset") or "")
                asset_rel = _copy_media(ws, asset, media_public)
                if asset and asset_rel is None and ("/" in asset or "." in asset):
                    problems.append(
                        problem("web", "WEB-ASSET", "blocker", STAGE, f"{chapter_id}/{slide_id}", f"素材无法复制：{asset}")
                    )
                visuals_out.append(
                    {
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "purpose": item.get("purpose"),
                        "asset": asset_rel or "",
                        "refs": _refs(item.get("source_refs") or []),
                    }
                )
                if asset_rel and item.get("type") in ("video", "image"):
                    media_refs.append(asset_rel)
            slides_out.append(
                {
                    "id": slide_id,
                    "title": slide.get("title"),
                    "kind": slide.get("kind"),
                    "points": [
                        {
                            "text": point.get("text"),
                            "step_id": point.get("step_id") or "",
                            "refs": _refs(point.get("source_refs") or []),
                        }
                        for point in slide.get("points") or []
                    ],
                    "steps": [
                        {"id": step.get("id"), "label": step.get("label")} for step in slide.get("steps") or []
                    ],
                    "visuals": visuals_out,
                    "media_refs": media_refs,
                    "narration": narration,
                    "custom": f"./custom/{slide_id}.tsx",
                }
            )
        narrations[chapter_id] = chapter_narrations
        chapters_out.append(
            {
                "id": chapter_id,
                "title": chapter.get("title"),
                "goal": chapter.get("goal"),
                "slides": slides_out,
            }
        )

    course = {
        "course": {
            "title": (outline.get("course") or {}).get("title"),
            "language": (outline.get("course") or {}).get("language"),
            "audience": (outline.get("course") or {}).get("audience"),
            "goal": (outline.get("course") or {}).get("goal"),
            "theme": theme_id,
            "duration_minutes": ((project.get("duration") or {}).get("target_minutes")),
        },
        "glossary": source_model.get("glossary") or [],
        "chapters": chapters_out,
        "has_degradations": bool(_degradations(ws)),
    }
    io.dump_json(presentation / "src" / "content" / "course.json", course)
    io.dump_json(presentation / "src" / "content" / "narrations.json", narrations)

    _write_start_scripts(ws)

    if npm_build:
        problems.extend(_run_npm(presentation))
    return problems


def _refs(refs: list) -> list[dict]:
    return [
        {"kind": ref.get("kind"), "locator": ref.get("locator"), "source_id": ref.get("source_id")}
        for ref in refs
    ]


def _script_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    matches = list(ANCHOR_RE.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.end():end]
    return blocks


def _copy_media(ws: Workspace, asset: str, media_public: Path) -> str | None:
    if not asset:
        return None
    candidates = [
        ws.root / asset,
        ws.root / "source" / "media" / Path(asset).name,
        ws.root / "source" / Path(asset).name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            target = media_public / candidate.name
            shutil.copyfile(candidate, target)
            return f"media/{candidate.name}"
    return None


def _degradations(ws: Workspace) -> list[dict]:
    state = ws.load_run_state() or {}
    result: list[dict] = []
    for entry in (state.get("stages") or {}).values():
        result.extend(entry.get("degradations") or [])
    return result


def _write_start_scripts(ws: Workspace) -> None:
    sh_path = ws.root / "start.sh"
    sh_path.write_text(START_SH, encoding="utf-8")
    sh_path.chmod(0o755)
    command_path = ws.root / "start.command"
    command_path.write_text(START_SH, encoding="utf-8")
    command_path.chmod(0o755)
    (ws.root / "start.bat").write_text(START_BAT, encoding="utf-8", newline="")


def _run_npm(presentation: Path) -> list[dict]:
    problems: list[dict] = []
    npm = shutil.which("npm")
    if npm is None:
        return [problem("web", "WEB-NPM", "blocker", STAGE, "npm", "找不到 npm，无法构建（需要 Node >= 18）")]
    try:
        if not (presentation / "node_modules").is_dir():
            install = subprocess.run(
                [npm, "install", "--no-audit", "--no-fund"],
                cwd=presentation,
                capture_output=True,
                text=True,
                timeout=900,
            )
            if install.returncode != 0:
                return [
                    problem(
                        "web",
                        "WEB-NPM",
                        "blocker",
                        STAGE,
                        "npm install",
                        (install.stderr or install.stdout or "").strip()[-300:] or "npm install 失败",
                    )
                ]
        build = subprocess.run(
            [npm, "run", "build"], cwd=presentation, capture_output=True, text=True, timeout=900
        )
        if build.returncode != 0:
            problems.append(
                problem(
                    "web",
                    "WEB-BUILD",
                    "blocker",
                    STAGE,
                    "npm run build",
                    (build.stderr or build.stdout or "").strip()[-300:] or "npm run build 失败",
                )
            )
    except Exception as exc:  # noqa: BLE001
        problems.append(problem("web", "WEB-BUILD", "blocker", STAGE, "npm", f"{type(exc).__name__}: {exc}"))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="生成课程站点数据与启动脚本")
    parser.add_argument("workspace")
    parser.add_argument("--npm-build", action="store_true", help="同时运行 npm install && npm run build")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problems = build(Workspace(args.workspace), npm_build=args.npm_build)
    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        for item in problems:
            print(f"[{item['severity']}] {item['rule_id']} {item['target']}: {item['message']}")
        print(f"{len(problems)} 个问题（{sum(1 for p in problems if p['severity'] == 'blocker')} 个 blocker）")
    return 1 if any(item["severity"] == "blocker" for item in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
