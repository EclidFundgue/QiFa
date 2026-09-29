# P1 案例：openpi-repo

- 案例定义：`tests/cases/openpi-repo.yaml`（development 模式，git URL `https://github.com/Physical-Intelligence/openpi`，45 分钟，engineering-blueprint）
- 运行记录：
  - round1：工作区 `qifa-output/openpi_round1`（2026-09-25，39.3 分钟，0 blocker/warning）
  - round2：工作区 `qifa-output/openpi_round2`（2026-09-25，46.4 分钟，0 blocker/warning/info→语义 4 条 info，0 降级）
  - round3：工作区 `D:\papers\qifa-output\openpi-repo`（2026-09-25，38.6 分钟，0 blocker/warning，语义 4 条 info 已 accepted，0 降级；系统 Edge 无头验收 38/38）

## expect 不变量（round3，`pipeline.py report --case tests/cases/openpi-repo.yaml <ws>`）

- [x] `no_blockers`：全阶段 blocker 0；`package` 完成时 9 个阶段全部 `validated`，`attempts=0`、`degradations=0`
- [x] `stages_done`：intake → source-analysis → curriculum → chapter-design → narrative → visual-storyboard → web-generation → automated-review → package
- [x] `outline`：7 章（5–7 内）；5 条学习目标全部有章节承接；38 页；讲稿 38.6 分钟（目标 45，-14.2%，容差内）

## round3 发现与固化

round3 共 3 条工程性发现，全部落到脚本 / reference / tests：

1. 中文 Windows 下 `build_site.py --npm-build` 按平台默认编码（GBK）解码 npm 输出，reader 线程抛 `UnicodeDecodeError` → `scripts/build_site.py:_run_npm` 显式 `encoding="utf-8", errors="replace"`；`tests::npm_output_encoding`
2. `visual_audit.py` 只能启动 playwright 自带 chromium，系统有 Edge 时也无法验收 → 新增 `--browser auto|chromium|msedge|chrome`（auto 依次回退）；`references/web-implementation.md`；`tests::cli_smoke` 断言
3. P0 `sentences_splitter` 用裸 Windows 绝对路径做 Node ESM 导入说明符 → `Path.as_uri()`；`tests::sentences_splitter`

round3 新增约定：文字页（concept/comparison/summary）与代码页分别由 `PointFlow` 与 `CodeFlow` 承担，`CodeFlow` 按字幕关键词高亮讲点、按 steps 压暗未到分组；组件已回收进模板 `assets/web-template/src/content/custom/CodeFlow.tsx`（`web-implementation.md` 同步说明），工作区只保留注册与课程特有组件。

## 历史（round2 汇总）

round2 共 9 条发现，全部落到 reference / validator / template / tests：

1. 拆句主权在写稿（一句话一行）→ `narrative-design.md`、`web-implementation.md`、`sentences.ts`、`tests::sentences_splitter`
2. 定制视觉跟随字幕（`sentence/sentences` 传入）→ 模板 `App.tsx`、`custom/index.ts`、`tests::template_layout_contract`
3. 高亮语义三态（有指向才 accent；无指向中性）→ 模板 `custom/focus.ts`、`web-implementation.md`、`tests::template_layout_contract`
4. 页面文字凝练成关键词 + 文本页示意图 → `chapter-design.md`、`web-implementation.md`、`validate_course.py`（`CHAP-TEXT`）、`tests::point_length_rule`、模板 `custom/PointFlow.tsx`
5. 字幕不做两行平衡对齐 → `base.css`、`web-implementation.md`、`tests::template_layout_contract`
6. 密集讲点自动缩排（4+ 条）→ `SlideRenderer.tsx`、`base.css`、`tests::template_layout_contract`
7. 无头浏览器视觉验收（round1 的“无浏览器”结论不成立）→ `scripts/visual_audit.py`、`web-implementation.md`、`tests::cli_smoke`
8. 定制 TSX 不得越出内容区（约 1136×552）→ `web-implementation.md` + 逐页 `visual_audit`
9. 模板生成物与 Agent 产物分离（继承 round1）→ 仍由 `tests::fixture_full_chain` 的“重跑 build_site 不覆盖 custom”保证

## 回归

- `python3 tests/test_validation.py`：13/13（含 fixture 全链路、`npm_output_encoding`、`visual_audit` CLI、`CHAP-TEXT`、字幕拆分与布局契约）
- round3 视觉验收：`visual_audit.py` 38/38 页通过（无溢出、无越界，浏览器为系统 Edge）
- 讲稿时长：38.6 分钟；大纲声明与实测一致（差异 0 分钟内）

