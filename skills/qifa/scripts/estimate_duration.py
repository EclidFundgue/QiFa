#!/usr/bin/env python3
"""讲稿字数与时长统计。

中文按“汉字数 ÷ zh_chars_per_minute”，英文按“单词数 ÷ en_words_per_minute”；
代码块、行内代码与公式不计入。系数默认 240 字/分钟、130 词/分钟，可在
project.yaml 的 speaking_rate 覆盖。

用法：python3 estimate_duration.py <workspace> [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.workbench import Workspace  # noqa: E402

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.DOTALL)
HAN_RE = re.compile(r"[\u3400-\u9fff]")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def clean(text: str) -> str:
    text = FENCE_RE.sub(" ", text)
    text = MATH_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    return text


def chapter_text(ws: Workspace) -> dict[str, str]:
    result: dict[str, str] = {}
    for chapter_id, script in ws.load_scripts().items():
        result[chapter_id] = clean(script["text"])
    return result


def estimate(ws: Workspace) -> dict:
    rate = ws.speaking_rate()
    per_chapter: list[dict] = []
    for chapter_id, text in sorted(chapter_text(ws).items()):
        chars = len(HAN_RE.findall(text))
        words = len(WORD_RE.findall(text))
        minutes = chars / float(rate["zh_chars_per_minute"]) + words / float(rate["en_words_per_minute"])
        per_chapter.append(
            {
                "chapter_id": chapter_id,
                "chars": chars,
                "words": words,
                "minutes": round(minutes, 1),
            }
        )
    total = round(sum(item["minutes"] for item in per_chapter), 1)
    return {"rate": rate, "per_chapter": per_chapter, "total": total}


def main() -> int:
    parser = argparse.ArgumentParser(description="统计讲稿字数与估算时长")
    parser.add_argument("workspace")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = estimate(Workspace(args.workspace))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    for item in result["per_chapter"]:
        print(f"{item['chapter_id']}: {item['chars']} 汉字 + {item['words']} 词 ≈ {item['minutes']} 分钟")
    print(f"合计 ≈ {result['total']} 分钟（中文 {result['rate']['zh_chars_per_minute']} 字/分，英文 {result['rate']['en_words_per_minute']} 词/分）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
