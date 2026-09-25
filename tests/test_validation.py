#!/usr/bin/env python3
"""QiFa 仓库、Skill 规范与流水线校验（纯标准库；可直接运行，也兼容 pytest）。

用法：
    python3 tests/test_validation.py
    pytest tests/
"""

from __future__ import annotations

import json
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
SKILL_DIR = SKILLS_DIR / "qifa"
SCRIPTS_DIR = SKILL_DIR / "scripts"
TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
WORKSPACE_FIXTURE = FIXTURES_DIR / "workspaces" / "valid-minimal"
CASES_DIR = TESTS_DIR / "cases"

sys.path.insert(0, str(SCRIPTS_DIR))

from lib import io, minischema, miniyaml  # noqa: E402
from lib.workbench import STAGES, Workspace  # noqa: E402
import build_site  # noqa: E402
import check_site  # noqa: E402
import estimate_duration  # noqa: E402
import validate_course  # noqa: E402
import validate_sources  # noqa: E402
import validate_stage  # noqa: E402

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata"}
MAX_SKILL_LINES = 500
THEMES = ("scientific-editorial", "engineering-blueprint", "classroom-clean")
PRESETS = ("research-course", "code-onboarding", "beginner-tutorial")
SCHEMAS = (
    "project",
    "source-model",
    "course-outline",
    "chapter-plan",
    "visual-plan",
    "qa-report",
    "run-state",
)
TEMPLATE_FILES = (
    "package.json",
    "index.html",
    "vite.config.ts",
    "tsconfig.json",
    "src/main.tsx",
    "src/App.tsx",
    "src/types.ts",
    "src/hooks/useCourseCursor.ts",
    "src/hooks/useStageScale.ts",
    "src/components/Stage.tsx",
    "src/components/SlideRenderer.tsx",
    "src/components/Subtitle.tsx",
    "src/components/GlossaryCard.tsx",
    "src/components/CodeWalkthrough.tsx",
    "src/components/FormulaSteps.tsx",
    "src/components/ChartZoom.tsx",
    "src/components/VideoEmbed.tsx",
    "src/content/custom/index.ts",
)


# --------------------------------------------------------------------------- #
# Skill 规范校验（也用于 tests/fixtures 的正反例）
# --------------------------------------------------------------------------- #

def read_frontmatter(skill_md: Path) -> tuple[dict[str, str], str]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md 必须以 YAML frontmatter 开头")
    frontmatter: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"无法解析 frontmatter 行：{line!r}")
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        frontmatter[key.strip()] = value
    return frontmatter, text


def validate_skill(skill_dir: Path) -> list[str]:
    problems: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"缺少 {skill_md}"]
    try:
        frontmatter, text = read_frontmatter(skill_md)
    except ValueError as exc:
        return [f"{skill_md}: {exc}"]

    unknown = set(frontmatter) - ALLOWED_KEYS
    if unknown:
        problems.append(f"frontmatter 含未知字段：{sorted(unknown)}")

    name = frontmatter.get("name", "")
    if not name:
        problems.append("frontmatter 缺少 name")
    else:
        if not NAME_PATTERN.fullmatch(name):
            problems.append(f"name {name!r} 必须为小写字母/数字/单个连字符")
        if len(name) > 64:
            problems.append(f"name 长度 {len(name)} 超过 64")
        if name != skill_dir.name:
            problems.append(f"name {name!r} 与目录名 {skill_dir.name!r} 不一致")

    description = frontmatter.get("description", "")
    if not description:
        problems.append("frontmatter 缺少 description")
    else:
        if len(description) > 1024:
            problems.append("description 超过 1024 字符")
        if "<" in description or ">" in description:
            problems.append("description 不能包含尖括号")

    if len(text.splitlines()) > MAX_SKILL_LINES:
        problems.append(f"SKILL.md 超过 {MAX_SKILL_LINES} 行")

    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = target.strip().split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            continue
        if not (skill_md.parent / target).exists():
            problems.append(f"相对链接不存在：{target}")
    return problems


def validate_openai_yaml(skill_dir: Path, skill_name: str) -> list[str]:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.is_file():
        return [f"缺少 {path}"]
    problems: list[str] = []
    interface: dict[str, str] = {}
    in_interface = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            in_interface = raw.split(":", 1)[0].strip() == "interface"
            continue
        if not in_interface:
            continue
        key, _, value = raw.strip().partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        interface[key.strip()] = value

    if not interface.get("display_name"):
        problems.append("display_name 缺失")
    short = interface.get("short_description", "")
    if not 25 <= len(short) <= 64:
        problems.append(f"short_description 需 25-64 字符，当前 {len(short)}")
    prompt = interface.get("default_prompt", "")
    if not prompt:
        problems.append("default_prompt 缺失")
    elif f"${skill_name}" not in prompt:
        problems.append(f"default_prompt 必须提及 ${skill_name}")
    return problems


