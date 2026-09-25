# P1 案例：openpi-repo

- 案例定义：`tests/cases/openpi-repo.yaml`（development 模式，本地仓库 `/home/ls/projects/openpi`，45 分钟，engineering-blueprint）
- 运行记录：
  - round1：工作区 `qifa-output/openpi_round1`（2026-09-25，39.3 分钟，0 blocker/warning）
  - round2：工作区 `qifa-output/openpi_round2`（2026-09-25，46.4 分钟，0 blocker/warning/info→语义 4 条 info，0 降级）

## expect 不变量（round2，`pipeline.py report --case tests/cases/openpi-repo.yaml <ws>`）

- [x] `no_blockers`：全阶段 blocker 0；`package` 完成时 9 个阶段全部 `validated`，`attempts=0`、`degradations=0`
- [x] `stages_done`：intake → source-analysis → curriculum → chapter-design → narrative → visual-storyboard → web-generation → automated-review → package
- [x] `outline`：6 章（5–7 内）；5 条学习目标全部有章节承接；42 页；讲稿 46.4 分钟（目标 45，+3.1%，容差内）

## 人工评审发现与固化（development 模式汇总）

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

- `python3 tests/test_validation.py`：12/12（含 fixture 全链路、`visual_audit` CLI、`CHAP-TEXT`、字幕拆分与布局契约）
- round2 视觉验收：`visual_audit.py` 42/42 页通过（无溢出、无越界）
- 讲稿时长：46.4 分钟；大纲声明与实测一致（差异 0.2 分钟内）
