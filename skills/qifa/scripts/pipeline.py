#!/usr/bin/env python3
"""QiFa pipeline：无 LLM 的确定性内核。

子命令：init / status / validate / advance / report / estimate
退出码：0 正常；1 硬失败（含 blocker 校验不过）；2 用法与配置错误。

生成内容由 Agent 完成；本脚本只负责初始化、状态推进、校验与汇总。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import deps, io, paths  # noqa: E402
from lib.workbench import STAGES, Workspace  # noqa: E402

import build_site as build_site_mod  # noqa: E402
import check_site as check_site_mod  # noqa: E402
import estimate_duration as estimate_mod  # noqa: E402
import validate_course as validate_course_mod  # noqa: E402
import validate_sources as validate_sources_mod  # noqa: E402
import validate_stage as validate_stage_mod  # noqa: E402

DEFAULT_POLICIES = {
    "max_repair_attempts": 2,
    "on_soft_failure": "continue-and-report",
    "on_hard_failure": "stop",
    "auto_install": True,
    "duration_tolerance": 0.3,
}

DEFAULT_SPEAKING_RATE = {"zh_chars_per_minute": 240, "en_words_per_minute": 130}

DURATION_CHOICES = (20, 45, 90)

ARTIFACT_PATTERNS = {
    "intake": ["project.yaml", "00-intake.md", ".qifa/run-state.yaml"],
    "source-analysis": ["source/source-model.json", "source/paper.md"],
    "curriculum": ["plan/course-outline.json"],
    "chapter-design": ["plan/chapter-plan-C*.json"],
    "narrative": ["script/*.md"],
    "visual-storyboard": ["plan/visual-plan.json"],
    "web-generation": ["presentation/package.json", "presentation/src/content/course.json", "presentation/dist/index.html"],
    "automated-review": ["review/qa-report.json", "review/qa-report.md"],
    "package": ["README-learner.md", "start.sh", "start.command", "start.bat"],
}


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #

def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def dedupe(problems: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result: list[dict] = []
    for item in problems:
        key = (item["rule_id"], item["target"], item["message"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def merge(base: dict, override: dict | None) -> dict:
    if not override:
        return base
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        elif value is not None:
            result[key] = value
    return result


def load_state(ws: Workspace) -> dict | None:
    return ws.load_run_state()


def save_state(ws: Workspace, state: dict) -> None:
    io.dump_yaml(ws.run_state_path, state)


def dispatch(ws: Workspace, stage: str) -> list[dict]:
    index = STAGES.index(stage)
    problems = validate_stage_mod.check(ws, stage)
    if index >= 1:
        problems += validate_sources_mod.check(ws)
    if index >= 2:
        problems += validate_course_mod.check(ws, stage=stage)
    if index >= 6:
        problems += check_site_mod.check(ws, require_build=True)
    return dedupe(problems)


def collect_artifacts(ws: Workspace, stage: str) -> list[str]:
    result: list[str] = []
    for pattern in ARTIFACT_PATTERNS.get(stage, []):
        result.extend(ws.rel(path) for path in sorted(ws.root.glob(pattern)))
    return result


def validator_names(stage: str) -> list[str]:
    index = STAGES.index(stage)
    names = ["validate_stage"]
    if index >= 1:
        names.append("validate_sources")
    if index >= 2:
        names.append("validate_course")
    if index >= 6:
        names.append("check_site")
    return names


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #

def _infer_input(value: str) -> tuple[str, str]:
    prefix, sep, rest = value.partition(":")
    if sep and prefix in ("paper", "repo", "media"):
        return prefix, rest
    low = value.lower()
    if low.startswith("git@") or low.endswith(".git") or re.search(r"(github|gitlab|bitbucket|gitee)\.com/", low):
        return "repo", value
    path = Path(value).expanduser()
    if path.is_dir():
        return "repo", value
    return "paper", value


def _paper_kind(origin: str) -> str:
    low = origin.lower()
    if "arxiv.org" in low:
        return "arxiv"
    if low.endswith(".pdf"):
        return "pdf"
    if low.endswith(".docx"):
        return "docx"
    if low.endswith(".tex"):
        return "latex-source"
    path = Path(origin).expanduser()
    if path.is_dir():
        return "latex-project"
    if low.startswith(("http://", "https://")) or path.suffix in (".html", ".htm"):
        return "webpage"
    return "pdf"


def _repo_kind(origin: str) -> str:
    if "://" in origin or origin.startswith("git@"):
        return "git"
    return "local"


def _slug_from(case: dict, inputs: dict) -> str:
    if case.get("name"):
        return paths.slugify(str(case["name"]))
    paper = (inputs.get("paper") or {}).get("origin")
    if paper:
        return paths.slugify(Path(str(paper)).stem or str(paper))
    repo = (inputs.get("repo") or {}).get("origin")
    if repo:
        return paths.slugify(Path(str(repo).rstrip("/")).name or str(repo))
    return "course"


def cmd_init(args) -> int:
    case: dict = {}
    if args.case:
        case_path = Path(args.case).expanduser()
        if not case_path.is_file():
            print(f"[错误] case 文件不存在：{case_path}", file=sys.stderr)
            return 2
        case = io.load_yaml(case_path) or {}

    # 输入
    inputs: dict = {}
    for item in args.input or []:
        kind, origin = _infer_input(item)
        if kind == "paper":
            inputs["paper"] = {"kind": _paper_kind(origin), "origin": origin}
        elif kind == "repo":
            inputs["repo"] = {"kind": _repo_kind(origin), "origin": origin}
        else:
            inputs.setdefault("media", []).append(origin)
    for kind, value in (case.get("input") or {}).items():
        if kind == "media":
            inputs.setdefault("media", []).extend(value if isinstance(value, list) else [value])
        elif value and kind not in inputs:
            if isinstance(value, dict):
                inputs[kind] = value
            elif kind == "paper":
                inputs["paper"] = {"kind": _paper_kind(str(value)), "origin": str(value)}
            elif kind == "repo":
                inputs["repo"] = {"kind": _repo_kind(str(value)), "origin": str(value)}

    if not inputs.get("paper") and not inputs.get("repo"):
        print("[错误] 至少需要一个 --input paper:<...> 或 --input repo:<...>", file=sys.stderr)
        return 2

    # 配置来源（低 -> 高）
    preset: dict = {}
    if args.preset:
        preset_path = paths.skill_dir() / "assets" / "presets" / f"{args.preset}.yaml"
        if not preset_path.is_file():
            print(f"[错误] preset 不存在：{args.preset}", file=sys.stderr)
            return 2
        preset = io.load_yaml(preset_path) or {}

    global_config: dict = {}
    if paths.config_file().is_file():
        global_config = io.load_yaml(paths.config_file()) or {}

    override: dict = {}
    if args.config:
        config_path = Path(args.config).expanduser()
        if not config_path.is_file():
            print(f"[错误] 配置文件不存在：{config_path}", file=sys.stderr)
            return 2
        override = io.load_yaml(config_path) or {}

    case_config = case.get("config") or {}
    flat = merge(
        merge(
            merge(
                merge(
                    {
                        "audience": "具备基础背景的学习者",
                        "level": None,
                        "depth": "intermediate",
                        "language": "zh-CN",
                        "visual_style": None,
                        "goal": None,
                    },
                    preset,
                ),
                {key: global_config.get(key) for key in ("audience", "language", "visual_style", "depth")},
            ),
            case_config,
        ),
        override,
    )

    depth = str(flat.get("depth") or "intermediate")
    level = flat.get("level")
    if not level:
        level = {"overview": "beginner", "intermediate": "intermediate", "deep": "advanced"}.get(depth, "intermediate")
    visual_style = flat.get("visual_style")
    if not visual_style:
        visual_style = "engineering-blueprint" if inputs.get("repo") and not inputs.get("paper") else "scientific-editorial"

    duration = args.duration or case_config.get("duration") or flat.get("duration_minutes") or 45
    mode = args.mode or case.get("mode") or "production"
    stop_after = args.stop_after or case.get("stop_after")

    slug = _slug_from(case, inputs)
    ws_root = Path(args.out).expanduser() if args.out else paths.default_output() / slug
    ws = Workspace(ws_root)

    goal = str(flat.get("goal") or f"讲清所选来源并让学习者能用自己的话复述")
    course_title = str(case.get("name") or slug)

    project = {
        "mode": mode,
        "interaction": "stage-review" if mode == "development" else "upfront-only",
        "input": inputs,
        "learner": {
            "audience": str(flat.get("audience") or "具备基础背景的学习者"),
            "level": level,
            "prerequisites": list(flat.get("prerequisites") or []),
        },
        "goal": goal,
        "language": str(flat.get("language") or "zh-CN"),
        "duration": {"target_minutes": int(duration)},
        "depth": depth,
        "visual_style": str(visual_style),
        "output": {"workspace": str(ws_root)},
        "policies": merge(DEFAULT_POLICIES, flat.get("policies")),
        "speaking_rate": merge(DEFAULT_SPEAKING_RATE, flat.get("speaking_rate")),
    }
    if stop_after:
        project["stop_after"] = stop_after

    for sub in ("source/media", "plan", "script", "review", ".qifa/logs"):
        (ws_root / sub).mkdir(parents=True, exist_ok=True)

    io.dump_yaml(ws.project_path, project)
    state = {
        "mode": mode,
        "stage": STAGES[0],
        "stages": {
            name: {
                "status": "pending",
                "attempts": 0,
                "artifacts": [],
                "checks": [],
                "degradations": [],
            }
            for name in STAGES
        },
        "warnings": [],
    }
    state["stages"][STAGES[0]]["status"] = "in_progress"
    state["stages"][STAGES[0]]["started_at"] = now()
    save_state(ws, state)

    (ws_root / "00-intake.md").write_text(_intake_skeleton(project, course_title), encoding="utf-8")

    dep_result = {"status": "skipped", "detail": "未执行"}
    if not args.no_install:
        dep_result = deps.ensure(no_install=False)
        (ws_root / ".qifa" / "logs" / "init.log").write_text(
            f"{now()} deps: {dep_result['status']} - {dep_result['detail']}\n", encoding="utf-8"
        )
    else:
        (ws_root / ".qifa" / "logs" / "init.log").write_text(
            f"{now()} deps: skipped (--no-install)\n", encoding="utf-8"
        )

    summary = {
        "workspace": str(ws_root),
        "mode": mode,
        "stage": STAGES[0],
        "preset": args.preset,
        "deps": dep_result,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"工作区已创建：{ws_root}")
        print(f"模式：{mode}；时长目标：{duration} 分钟；语言：{project['language']}；风格：{project['visual_style']}")
        print(f"依赖：{dep_result['status']} - {dep_result['detail']}")
    return 0


def _intake_skeleton(project: dict, title: str) -> str:
    inputs = project.get("input") or {}
    lines = [
        f"# Intake：{title}",
        "",
        "## 输入",
        f"- 论文：{((inputs.get('paper') or {}).get('origin') or '无')}",
        f"- 代码库：{((inputs.get('repo') or {}).get('origin') or '无')}",
        f"- 媒体：{', '.join(inputs.get('media') or []) or '无'}",
        "",
        "## 本次确认",
        f"- 目标学习者：{project['learner']['audience']}（{project['learner']['level']}）",
        f"- 课程目标：{project['goal']}",
        f"- 期望时长：{project['duration']['target_minutes']} 分钟",
        f"- 输出语言：{project['language']}",
        f"- 视觉风格：{project['visual_style']}",
        f"- 深度：{project['depth']}",
        "",
        "## 推断与默认值",
        "- 待填写：哪些字段来自推断、哪些使用了默认值",
        "",
        "## 论文与代码相关性（混合输入时）",
        "- relation：待判定（related / partial / none）",
        "- 用户选择（relation 非 related 时）：待确认",
        "",
        "## 备注",
        "- Agent 在此记录 intake 结论；确认完成后本文件不再修改。",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# status / validate / advance
# --------------------------------------------------------------------------- #

def cmd_status(args) -> int:
    ws = Workspace(args.workspace)
    state = load_state(ws)
    if state is None:
        print(f"[错误] 找不到工作区状态文件：{ws.run_state_path}", file=sys.stderr)
        return 2
    rows = [(name, state["stages"].get(name, {})) for name in STAGES]
    if args.json:
        print(json.dumps({"stage": state.get("stage"), "mode": state.get("mode"), "stages": dict(rows)}, ensure_ascii=False, indent=2))
        return 0
    print(f"工作区：{ws.root}")
    print(f"模式：{state.get('mode')}；当前阶段：{state.get('stage')}")
    for name, entry in rows:
        print(
            f"  {name:18} {entry.get('status', '?'):12} attempts={entry.get('attempts', 0)}"
            f" degradations={len(entry.get('degradations') or [])}"
        )
    return 0


def cmd_validate(args) -> int:
    ws = Workspace(args.workspace)
    problems = dispatch(ws, args.stage)
    if args.json:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
    else:
        for item in problems:
            print(f"[{item['severity']}] {item['rule_id']} {item['target']}: {item['message']}")
        print(f"{len(problems)} 个问题（{sum(1 for p in problems if p['severity'] == 'blocker')} 个 blocker）")
    return 1 if any(item["severity"] == "blocker" for item in problems) else 0


def cmd_advance(args) -> int:
    ws = Workspace(args.workspace)
    state = load_state(ws)
    project = ws.load_project()
    if state is None or project is None:
        print("[错误] 工作区不完整（缺少 project.yaml 或 run-state.yaml）", file=sys.stderr)
        return 2
    if state.get("stage") != args.stage:
        print(f"[错误] 当前阶段是 {state.get('stage')}，不能推进 {args.stage}", file=sys.stderr)
        return 2

    problems = dispatch(ws, args.stage)
    blockers = [item for item in problems if item["severity"] == "blocker"]
    warnings = [item for item in problems if item["severity"] == "warning"]
    entry = state["stages"][args.stage]
    entry["checks"] = validator_names(args.stage)
    entry["artifacts"] = collect_artifacts(ws, args.stage)

    if blockers:
        entry["attempts"] = int(entry.get("attempts", 0)) + 1
        max_attempts = int((project.get("policies") or {}).get("max_repair_attempts", 2))
        if entry["attempts"] > max_attempts:
            entry["status"] = "failed"
            entry["finished_at"] = now()
            save_state(ws, state)
            print(f"[终止] {args.stage} 修复 {max_attempts} 次后仍有 {len(blockers)} 个 blocker：")
            for item in blockers:
                print(f"  - {item['rule_id']} {item['target']}: {item['message']}")
            return 1
        entry["status"] = "in_progress"
        save_state(ws, state)
        print(f"[未通过] {args.stage} 有 {len(blockers)} 个 blocker（第 {entry['attempts']} 次尝试）：")
        for item in blockers:
            print(f"  - {item['rule_id']} {item['target']}: {item['message']}")
        return 1

    entry["status"] = "degraded" if warnings else "validated"
    entry["finished_at"] = now()
    entry["degradations"] = [
        {"code": item["rule_id"], "message": f"{item['target']}: {item['message']}"} for item in warnings
    ]
    index = STAGES.index(args.stage)
    if index + 1 < len(STAGES):
        next_stage = STAGES[index + 1]
        state["stage"] = next_stage
        next_entry = state["stages"][next_stage]
        if next_entry.get("status") == "pending":
            next_entry["status"] = "in_progress"
            next_entry["started_at"] = now()
    save_state(ws, state)
    print(f"[通过] {args.stage} → {state['stage']}（警告 {len(warnings)} 项）")
    return 0


# --------------------------------------------------------------------------- #
# report / estimate
# --------------------------------------------------------------------------- #

def cmd_estimate(args) -> int:
    ws = Workspace(args.workspace)
    result = estimate_mod.estimate(ws)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result["per_chapter"]:
            print(f"{item['chapter_id']}: {item['chars']} 汉字 + {item['words']} 词 ≈ {item['minutes']} 分钟")
        print(f"合计 ≈ {result['total']} 分钟")
    return 0


def cmd_report(args) -> int:
    ws = Workspace(args.workspace)
    state = load_state(ws)
    project = ws.load_project() or {}
    if state is None:
        print("[错误] 缺少 run-state.yaml", file=sys.stderr)
        return 2

    problems = dedupe(
        validate_stage_mod.check(ws, "web-generation")
        + validate_sources_mod.check(ws)
        + validate_course_mod.check(ws, stage="automated-review")
        + check_site_mod.check(ws, require_build=True)
    )
    estimate_result = estimate_mod.estimate(ws)
    degradations: list[dict] = []
    for entry in (state.get("stages") or {}).values():
        degradations.extend(entry.get("degradations") or [])

    items = [dict(item, status="open") for item in problems]
    report = {
        "generated_at": now(),
        "mode": str(state.get("mode") or project.get("mode") or "production"),
        "summary": {
            "blockers": sum(1 for item in items if item["severity"] == "blocker"),
            "warnings": sum(1 for item in items if item["severity"] == "warning"),
            "infos": sum(1 for item in items if item["severity"] == "info"),
            "degradations": len(degradations),
        },
        "items": items,
        "duration": {"per_chapter": estimate_result["per_chapter"], "total": estimate_result["total"]},
    }
    io.dump_json(ws.qa_report_path, report)
    (ws.root / "review" / "qa-report.md").write_text(
        _report_markdown(report, degradations), encoding="utf-8"
    )
    (ws.root / "README-learner.md").write_text(
        _learner_readme(ws, project, state, report), encoding="utf-8"
    )

    exit_code = 0
    if args.case:
        exit_code = _check_expect(args.case, ws, state, report, project)
    if args.json:
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(
            f"QA 报告已生成：blockers={summary['blockers']} warnings={summary['warnings']} "
            f"infos={summary['infos']} degradations={summary['degradations']}"
        )
        print(f"讲稿合计 ≈ {estimate_result['total']} 分钟")
    return exit_code


def _check_expect(case_path: str, ws: Workspace, state: dict, report: dict, project: dict) -> int:
    case = io.load_yaml(Path(case_path).expanduser()) or {}
    expect = case.get("expect") or {}
    failures: list[str] = []
    if expect.get("no_blockers") and report["summary"]["blockers"]:
        failures.append(f"存在 {report['summary']['blockers']} 个 blocker")
    for stage in expect.get("stages_done") or []:
        status = (state["stages"].get(stage) or {}).get("status")
        if status not in ("validated", "degraded"):
            failures.append(f"阶段 {stage} 状态为 {status}，未完成")
    outline_expect = expect.get("outline") or {}
    outline = ws.load_outline() or {}
    chapters = outline.get("chapters") or []
    if "min_chapters" in outline_expect and len(chapters) < outline_expect["min_chapters"]:
        failures.append(f"章节数 {len(chapters)} 少于 min_chapters {outline_expect['min_chapters']}")
    if "max_chapters" in outline_expect and len(chapters) > outline_expect["max_chapters"]:
        failures.append(f"章节数 {len(chapters)} 多于 max_chapters {outline_expect['max_chapters']}")
    if outline_expect.get("objectives_covered"):
        uncovered = [obj.get("id") for obj in outline.get("objectives") or [] if not obj.get("chapter_ids")]
        if uncovered:
            failures.append(f"目标未被章节覆盖：{uncovered}")
    if failures:
        print("[expect 未满足]")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("[expect 满足]")
    return 0


def _report_markdown(report: dict, degradations: list[dict]) -> str:
    summary = report["summary"]
    lines = [
        "# QA 报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 模式：{report['mode']}",
        f"- 摘要：blocker {summary['blockers']} / warning {summary['warnings']} / info {summary['infos']} / 降级 {summary['degradations']}",
        "",
        "## 时长",
        "",
        "| 章节 | 汉字 | 英文词 | 估算分钟 |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["duration"]["per_chapter"]:
        lines.append(f"| {item['chapter_id']} | {item['chars']} | {item['words']} | {item['minutes']} |")
    lines.append(f"| 合计 | - | - | {report['duration']['total']} |")
    lines += ["", "## 问题清单", ""]
    if not report["items"]:
        lines.append("无。")
    for item in report["items"]:
        lines.append(
            f"- [{item['severity']}] {item['rule_id']}（{item['layer']}）{item['target']}：{item['message']}"
            + (f" → {item['remediation']}" if item.get("remediation") else "")
        )
    lines += ["", "## 降级与警告", ""]
    if not degradations:
        lines.append("无。")
    for item in degradations:
        lines.append(f"- {item.get('code')}: {item.get('message')}")
    if degradations or summary["degradations"]:
        lines += ["", "> 本课程存在降级项，课件首屏会提示学习者。"]
    return "\n".join(lines) + "\n"


def _learner_readme(ws: Workspace, project: dict, state: dict, report: dict) -> str:
    title = ((ws.load_outline() or {}).get("course") or {}).get("title") or "QiFa 课程"
    summary = report["summary"]
    lines = [
        f"# {title}",
        "",
        "## 怎么打开",
        "",
        "- Windows：双击 `start.bat`",
        "- macOS：双击 `start.command`（首次若被拦截，右键 → 打开）",
        "- Linux / macOS 终端：`bash start.sh`",
        "",
        "需要安装 Node >= 18（https://nodejs.org/）。首次启动会自动安装依赖，可能需要几分钟。",
        "",
        "## 课程状态",
        "",
        f"- 时长目标：{((project.get('duration') or {}).get('target_minutes'))} 分钟；讲稿换算：{report['duration']['total']} 分钟",
        f"- 质检：blocker {summary['blockers']} / warning {summary['warnings']} / 降级 {summary['degradations']}",
        "- 详细报告：`review/qa-report.md`",
    ]
    if summary["degradations"]:
        lines += ["", "> 本课程存在降级项（部分内容以更保守的方式呈现），详见 QA 报告。"]
    lines += [
        "",
        "## 文件",
        "",
        "- `presentation/`：课程站点源码",
        "- `script/`：分章讲稿",
        "- `plan/`：课程大纲、章节计划、视觉登记",
        "- `source/`：论文、代码与素材来源",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline.py", description="QiFa 确定性流水线内核（无 LLM）")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="创建工作区、project.yaml 与 run-state.yaml")
    p_init.add_argument("--case", help="dev case YAML（tests/cases/*.yaml）")
    p_init.add_argument("--mode", choices=["production", "development"])
    p_init.add_argument("--input", action="append", help="paper:<origin> / repo:<origin> / media:<path>，可重复")
    p_init.add_argument("--config", help="项目覆盖配置 YAML")
    p_init.add_argument("--preset", choices=["research-course", "code-onboarding", "beginner-tutorial"])
    p_init.add_argument("--out", help="工作区目录")
    p_init.add_argument("--duration", type=int, help="目标时长（分钟）")
    p_init.add_argument("--stop-after", dest="stop_after", help="development 模式停止阶段")
    p_init.add_argument("--no-install", action="store_true", help="不创建 venv、不安装可选依赖")
    p_init.add_argument("--json", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status", help="查看阶段状态")
    p_status.add_argument("workspace", nargs="?", default=".")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_validate = sub.add_parser("validate", help="运行指定阶段的确定性校验")
    p_validate.add_argument("stage", choices=STAGES)
    p_validate.add_argument("workspace", nargs="?", default=".")
    p_validate.add_argument("--json", action="store_true")
    p_validate.set_defaults(func=cmd_validate)

    p_advance = sub.add_parser("advance", help="校验通过后推进阶段；不通过累计修复次数")
    p_advance.add_argument("--stage", required=True, choices=STAGES)
    p_advance.add_argument("workspace", nargs="?", default=".")
    p_advance.set_defaults(func=cmd_advance)

    p_report = sub.add_parser("report", help="汇总 QA 报告、时长与学习者说明")
    p_report.add_argument("workspace", nargs="?", default=".")
    p_report.add_argument("--case", help="同时校验 case 的 expect 不变量")
    p_report.add_argument("--json", action="store_true")
    p_report.set_defaults(func=cmd_report)

    p_estimate = sub.add_parser("estimate", help="讲稿字数与时长统计")
    p_estimate.add_argument("workspace", nargs="?", default=".")
    p_estimate.add_argument("--json", action="store_true")
    p_estimate.set_defaults(func=cmd_estimate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，避免泄漏堆栈
        print(f"[错误] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