# --------------------------------------------------------------------------- #
# 仓库与 Skill
# --------------------------------------------------------------------------- #

def test_仓库根文件齐全():
    for filename in ("README.md", "LICENSE", "THIRD_PARTY_LICENSES", ".gitignore"):
        assert (REPO_ROOT / filename).is_file(), f"缺少仓库根文件 {filename}"


def test_仓库只有一个技能():
    skills = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
    assert [path.name for path in skills] == ["qifa"], f"skills/ 下应为唯一的 qifa，实际 {skills}"


def test_skill通过规范校验():
    problems = validate_skill(SKILL_DIR)
    assert problems == [], "\n".join(problems)


def test_校验器拒绝大写名称():
    problems = validate_skill(FIXTURES_DIR / "bad-name")
    assert any("name" in problem for problem in problems), problems


def test_校验器拒绝缺少描述():
    problems = validate_skill(FIXTURES_DIR / "missing-description")
    assert any("description" in problem for problem in problems), problems


def test_openai_yaml通过校验():
    frontmatter, _ = read_frontmatter(SKILL_DIR / "SKILL.md")
    problems = validate_openai_yaml(SKILL_DIR, frontmatter.get("name", ""))
    assert problems == [], "\n".join(problems)


def test_skill无TODO占位():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "TODO" not in text


def test_引用文件齐全():
    references = {path.name for path in (SKILL_DIR / "references").glob("*.md")}
    expected = {
        "production-workflow.md",
        "development-workflow.md",
        "intake.md",
        "paper-analysis.md",
        "code-analysis.md",
        "curriculum-design.md",
        "chapter-design.md",
        "narrative-design.md",
        "visual-design.md",
        "web-implementation.md",
        "quality-rubrics.md",
    }
    assert expected <= references, f"缺少 references：{sorted(expected - references)}"


# --------------------------------------------------------------------------- #
# schemas / presets / themes / template
# --------------------------------------------------------------------------- #

def test_schemas可解析():
    for name in SCHEMAS:
        path = SKILL_DIR / "references" / "schemas" / f"{name}.schema.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("title"), f"{name} 缺少 title"
        assert data.get("$schema", "").endswith("2020-12/schema"), f"{name} 未声明 2020-12"


def test_presets可解析():
    for preset in PRESETS:
        path = SKILL_DIR / "assets" / "presets" / f"{preset}.yaml"
        data = miniyaml.loads(path.read_text(encoding="utf-8"))
        assert data["id"] == preset
        assert data["visual_style"] in THEMES
        assert isinstance(data["duration_minutes"], int)


def test_主题齐全():
    for theme in THEMES:
        theme_dir = SKILL_DIR / "assets" / "themes" / theme
        meta = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
        assert meta["id"] == theme
        assert (theme_dir / "tokens.css").is_file()


def test_模板文件齐全():
    template = SKILL_DIR / "assets" / "web-template"
    for relative in TEMPLATE_FILES:
        assert (template / relative).is_file(), f"模板缺少 {relative}"


def test_脚本可编译():
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(SCRIPTS_DIR.rglob("*.py")):
            cfile = Path(tmp) / (path.stem + ".pyc")
            py_compile.compile(str(path), cfile=str(cfile), doraise=True)


# --------------------------------------------------------------------------- #
# 内置最小实现
# --------------------------------------------------------------------------- #

def test_miniyaml往返():
    data = {
        "mode": "development",
        "stop_after": "curriculum",
        "learner": {"audience": "研究生", "level": "intermediate", "prerequisites": ["Python 基础"]},
        "chapters": [
            {"id": "C01", "slides": [{"id": "S01", "kind": "concept"}], "ok": True},
            {"id": "C02", "slides": [], "ok": False},
        ],
        "duration": 45,
        "ratio": 0.5,
        "none": None,
        "inline": {"a": 1, "b": [1, 2, 3]},
    }
    text = miniyaml.dumps(data)
    assert miniyaml.loads(text) == data
    inline = miniyaml.loads('config: {language: zh-CN, duration: 20}\nlist: [a, b, c]\n')
    assert inline == {"config": {"language": "zh-CN", "duration": 20}, "list": ["a", "b", "c"]}


