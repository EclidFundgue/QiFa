# P1 案例：pir2-paper

- 案例定义：`tests/cases/pir2-paper.yaml`（development 模式，论文 arXiv:2607.26055 + 官方实现 `pi-r2-flow/pi-r2-flow`，45 分钟，engineering-blueprint）
- 运行记录：工作区 `qifa-output/pir2-paper`（2026-09-28，39.0 分钟讲稿，0 blocker / 0 warning / 0 降级）

## expect 不变量（`pipeline.py report <ws> --case tests/cases/pir2-paper.yaml`）

- [x] `no_blockers`：全阶段 blocker 0；9 个阶段全部 `validated`，`attempts=0`、`degradations=0`
- [x] `stages_done`：intake → source-analysis → curriculum → chapter-design → narrative → visual-storyboard → web-generation → automated-review → package
- [x] `outline`：6 章（5–7 内）；5 条学习目标全部有章节承接；39 页；讲稿 39.0 分钟（目标 45，容差 30% 内）

## 人工评审发现与固化（development 模式汇总）

1. 来源边界要显式标注（仿真训练代码未发布、部署代码的未支持路径）→ `source/source-model.json` notes + C05/C06 讲稿（已应用）
2. 讲点与讲稿措辞必须互相可命中（PointFlow 高亮预检发现 14 页不可达）→ 讲点用讲稿原词；预检脚本复刻 `pointflow_detector`（已应用）
3. 模板 `PointFlow.tsx` 遗留未使用变量导致 `tsc` 失败（模板侧已修复，工作区同步）
4. 默认渲染器大图页溢出（S34/S35/S37）→ 大图页定制组件 + `img max-height`；规则固化到 `references/web-implementation.md`（已应用）
5. 论文图表引用必须核对到 PDF 物理页与图表编号（本案例把 LaTeX 编号与 PDF 编号的差异逐条核对后引用）

## 回归

- `python3 tests/test_validation.py`：13/13 通过（含 `template_layout_contract` 与 skill 自检）
- `visual_audit.py`：39/39 页通过（无溢出、无越界；截图 `review/screenshots/`）
- `highlight_audit.py`：37 页 0 违规（7 条回指 info，按规则保持焦点）
- `check_site.py`：0 问题；`npm run build` 通过
