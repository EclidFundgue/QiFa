#!/usr/bin/env python3
"""QiFa P0 回归：零 LLM、零网络，全部使用标准库。

覆盖：
1. 仓库结构与 skill 自检（目录命名、frontmatter、资源索引）；
2. `references/schemas/*.schema.json` 可解析；
3. `tests/cases/*.yaml` 契约（名称/模式/输入/expect）；
4. CLI 冒烟（--help；空工作区报错但不抛栈）；
5. fixture 工作区全链路：validate → build_site → check_site → estimate；
6. development 模式 `init` + `advance intake`；
7. 解释器与依赖契约（内置实现是默认路径，见 production-workflow.md）。

用法：python3 tests/test_validation.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURE = SKILL / "tests" / "fixtures" / "workspaces" / "tiny-course"

# SKILL.md 里提到的、但属于工作区产物而非 references/ 的 markdown 文件名。
WORKSPACE_MD = {"SKILL.md", "README-learner.md", "00-intake.md", "qa-report.md"}

sys.path.insert(0, str(SCRIPTS))

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def run(*args, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return run_exe(sys.executable, *args, cwd=cwd, env=env)


def run_exe(*args, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=merged_env,
    )


# --------------------------------------------------------------------------- #
# 1. 仓库结构与 skill 自检
# --------------------------------------------------------------------------- #

@case
def repository_structure() -> None:
    assert (SKILL / "SKILL.md").is_file(), "缺少 SKILL.md"
    for sub in ("references", "scripts", "assets", "tests"):
        assert (SKILL / sub).is_dir(), f"缺少目录 {sub}/"
    dir_name = re.compile(r"^[a-z0-9][a-z0-9-]*$")
    for path in sorted(SKILL.rglob("*")):
        if not path.is_dir() or path.name.startswith(".") or path.name == "__pycache__":
            continue
        assert dir_name.match(path.name), f"目录名不符合小写 kebab-case：{path.relative_to(SKILL)}"


@case
def skill_frontmatter_and_resource_index() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(\S+)\s*$", text, re.MULTILINE)
    assert match, "SKILL.md 缺少 frontmatter name"
    assert match.group(1) == SKILL.name == "qifa", f"frontmatter name={match.group(1)} 与目录名不一致"
    for span in re.findall(r"`([^`]+)`", text):
        if span.startswith(("references/", "scripts/", "assets/", "tests/")) and "*" not in span:
            assert (SKILL / span).exists(), f"SKILL.md 资源索引指向不存在的路径：{span}"
        elif span.endswith(".md") and "/" not in span and span not in WORKSPACE_MD:
            assert (SKILL / "references" / span).is_file(), f"SKILL.md 提到的 reference 不存在：{span}"


# --------------------------------------------------------------------------- #
# 2. schema 可解析
# --------------------------------------------------------------------------- #

@case
def schemas_parse() -> None:
    schema_dir = SKILL / "references" / "schemas"
    paths = sorted(schema_dir.glob("*.schema.json"))
    assert len(paths) == 7, f"预期 7 个 schema，实际 {len(paths)}"
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("title"), path.name
        assert data.get("type") == "object", path.name


# --------------------------------------------------------------------------- #
# 3. case 契约
# --------------------------------------------------------------------------- #

@case
def cases_contract() -> None:
    from lib import miniyaml

    paths = sorted((SKILL / "tests" / "cases").glob("*.yaml"))
    assert paths, "tests/cases/ 下没有 case"
    for path in paths:
        data = miniyaml.loads(path.read_text(encoding="utf-8"))
        assert data.get("name"), f"{path.name}: 缺少 name"
        assert data.get("mode") in ("production", "development"), f"{path.name}: mode 非法"
        inputs = data.get("input") or {}
        assert inputs.get("paper") or inputs.get("repo"), f"{path.name}: 缺少 paper/repo 输入"
        if data["mode"] == "development":
            assert data.get("expect"), f"{path.name}: development case 必须带 expect"


# --------------------------------------------------------------------------- #
# 4. CLI 冒烟
# --------------------------------------------------------------------------- #

@case
def cli_smoke() -> None:
    help_result = run(SCRIPTS / "pipeline.py", "--help")
    assert help_result.returncode == 0, help_result.stderr
    visual_help = run(SCRIPTS / "visual_audit.py", "--help")
    assert visual_help.returncode == 0, visual_help.stderr
    assert "视觉验收" in visual_help.stdout, "visual_audit.py 缺少用途说明"
    with tempfile.TemporaryDirectory() as tmp:
        missing = run(SCRIPTS / "pipeline.py", "validate", "curriculum", tmp)
        assert missing.returncode != 0, "空工作区校验本应失败"
        assert "Traceback" not in missing.stderr, missing.stderr


# --------------------------------------------------------------------------- #
# 5. fixture 全链路
# --------------------------------------------------------------------------- #

@case
def fixture_full_chain() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "tiny-course"
        shutil.copytree(FIXTURE, ws)

        for stage in ("curriculum", "chapter-design", "narrative", "visual-storyboard"):
            result = run(SCRIPTS / "pipeline.py", "validate", stage, ws)
            assert result.returncode == 0, f"{stage}:\n{result.stdout}{result.stderr}"
            assert "0 个 blocker" in result.stdout, result.stdout
            assert "0 个问题" in result.stdout, f"fixture 必须零问题（含 warning）：\n{result.stdout}"

        build = run(SCRIPTS / "build_site.py", ws)
        assert build.returncode == 0, build.stdout + build.stderr
        site = run(SCRIPTS / "check_site.py", ws, "--no-build-check")
        assert site.returncode == 0, site.stdout + site.stderr

        # 重复 build 不得覆盖 Agent 写的定制组件
        custom = ws / "presentation/src/content/custom/S01.tsx"
        custom.write_text("export default function S01() { return <p>custom</p>; }\n", encoding="utf-8")
        rebuild = run(SCRIPTS / "build_site.py", ws)
        assert rebuild.returncode == 0, rebuild.stdout + rebuild.stderr
        assert custom.is_file() and "custom" in custom.read_text(encoding="utf-8"), "定制组件被 build 覆盖"

        estimate = run(SCRIPTS / "estimate_duration.py", ws, "--json")
        assert estimate.returncode == 0, estimate.stderr
        assert json.loads(estimate.stdout)["total"] > 0

        course = json.loads((ws / "presentation/src/content/course.json").read_text(encoding="utf-8"))
        slides = course["chapters"][0]["slides"]
        assert len(slides) == 4, slides
        assert all(str(slide["narration"]).strip() for slide in slides), "有页面缺讲稿文本"
        tokens = (ws / "presentation/src/styles/tokens.css").read_text(encoding="utf-8")
        theme = (SKILL / "assets/themes/classroom-clean/tokens.css").read_text(encoding="utf-8")
        assert tokens == theme, "tokens.css 必须是所选主题的原样拷贝"
        for script_name in ("start.sh", "start.command", "start.bat"):
            assert (ws / script_name).is_file(), f"缺少启动脚本 {script_name}"


# --------------------------------------------------------------------------- #
# 6. development init
# --------------------------------------------------------------------------- #

@case
def development_init() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        case_path = Path(tmp) / "case.yaml"
        case_path.write_text(
            "name: tiny-dev\n"
            "mode: development\n"
            f"input:\n  repo: {FIXTURE / 'source' / 'tiny-repo'}\n"
            "config: {language: zh-CN, duration: 20, depth: overview}\n"
            "expect: {no_blockers: true}\n",
            encoding="utf-8",
        )
        out = Path(tmp) / "ws"
        env = {"QIFA_CONFIG": str(Path(tmp) / "no-such-config.yaml")}
        result = run(
            SCRIPTS / "pipeline.py", "init", "--case", case_path, "--out", out, "--no-install", env=env
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "development" in result.stdout, result.stdout
        project = (out / "project.yaml").read_text(encoding="utf-8")
        assert "mode: development" in project and "stage-review" in project, project
        advance = run(SCRIPTS / "pipeline.py", "advance", "--stage", "intake", out, env=env)
        assert advance.returncode == 0, advance.stdout + advance.stderr


# --------------------------------------------------------------------------- #
# 7. 解释器与依赖契约
# --------------------------------------------------------------------------- #

@case
def deps_contract() -> None:
    from lib import deps

    result = deps.ensure(no_install=True)
    assert result["status"] == "skipped", result
    assert "内置" in result["detail"], result
    doc = (SKILL / "references" / "production-workflow.md").read_text(encoding="utf-8")
    assert "调用方解释器" in doc, "production-workflow.md 必须写明脚本在调用方解释器下运行"
    assert "不会自动接管" in doc, "production-workflow.md 必须写明 venv 不自动接管后续命令"


@case
def stage_scoped_warnings() -> None:
    """curriculum 不等于 chapter-design：提前评估“章节计划缺失”会污染降级清单。"""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        shutil.copytree(FIXTURE, ws)
        (ws / "plan" / "chapter-plan-C01.json").unlink()
        (ws / "plan" / "visual-plan.json").unlink()

        early = run(SCRIPTS / "pipeline.py", "validate", "curriculum", ws)
        assert early.returncode == 0, early.stdout + early.stderr
        assert "0 个问题" in early.stdout, f"curriculum 阶段不应评估章节计划：\n{early.stdout}"

        late = run(SCRIPTS / "validate_course.py", ws, "--stage", "chapter-design")
        assert late.returncode == 0, late.stdout + late.stderr
        assert "CHAP-MISSING" in late.stdout, late.stdout


@case
def point_length_rule() -> None:
    """讲点只放关键词：超过 42 字（公式除外）给 CHAP-TEXT 警告。"""
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "ws"
        shutil.copytree(FIXTURE, ws)
        plan_path = ws / "plan" / "chapter-plan-C01.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["slides"][0]["points"][0]["text"] = (
            "这是一条很长的讲点，它把讲稿里应该说的话全写在了页面上，应当被校验器拦下来提醒改成关键词短语。"
        )
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        long_run = run(SCRIPTS / "validate_course.py", ws, "--stage", "chapter-design")
        assert "CHAP-TEXT" in long_run.stdout, long_run.stdout

        plan["slides"][0]["points"][0]["text"] = "关键词短语"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        ok_run = run(SCRIPTS / "validate_course.py", ws, "--stage", "chapter-design")
        assert "CHAP-TEXT" not in ok_run.stdout, ok_run.stdout


@case
def sentences_splitter() -> None:
    """字幕拆分器是纯函数，用 Node 直接跑 TypeScript（类型剥离）做单元校验。"""
    node = shutil.which("node")
    if node is None:
        return  # 环境没有 Node 时跳过；其余 P0 项不依赖它
    script = (
        "import { splitSentences } from "
        + json.dumps(str(SKILL / "assets/web-template/src/content/sentences.ts"))
        + ";\n"
        "const basic = splitSentences('甲。乙！丙？');\n"
        "if (basic.length !== 3) throw new Error('句数应为 3，实际 ' + basic.length);\n"
        "const lines = splitSentences('一句话一行，行就是一条字幕。\\n第二行是第二条字幕。');\n"
        "if (lines.length !== 2) throw new Error('一句话一行应得到 2 条：' + JSON.stringify(lines));\n"
        "const long = splitSentences('这是一句很长的中文，它包含了很多个逗号，需要被自动切开，以保证字幕不超过两行显示，这里再加一点内容，让它超过八十个字，再补一些字确保够长，还差一点就够八十个字了。');\n"
        "if (long.length < 2) throw new Error('超过 80 字的行应被兜底切开');\n"
        "for (const s of long) { if (s.length > 80) throw new Error('字幕超过 80 字：' + s); }\n"
        "const merged = splitSentences('还有机器人自己的本体状态，也就是关节角、夹爪开合这类低维数字。');\n"
        "if (merged.length !== 1) throw new Error('80 字以内的句子不得被逗号切碎：' + JSON.stringify(merged));\n"
        "if (splitSentences('   ').length !== 0) throw new Error('空白应返回空数组');\n"
        "console.log('ok');\n"
    )
    result = run_exe(node, "--input-type=module", "-e", script)
    assert result.returncode == 0, result.stderr or result.stdout


@case
def template_layout_contract() -> None:
    """模板布局契约：主题不被基础样式覆盖；舞台是唯一缩放单元；字幕逐句；导航占位不遮挡。"""
    root = SKILL / "assets" / "web-template" / "src"
    base = (root / "styles" / "base.css").read_text(encoding="utf-8")
    assert "--bg:" not in base, "base.css 不得重定义主题色 token（会覆盖 themes/<id>/tokens.css）"
    for marker in (
        ".app-shell",
        ".course-column",
        ".stage-area",
        ".stage-fitter",
        ".stage-body",
        ".narration-count",
        "grid-template-columns",
        "minmax(0, 1fr)",
        "overflow: hidden",
    ):
        assert marker in base, f"base.css 缺少布局契约：{marker}"
    side_nav = re.search(r"\.side-nav\s*\{[^}]*\}", base)
    assert side_nav and "position: fixed" not in side_nav.group(0), "侧栏必须是占位列，不能是固定浮层"
    app = (root / "App.tsx").read_text(encoding="utf-8")
    for marker in ("app-shell", "course-column", "stage-body", "glossary-backdrop", "onClose"):
        assert marker in app, f"App.tsx 缺少布局契约：{marker}"
    assert "step={step}" in app, "App.tsx 必须把页内步进传给定制视觉组件"
    assert "sentence={sentence}" in app and "sentences={sentences}" in app, "App.tsx 必须把当前字幕传给定制视觉组件"
    custom_index = (root / "content" / "custom" / "index.ts").read_text(encoding="utf-8")
    assert "step: number" in custom_index, "定制视觉注册表必须声明 step 参数"
    assert "sentences: string[]" in custom_index, "定制视觉注册表必须声明 sentences 参数"
    focus_helper = (root / "content" / "custom" / "focus.ts").read_text(encoding="utf-8")
    assert "neutral" in focus_helper and "focusOf" in focus_helper, "缺少高亮语义工具（有指向才高亮，无指向保持中性）"
    web_ref = (SKILL / "references" / "web-implementation.md").read_text(encoding="utf-8")
    assert "高亮语义" in web_ref, "web-implementation.md 必须写明高亮语义"
    stage = (root / "components" / "Stage.tsx").read_text(encoding="utf-8")
    assert "stage-area" in stage and "stage-fitter" in stage, "Stage.tsx 缺少舞台三层结构"
    cursor = (root / "hooks" / "useCourseCursor.ts").read_text(encoding="utf-8")
    assert "splitSentences" in cursor and "sentence" in cursor, "游标缺少逐句逻辑"
    subtitle = (root / "components" / "Subtitle.tsx").read_text(encoding="utf-8")
    assert "narration-count" in subtitle, "字幕缺少句序指示"
    narration_text = re.search(r"\.narration-text\s*\{[^}]*\}", base)
    assert narration_text and "text-wrap" not in narration_text.group(0), "字幕不得做两行平衡对齐（一行满自动换行）"
    renderer = (root / "components" / "SlideRenderer.tsx").read_text(encoding="utf-8")
    assert "points-dense" in renderer, "密集讲点页必须走缩排渲染"
    assert ".points-dense" in base, "base.css 缺少密集讲点的缩排规则"


def main() -> int:
    failures: list[str] = []
    for fn in CASES:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 - 测试框架需要收集全部失败
            failures.append(fn.__name__)
            print(f"[FAIL] {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(CASES) - len(failures)}/{len(CASES)} 通过")
    if failures:
        print("失败：" + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