def test_minischema正反例():
    schema = {
        "type": "object",
        "required": ["name"],
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "pattern": "^[a-z]+$"},
            "items": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/item"}},
        },
        "$defs": {"item": {"type": "object", "required": ["id"], "properties": {"id": {"type": "integer"}}}},
    }
    assert minischema.validate({"name": "ok", "items": [{"id": 1}]}, schema) == []
    errors = minischema.validate({"name": "BAD", "items": [{}], "extra": 1}, schema)
    assert len(errors) >= 3, errors


# --------------------------------------------------------------------------- #
# 工作区夹具与流水线
# --------------------------------------------------------------------------- #

def test_工作区夹具通过全部阶段校验():
    ws = Workspace(WORKSPACE_FIXTURE)
    for stage in STAGES:
        problems = validate_stage.check(ws, stage)
        blockers = [problem for problem in problems if problem["severity"] == "blocker"]
        assert blockers == [], f"{stage}: {blockers}"


def test_来源课程站点校验无blocker():
    ws = Workspace(WORKSPACE_FIXTURE)
    for name, problems in (
        ("validate_sources", validate_sources.check(ws)),
        ("validate_course", validate_course.check(ws, stage="package")),
        ("check_site", check_site.check(ws, require_build=True)),
    ):
        blockers = [problem for problem in problems if problem["severity"] == "blocker"]
        assert blockers == [], f"{name}: {blockers}"


def test_时长统计():
    result = estimate_duration.estimate(Workspace(WORKSPACE_FIXTURE))
    assert result["total"] > 0
    assert len(result["per_chapter"]) == 1
    assert result["rate"]["zh_chars_per_minute"] == 240


def test_build_site生成站点():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "ws"
        shutil.copytree(WORKSPACE_FIXTURE, target)
        ws = Workspace(target)
        problems = build_site.build(ws)
        blockers = [problem for problem in problems if problem["severity"] == "blocker"]
        assert blockers == [], blockers
        assert (target / "presentation" / "src" / "content" / "course.json").is_file()
        assert (target / "presentation" / "src" / "content" / "narrations.json").is_file()
        assert (target / "presentation" / "src" / "styles" / "tokens.css").is_file()
        assert (target / "start.sh").is_file() and (target / "start.bat").is_file()
        course = io.load_json(target / "presentation" / "src" / "content" / "course.json")
        assert course["chapters"][0]["slides"][0]["narration"]


def test_负例缺文件被拦截():
    with tempfile.TemporaryDirectory() as tmp:
        problems = validate_stage.check(Workspace(tmp), "intake")
        assert any(problem["severity"] == "blocker" for problem in problems)


def test_pipeline_init与推进():
    with tempfile.TemporaryDirectory() as tmp:
        ws_dir = Path(tmp) / "ws"
        init = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "pipeline.py"),
                "init",
                "--input",
                "paper:tests/fixtures/papers/tiny-paper.tex",
                "--out",
                str(ws_dir),
                "--no-install",
                "--json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert init.returncode == 0, init.stderr
        assert (ws_dir / "project.yaml").is_file()
        assert (ws_dir / ".qifa" / "run-state.yaml").is_file()

        validate = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "pipeline.py"), "validate", "intake"],
            cwd=ws_dir,
            capture_output=True,
            text=True,
        )
        assert validate.returncode == 0, validate.stdout + validate.stderr

        advance = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "pipeline.py"), "advance", "--stage", "intake"],
            cwd=ws_dir,
            capture_output=True,
            text=True,
        )
        assert advance.returncode == 0, advance.stdout + advance.stderr
        state = io.load_yaml(ws_dir / ".qifa" / "run-state.yaml")
        assert state["stage"] == "source-analysis"
        assert state["stages"]["intake"]["status"] == "validated"


def test_cases与不变量齐全():
    cases = sorted(CASES_DIR.glob("*.yaml"))
    assert [path.stem for path in cases] == [
        "paper-basic",
        "paper-math-heavy",
        "repository-fullstack",
        "repository-small",
    ]
    for path in cases:
        data = miniyaml.loads(path.read_text(encoding="utf-8"))
        assert data["mode"] == "development"
        assert data.get("stop_after") in STAGES
        assert "expect" in data
        invariant = TESTS_DIR / "expected-invariants" / f"{path.stem}.md"
        assert invariant.is_file(), f"缺少不变量文档：{invariant.name}"


# --------------------------------------------------------------------------- #
# 运行器（零依赖直接执行）
# --------------------------------------------------------------------------- #

def main() -> int:
    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, func in tests:
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - 直接运行时展示全部失败
            failed += 1
            print(f"FAIL   {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS   {name}")
    print(f"\n共 {len(tests)} 项检查，{failed} 项失败。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
