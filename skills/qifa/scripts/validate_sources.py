#!/usr/bin/env python3
"""来源校验：source-model 完整性、引用可解析、代码路径与媒体文件存在。

用法：python3 validate_sources.py <workspace> [--json]
作为库：from validate_sources import check; check(Workspace)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.workbench import (  # noqa: E402
    Workspace,
    iter_source_refs,
    problem,
    strip_code_locator,
)

STAGE = "source-analysis"


def check(ws: Workspace) -> list[dict]:
    problems: list[dict] = []
    model = ws.load_source_model()
    if model is None:
        return [
            problem(
                "source",
                "SRC-MISSING",
                "blocker",
                STAGE,
                "source/source-model.json",
                "缺少或无法解析 source-model.json",
                "按 paper-analysis.md / code-analysis.md 生成来源模型",
            )
        ]

    sources = model.get("sources") or []
    if not sources:
        problems.append(
            problem("source", "SRC-EMPTY", "blocker", STAGE, "source/source-model.json", "sources 为空")
        )

    by_id: dict[str, dict] = {}
    repo_roots: dict[str, Path] = {}
    for source in sources:
        source_id = source.get("id", "")
        if source_id in by_id:
            problems.append(
                problem("source", "SRC-DUP", "blocker", STAGE, source_id, f"source id 重复：{source_id}")
            )
        by_id[source_id] = source

        source_type = source.get("type")
        origin = str(source.get("origin", ""))
        if source_type == "repo":
            root = _local_repo_root(origin, ws)
            if root is not None:
                if not root.exists():
                    problems.append(
                        problem("source", "SRC-REPO", "blocker", STAGE, source_id, f"本地仓库不存在：{origin}")
                    )
                else:
                    repo_roots[source_id] = root
            elif str(source.get("kind", "")) == "local":
                problems.append(
                    problem("source", "SRC-REPO", "blocker", STAGE, source_id, f"本地仓库不存在：{origin}")
                )

    # 代码路径存在性
    for source_id, source in by_id.items():
        if source.get("type") != "repo" or source_id not in repo_roots:
            continue
        root = repo_roots[source_id]
        code = source.get("code") or {}
        for relative in code.get("files") or []:
            if not (root / relative).exists():
                problems.append(
                    problem("source", "SRC-CODE-PATH", "blocker", STAGE, f"{source_id}:{relative}", "代码文件不存在")
                )
        for symbol in code.get("symbols") or []:
            if ":" not in str(symbol):
                problems.append(
                    problem(
                        "source",
                        "SRC-CODE-FORMAT",
                        "warning",
                        STAGE,
                        f"{source_id}:{symbol}",
                        "代码引用应为 path:符号 格式",
                    )
                )

    # 媒体文件存在性
    media_dir = ws.root / "source" / "media"
    for source_id, source in by_id.items():
        if source.get("type") != "media":
            continue
        origin = Path(str(source.get("origin", "")))
        candidates = [origin, media_dir / origin.name, ws.root / origin]
        if not any(path.is_file() for path in candidates):
            problems.append(
                problem("source", "SRC-MEDIA", "blocker", STAGE, f"{source_id}:{origin}", "媒体文件不存在")
            )

    # 相关性映射
    relevance = model.get("relevance") or {}
    relation = relevance.get("relation")
    mapping = relevance.get("mapping") or []
    if relation in ("related", "partial") and not mapping:
        problems.append(
            problem("source", "SRC-RELEVANCE", "warning", STAGE, "relevance", "related/partial 但没有 mapping 条目")
        )
    for index, item in enumerate(mapping):
        target = f"relevance.mapping[{index}]"
        if not str(item.get("paper_section", "")).strip():
            problems.append(problem("source", "SRC-MAPPING", "warning", STAGE, target, "paper_section 为空"))
        for code_path in item.get("code_paths") or []:
            if not code_path:
                continue
            repo_root = next(iter(repo_roots.values()), None)
            if repo_root is not None and not (repo_root / strip_code_locator(str(code_path))).exists():
                problems.append(
                    problem("source", "SRC-MAPPING", "blocker", STAGE, f"{target}:{code_path}", "映射的代码路径不存在")
                )

    # 词汇表
    seen_terms: set[str] = set()
    seen_translations: set[str] = set()
    for index, entry in enumerate(model.get("glossary") or []):
        term = str(entry.get("term", ""))
        translation = str(entry.get("translation", ""))
        if term in seen_terms:
            problems.append(problem("source", "SRC-GLOSSARY", "warning", STAGE, f"glossary[{index}]", f"术语重复：{term}"))
        seen_terms.add(term)
        if translation and translation in seen_translations:
            problems.append(
                problem("source", "SRC-GLOSSARY", "warning", STAGE, f"glossary[{index}]", f"译名重复：{translation}")
            )
        seen_translations.add(translation)

    # 引用可解析（plan 与讲稿中已存在的引用）
    problems.extend(_check_refs(ws, by_id, repo_roots))
    return problems


def _local_repo_root(origin: str, ws: Workspace | None = None) -> Path | None:
    if "://" in origin or origin.startswith("git@"):
        return None
    parsed = urlparse(origin)
    if parsed.scheme:
        return None
    path = Path(origin).expanduser()
    if not path.is_absolute() and ws is not None:
        path = (ws.root / path).resolve()
    return path


def _check_refs(ws: Workspace, by_id: dict, repo_roots: dict[str, Path]) -> list[dict]:
    problems: list[dict] = []
    containers: list[tuple[str, dict]] = []
    outline = ws.load_outline()
    if outline:
        containers.append(("plan/course-outline.json", outline))
    visual = ws.load_visual_plan()
    if visual:
        containers.append(("plan/visual-plan.json", visual))
    for path, data in ws.load_chapter_plans():
        if data:
            containers.append((ws.rel(path), data))

    seen: set[tuple] = set()
    for label, data in containers:
        for ref in iter_source_refs(data):
            key = (label, str(ref.get("source_id")), str(ref.get("locator")))
            if key in seen:
                continue
            seen.add(key)
            source_id = str(ref.get("source_id"))
            locator = str(ref.get("locator", "")).strip()
            if source_id not in by_id:
                problems.append(
                    problem("source", "SRC-REF", "blocker", STAGE, label, f"引用指向不存在的来源：{source_id}")
                )
                continue
            if not locator:
                problems.append(problem("source", "SRC-REF", "blocker", STAGE, label, f"{source_id} 的引用缺少 locator"))
                continue
            source = by_id[source_id]
            if source.get("type") == "repo" and source_id in repo_roots:
                relative = strip_code_locator(locator)
                if not (repo_roots[source_id] / relative).exists():
                    problems.append(
                        problem(
                            "source",
                            "SRC-REF",
                            "blocker",
                            STAGE,
                            label,
                            f"代码引用不存在：{source_id}:{locator}",
                        )
                    )
            if source.get("type") == "media":
                media_dir = ws.root / "source" / "media"
                if not (media_dir / locator).exists() and not (ws.root / locator).exists():
                    problems.append(
                        problem("source", "SRC-REF", "blocker", STAGE, label, f"媒体引用不存在：{locator}")
                    )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="校验来源模型与引用可解析性")
    parser.add_argument("workspace")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problems = check(Workspace(args.workspace))
    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        for item in problems:
            print(f"[{item['severity']}] {item['rule_id']} {item['target']}: {item['message']}")
        print(f"{len(problems)} 个问题（{sum(1 for p in problems if p['severity'] == 'blocker')} 个 blocker）")
    return 1 if any(item["severity"] == "blocker" for item in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
