#!/usr/bin/env python3
"""高亮检查（规则见 references/highlight-rules.md）。

用法：python3 highlight_audit.py <workspace> [--json]

做什么：对每个带 `custom/<slide-id>.tsx` 的页面，解析组件里的
`const detect = detector(rules, stops, neutrals);`，用 `course.json` 的逐句讲稿
重放 `focusAt` 的判定，输出每页的焦点序列，并报告硬约束违规：

- 讲点从未被高亮（讲稿里找不到可命中的短语，常见于"points 写成整句话"）；
- STOP 之后仍出现焦点（结构讲完后被复活）。

回指已讲元素只作为 info 提示：运行期会保持当前焦点，不改变高亮结果。

只覆盖使用 `detector(...)` 的定制组件；`PointFlow` 等动态检测器按文档清单人工检查。
退出码：0 通过；1 有违规；2 用法/数据问题。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STOP = -1
NEUTRAL = -2
POINTFLOW_KINDS = {"title", "concept", "comparison", "summary"}
TOKEN_SPLIT = re.compile(r"[\s、，。：；/（）()·+×→←|]+")
TOKEN_TRIM = re.compile(r"^[^\u4e00-\u9fffA-Za-z0-9_]+|[^\u4e00-\u9fffA-Za-z0-9_.-]+$")


def tokens_of(text: str) -> list[str]:
    cleaned = re.sub(r"\$[^$]*\$", " ", text)
    result = []
    for part in TOKEN_SPLIT.split(cleaned):
        part = TOKEN_TRIM.sub("", part)
        if len(part) >= 2:
            result.append(part)
    return result


def pointflow_detector(points: list[dict]):
    """复刻模板 PointFlow：特征词（跨讲点去重）+ 最长命中优先 + 过渡句终止。"""
    lists = [tokens_of(str(point.get("text") or "")) for point in points]
    keep: list[list[str]] = []
    for index, tokens in enumerate(lists):
        unique = [
            token
            for token in tokens
            if not any(token in other for other_index, other in enumerate(lists) if other_index != index)
        ]
        keep.append(unique if unique else tokens)

    def detect(text: str):
        if not text:
            return None
        if re.search(r"下一页|下一章|谢谢", text):
            return STOP
        best: int | None = None
        best_length = 0
        for index, tokens in enumerate(keep):
            for token in tokens:
                if token in text and len(token) > best_length:
                    best = index
                    best_length = len(token)
        return best

    return detect


def split_args(text: str) -> list[str]:
    args: list[str] = []
    depth = 0
    current = ""
    for char in text:
        if char == "[":
            depth += 1
        if char == "]":
            depth -= 1
        if char == "," and depth == 0:
            args.append(current.strip())
            current = ""
            continue
        current += char
    if current.strip():
        args.append(current.strip())
    return args


def load_detector(path: Path):
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"const detect = detector\((.*?)\);", text, re.S)
    if not match:
        return None
    try:
        rules, stops, neutrals = [json.loads(arg) for arg in split_args(match.group(1))]
    except json.JSONDecodeError:
        return None

    def detect(sentence_text: str):
        for word in stops:
            if word in sentence_text:
                return STOP
        for word in neutrals:
            if word in sentence_text:
                return NEUTRAL
        for word, index in rules:
            if word in sentence_text:
                return index
        return None

    return detect


def focus_at(sentences: list[str], sentence: int, detect) -> int | None:
    focus: int | None = None
    max_focus = -1
    stopped = False
    for i in range(sentence + 1):
        hit = detect(sentences[i])
        if hit == STOP:
            stopped = True
            focus = None
            continue
        if stopped or hit is None:
            continue
        if hit == NEUTRAL:
            if i == sentence:
                focus = None
            continue
        if hit < max_focus:
            continue  # 回指已讲过的元素：保持当前焦点，不二次聚焦
        focus = hit
        max_focus = hit
    return focus


def audit(ws: Path) -> tuple[list[dict], list[str], list[str]]:
    course_path = ws / "presentation" / "src" / "content" / "course.json"
    if not course_path.is_file():
        print(f"[错误] 找不到 {course_path}，先运行 build_site.py", file=sys.stderr)
        return [], ["缺少 course.json"], []
    course = json.loads(course_path.read_text(encoding="utf-8"))
    custom_dir = ws / "presentation" / "src" / "content" / "custom"

    pages: list[dict] = []
    problems: list[str] = []
    notes: list[str] = []
    for chapter in course.get("chapters") or []:
        for slide in chapter.get("slides") or []:
            slide_id = str(slide.get("id"))
            sentences = [line.strip() for line in str(slide.get("narration") or "").splitlines() if line.strip()]
            detect = load_detector(custom_dir / f"{slide_id}.tsx")
            mode = "component"
            if detect is None:
                if str(slide.get("kind")) not in POINTFLOW_KINDS:
                    continue
                detect = pointflow_detector(slide.get("points") or [])
                mode = "pointflow"
            sequence = [focus_at(sentences, i, detect) for i in range(len(sentences))]
            pages.append({"slide_id": slide_id, "mode": mode, "sequence": sequence, "sentences": sentences})
            hits: list[int] = []
            stopped = False
            for index, sentence_text in enumerate(sentences):
                hit = detect(sentence_text)
                if hit == STOP:
                    stopped = True
                    continue
                if hit is None or hit == NEUTRAL:
                    continue
                if stopped:
                    problems.append(f"{slide_id} STOP 之后仍有焦点命中（第 {index + 1} 句：{sentence_text[:24]}）")
                    continue
                if hits and hit < hits[-1]:
                    notes.append(
                        f"{slide_id} 回指已讲元素：第 {index + 1} 句命中 {hit}（已讲过 {hits[-1]}）；运行期保持当前焦点（{sentence_text[:24]}）"
                    )
                hits.append(hit)
            if mode == "pointflow":
                for index in range(len(slide.get("points") or [])):
                    if index not in hits:
                        problems.append(f"{slide_id} 讲点 {index + 1} 从未被高亮（讲稿里找不到可命中的短语）")
    return pages, problems, notes


def main() -> int:
    parser = argparse.ArgumentParser(description="逐页重放高亮判定，检查是否违反高亮规则（误用检查）")
    parser.add_argument("workspace")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="只打印问题与新序列摘要")
    args = parser.parse_args()

    pages, problems, notes = audit(Path(args.workspace).expanduser())
    if not pages:
        print("没有可检查的定制组件（detector 规则），请按 references/highlight-rules.md 的清单人工检查。")
        return 0
    if args.json:
        print(json.dumps({"pages": pages, "problems": problems, "notes": notes}, ensure_ascii=False, indent=2))
    else:
        if not args.quiet:
            for page in pages:
                sequence = " ".join("·" if value is None else str(value) for value in page["sequence"])
                print(f"{page['slide_id']}: {sequence}")
        print(f"检查 {len(pages)} 页；违反规则 {len(problems)} 条；回指提示 {len(notes)} 条")
        for item in problems:
            print(f"[warning] HIGHLIGHT {item}")
        for item in notes:
            print(f"[info] HIGHLIGHT {item}")
        print("高亮检查通过" if not problems else "高亮检查发现问题（按 references/highlight-rules.md 修复）")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
