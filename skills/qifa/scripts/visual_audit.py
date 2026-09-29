#!/usr/bin/env python3
"""无头浏览器视觉验收（可选，不阻塞流程）。

用法：
    python3 -m http.server 8791 --directory <ws>/presentation/dist &
    python3 visual_audit.py <workspace> [--base-url http://127.0.0.1:8791/] [--out <dir>] [--browser auto|chromium|msedge|chrome]

做什么：逐页打开站点，测量「字幕条之上的内容区」是否放得下（.stage-body 不允许内滚，
元素不得越过内容区边界），可选把每页截图存到 --out。

先做一致性守卫：用工作区 course.json 里的页面标题核对被服务的站点，防止端口被占用时
审计打到别的课程 / 旧构建上给出假通过（返回码 2 表示站点与工作区不匹配）。

依赖：playwright + 浏览器。浏览器按 `--browser` 选择：`auto`（默认）依次尝试
playwright 自带的 chromium、系统 Edge、系统 Chrome；playwright 包缺失或全部浏览器
启动失败时才打印「跳过」并返回 0——降级信息由调用方写入 qa-report。
发现问题（溢出/越界）返回 1，并逐页列出，与 web-implementation.md 的「视觉验收」一节配套。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys

BROWSER_CANDIDATES: dict[str, list[str | None]] = {
    "msedge": [
        os.environ.get("MSEDGE_PATH"),
        shutil.which("msedge"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/microsoft-edge",
    ],
    "chrome": [
        os.environ.get("CHROME_PATH"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
    ],
}


def find_browser(name: str) -> str | None:
    for candidate in BROWSER_CANDIDATES.get(name, []):
        if candidate and pathlib.Path(candidate).is_file():
            return candidate
    return None


def launch_browser(playwright, browser: str):
    """返回 (browser, 说明) 或 (None, 错误说明)；auto 按 chromium → msedge → chrome 顺序回退。"""
    attempts: list[tuple[str, str | None]] = []
    if browser in ("auto", "chromium"):
        attempts.append(("chromium", None))
    for name in ("msedge", "chrome"):
        if browser in ("auto", name):
            attempts.append((name, find_browser(name)))
    errors: list[str] = []
    for name, executable in attempts:
        if name != "chromium" and executable is None:
            errors.append(f"{name}: 未找到可执行文件")
            continue
        kwargs: dict = {"args": ["--no-sandbox"]}
        if executable:
            kwargs["executable_path"] = executable
        try:
            return playwright.chromium.launch(**kwargs), f"{name}（{executable or 'playwright 内置'}）"
        except Exception as exc:  # noqa: BLE001 - 逐个回退，最后统一降级
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    return None, "；".join(errors)

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
    parser.add_argument(
        "--browser",
        default="auto",
        choices=["auto", "chromium", "msedge", "chrome"],
        help="浏览器选择：auto 依次尝试内置 chromium / 系统 Edge / 系统 Chrome",
    )
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
        browser, detail = launch_browser(p, args.browser)
        if browser is None:
            print(f"[跳过] 无法启动浏览器（{detail}）")
            return 0
        print(f"[浏览器] {detail}")
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        expected_titles = [
            str(slide.get("title"))
            for chapter in chapters
            for slide in chapter.get("slides") or []
        ]
        page.goto(f"{args.base_url}?v=fingerprint#c1/s1", wait_until="load")
        page.wait_for_timeout(args.wait_ms)
        body_text = page.inner_text("body")
        missing = [title for title in expected_titles[:8] if title and title not in body_text]
        if missing:
            print("[错误] 站点与工作区不匹配：页面里找不到本工作区的页面标题。")
            print(f"  - 期望（示例）：{'；'.join(missing[:3])}")
            print(f"  - 实际地址：{args.base_url}")
            print("  - 请确认 http.server 指向 <workspace>/presentation/dist，且刚重新构建过（端口被占用会打到别的站点）。")
            browser.close()
            return 2
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
