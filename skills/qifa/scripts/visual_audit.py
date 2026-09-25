#!/usr/bin/env python3
"""无头浏览器视觉验收（可选，不阻塞流程）。

用法：
    python3 -m http.server 8791 --directory <ws>/presentation/dist &
    python3 visual_audit.py <workspace> [--base-url http://127.0.0.1:8791/] [--out <dir>]

做什么：逐页打开站点，测量「字幕条之上的内容区」是否放得下（.stage-body 不允许内滚，
元素不得越过内容区边界），可选把每页截图存到 --out。

依赖：playwright + chromium。缺失时打印「跳过」并返回 0——降级信息由调用方写入 qa-report。
发现问题（溢出/越界）返回 1，并逐页列出，与 web-implementation.md 的「视觉验收」一节配套。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

OVERFLOW_SCRIPT = """
() => {
  const body = document.querySelector('.stage-body');
  if (!body) return { missing: true };
  const bodyRect = body.getBoundingClientRect();
  const bad = [];
  for (const el of body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && (r.bottom > bodyRect.bottom + 1 || r.right > bodyRect.right + 1 || r.left < bodyRect.left - 1)) {
      bad.push((el.tagName + '.' + String(el.className)).slice(0, 80));
    }
  }
  return {
    missing: false,
    overflow: body.scrollHeight - body.clientHeight,
    badCount: bad.length,
    badSample: bad.slice(0, 4),
    title: (document.querySelector('.slide-title') || {}).textContent || ''
  };
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="无头浏览器视觉验收：逐页溢出测量与截图")
    parser.add_argument("workspace")
    parser.add_argument("--base-url", default="http://127.0.0.1:8791/")
    parser.add_argument("--out", default=None, help="截图输出目录（可选）")
    parser.add_argument("--wait-ms", type=int, default=450)
    args = parser.parse_args()

    ws = pathlib.Path(args.workspace).expanduser()
    dist_index = ws / "presentation" / "dist" / "index.html"
    if not dist_index.is_file():
        print("[跳过] 未找到 presentation/dist/index.html，先运行 npm run build")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[跳过] 未安装 playwright（pip install playwright && playwright install chromium）")
        return 0

    chapters = json.loads(dist_index.parent.parent.joinpath("src/content/course.json").read_text(encoding="utf-8"))[
        "chapters"
    ]
    out_dir = pathlib.Path(args.out).expanduser() if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    problems: list[str] = []
    checked = 0
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # noqa: BLE001 - 浏览器缺失按降级处理
            print(f"[跳过] 无法启动 chromium：{exc}")
            return 0
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        for chapter in chapters:
            chapter_number = int(str(chapter.get("id", "C0")).lstrip("C") or 0)
            for index, slide in enumerate(chapter.get("slides") or [], start=1):
                slide_id = str(slide.get("id"))
                url = f"{args.base_url}?v={slide_id}#c{chapter_number}/s{index}"
                page.goto(url, wait_until="load")
                page.wait_for_timeout(args.wait_ms)
                result = page.evaluate(OVERFLOW_SCRIPT)
                checked += 1
                if result.get("missing"):
                    problems.append(f"{slide_id}: 页面缺少 .stage-body")
                    continue
                if result["overflow"] > 0 or result["badCount"] > 0:
                    problems.append(
                        f"{slide_id} {result.get('title', '')[:24]}: 内容区溢出 {result['overflow']}px，越界元素 {result['badCount']} 个 {result['badSample']}"
                    )
                if out_dir:
                    page.screenshot(path=str(out_dir / f"{slide_id}.png"), full_page=False)
        browser.close()

    print(f"检查 {checked} 页；问题 {len(problems)} 个")
    for item in problems:
        print(f"[warning] WEB-VISUAL {item}")
    print("视觉验收通过" if not problems else "视觉验收发现排版问题（不阻塞构建，需修复或记录）")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
