#!/usr/bin/env python3
"""站点检查：构建产物、资源与链接、离线可用性、无障碍基线。

用法：python3 check_site.py <workspace> [--no-build-check] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io  # noqa: E402
from lib.workbench import Workspace, problem  # noqa: E402

STAGE = "web-generation"
ATTR_RE = re.compile(r'(?:src|href)\s*=\s*"([^"]+)"')
IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s\"')]+")


def check(ws: Workspace, require_build: bool = True) -> list[dict]:
    problems: list[dict] = []
    presentation = ws.root / "presentation"
    if not (presentation / "package.json").is_file():
        return [
            problem(
                "web",
                "WEB-FILES",
                "blocker",
                STAGE,
                "presentation/",
                "缺少站点工程（先运行 build_site.py）",
            )
        ]

    course_path = presentation / "src" / "content" / "course.json"
    course = None
    if not course_path.is_file():
        problems.append(problem("web", "WEB-DATA", "blocker", STAGE, ws.rel(course_path), "缺少 course.json"))
    else:
        try:
            course = io.load_json(course_path)
        except Exception as exc:  # noqa: BLE001
            problems.append(problem("web", "WEB-DATA", "blocker", STAGE, ws.rel(course_path), f"无法解析：{exc}"))

    narrations_path = presentation / "src" / "content" / "narrations.json"
    narrations = {}
    if narrations_path.is_file():
        try:
            narrations = io.load_json(narrations_path)
        except Exception:  # noqa: BLE001
            problems.append(problem("web", "WEB-DATA", "warning", STAGE, ws.rel(narrations_path), "narrations.json 无法解析"))
    else:
        problems.append(problem("web", "WEB-DATA", "warning", STAGE, ws.rel(narrations_path), "缺少 narrations.json"))

    if isinstance(course, dict):
        chapters = course.get("chapters") or []
        if not chapters:
            problems.append(problem("web", "WEB-EMPTY", "blocker", STAGE, ws.rel(course_path), "课程没有任何章节"))
        for chapter in chapters:
            for slide in chapter.get("slides") or []:
                slide_id = slide.get("id")
                if not str(slide.get("narration", "")).strip():
                    problems.append(
                        problem("web", "WEB-NARR", "warning", STAGE, f"{chapter.get('id')}/{slide_id}", "该页没有讲稿文本")
                    )
                for ref in slide.get("media_refs") or []:
                    target = presentation / "public" / ref
                    if not target.is_file():
                        problems.append(
                            problem("web", "WEB-ASSET", "blocker", STAGE, f"{chapter.get('id')}/{slide_id}", f"素材缺失：{ref}")
                        )

    dist_index = presentation / "dist" / "index.html"
    if require_build and not dist_index.is_file():
        problems.append(
            problem(
                "web",
                "WEB-BUILD",
                "blocker",
                STAGE,
                "presentation/dist/index.html",
                "缺少构建产物，请运行 npm run build",
            )
        )
    if dist_index.is_file():
        problems.extend(_check_dist(presentation, dist_index))
    problems.extend(_check_offline_and_a11y(presentation))
    return problems


def _check_dist(presentation: Path, dist_index: Path) -> list[dict]:
    problems: list[dict] = []
    html = dist_index.read_text(encoding="utf-8", errors="ignore")
    if not re.search(r"<html[^>]*\blang\s*=", html, re.IGNORECASE):
        problems.append(
            problem("web", "WEB-A11Y", "warning", STAGE, "presentation/dist/index.html", "html 缺少 lang 属性")
        )
    for ref in ATTR_RE.findall(html):
        if ref.startswith(("http://", "https://", "data:", "#", "mailto:")):
            continue
        relative = ref.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        if relative and not (presentation / "dist" / relative).exists() and not (presentation / "public" / relative).exists():
            problems.append(
                problem("web", "WEB-LINK", "blocker", STAGE, "presentation/dist/index.html", f"引用的资源不存在：{ref}")
            )
    return problems


def _check_offline_and_a11y(presentation: Path) -> list[dict]:
    problems: list[dict] = []
    scan_roots = [presentation / "src", presentation / "index.html"]
    external: set[str] = set()
    for root in scan_roots:
        files = [root] if root.is_file() else list(root.rglob("*")) if root.is_dir() else []
        for path in files:
            if not path.is_file() or path.suffix not in (".ts", ".tsx", ".css", ".html"):
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith(("//", "*", "/*", "<!--")):
                    continue
                for url in URL_RE.findall(line):
                    external.add(f"{path.relative_to(presentation)}:{line_number} -> {url}")
            if path.suffix == ".tsx":
                for tag in IMG_RE.findall(path.read_text(encoding="utf-8", errors="ignore")):
                    if "alt=" not in tag:
                        problems.append(
                            problem("web", "WEB-A11Y", "warning", STAGE, str(path.relative_to(presentation)), "img 缺少 alt")
                        )
    for entry in sorted(external):
        problems.append(
            problem(
                "web",
                "WEB-OFFLINE",
                "warning",
                STAGE,
                entry.split(" -> ")[0],
                f"引用了外部资源，离线不可用：{entry.split(' -> ')[1]}",
            )
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="检查课程站点")
    parser.add_argument("workspace")
    parser.add_argument("--no-build-check", action="store_true", help="不要求 dist 构建产物")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problems = check(Workspace(args.workspace), require_build=not args.no_build_check)
    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        for item in problems:
            print(f"[{item['severity']}] {item['rule_id']} {item['target']}: {item['message']}")
        print(f"{len(problems)} 个问题（{sum(1 for p in problems if p['severity'] == 'blocker')} 个 blocker）")
    return 1 if any(item["severity"] == "blocker" for item in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
