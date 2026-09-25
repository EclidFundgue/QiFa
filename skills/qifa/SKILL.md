---
name: qifa
description: 把论文（本地 PDF、arXiv URL、arXiv LaTeX 源码、本地 LaTeX 工程、DOCX、网页文章）和/或代码库（本地路径、git URL）做成 PPT 式可视化讲解网页课程：chapter 到 slide 到 step 三级、16:9 网页、课堂口语讲稿与可开关字幕、术语卡、公式分步、代码走读、图表放大、可选视频嵌入，并带自动质检与有界修复。当用户要求把论文或代码库做成讲解课件、教学网页、PPT 式课程、可视化讲义，或要求讲透某篇论文/某个仓库时使用。默认 production 模式：开头一次确认、中途不打断；仅当用户明确要求运行开发模式或停在某个阶段时进入 development 模式。
license: MIT
---

# QiFa

把论文和/或代码库做成 PPT 式可视化讲解网页课程。本文件是入口：先读"核心约束"，按"路由"读对应 reference，再执行。

## 核心约束（不可协商）

1. **默认 production 模式**：开头一次确认需求（见 `references/intake.md`），之后全程不向用户提问；只有用户明确说"开发模式 / 停在某阶段 / 测试某阶段"时才进入 development。
2. **生成由 Agent 完成，脚本无 LLM**：`scripts/pipeline.py` 只做初始化、状态、校验、汇总；每阶段"产出 → `validate` → `advance`"。
3. **每阶段产物必须过确定性校验才能推进**；`blocker` 最多修复 2 次（`advance` 失败即计一次），仍失败则终止并说明；`warning` 降级发布并写入 `review/qa-report.md`。
4. **不修改用户仓库**：代码库一律只读；本地路径不复制，git URL 只做浅克隆。
5. **不夸大来源**：论文贡献以原文为依据，不确定就标注不确定性；引用必须真实存在（论文编号 + 页码，代码 `path:符号`）。
6. **视觉/动效登记制**：任何动画、视频、图示必须在 `plan/visual-plan.json` 登记教学目的；无登记不得进课件。不设数量配额。
7. **范围守卫**：不做 TTS/配音、录屏与视频合成、练习与自测、代码沙箱、后台类 Web App、修改用户仓库。
8. 修改本 Skill 后必须运行 `python3 tests/test_validation.py` 并保持通过。

## 路由

| 任务 | 先读 | 再执行 |
| --- | --- | --- |
| 生产模式流程与阶段循环 | `references/production-workflow.md` | `scripts/pipeline.py` |
| 开发模式、阶段评审与反馈固化 | `references/development-workflow.md` | `tests/cases/*.yaml` |
| 开头确认、默认配置、相关性判断 | `references/intake.md` | `pipeline.py init` |
| 论文解析与资产提取 | `references/paper-analysis.md` | `validate_sources.py` |
| 代码库 digest 与讲法 | `references/code-analysis.md` | `validate_sources.py` |
| 课程目标、先修、章节与时长预算 | `references/curriculum-design.md` | `validate_course.py` |
| slide/step 结构与覆盖检查 | `references/chapter-design.md` | `validate_course.py` |
| 讲稿、字幕、术语表 | `references/narrative-design.md` | `validate_course.py`、`estimate_duration.py` |
| 主题、视觉与视频嵌入 | `references/visual-design.md` | `validate_course.py` |
| 网页实现与构建 | `references/web-implementation.md` | `build_site.py`、`check_site.py` |
| 质检 rubric、严重级与修复 | `references/quality-rubrics.md` | `pipeline.py report` |
| 数据结构 | `references/schemas/*.schema.json` | `validate_stage.py` |

## 工作流（production）

1. **intake**：收集输入与 5 项确认；能推断的不问；缺失字段用默认值并记录。`pipeline.py init` 建工作区；写 `00-intake.md`。
2. **source-analysis**：按 `paper-analysis.md` / `code-analysis.md` 抽取并写 `source/source-model.json`；论文与代码混合时先判定相关性（`relevance`），不相关按 intake 记录的用户选择处理。
3. **curriculum**：写 `plan/course-outline.json`（学习目标、先修、章节、时长预算）。
4. **chapter-design**：写 `plan/chapter-plan.json`（章节 → slide → step，讲点与可选引用）。
5. **narrative**：写 `script/NN-<chapter-id>.md`（按 slide 锚点的课堂口语讲稿）+ 术语表。
6. **visual-storyboard**：写 `plan/visual-plan.json`（登记每个视觉的教学目的与资产）。
7. **web-generation**：`build_site.py` 从 `assets/web-template` 生成 `presentation/`，再补章节数据与定制 TSX；`npm run build` 必须通过。
8. **automated-review**：`pipeline.py report` 汇总确定性检查 + 按 `quality-rubrics.md` 做语义评审；blocker 修复最多 2 次。
9. **package**：确认三个启动脚本与 `README-learner.md` 就绪；工作区根交付。

每阶段完成即：

```bash
python3 <skill>/scripts/pipeline.py validate <stage>
python3 <skill>/scripts/pipeline.py advance  --stage <stage>
```

## 资源索引

- `references/`：方法与规则（按路由读取，不必全部加载）。
- `references/schemas/`：7 个数据结构的 JSON Schema；写产物前先读对应 schema。
- `scripts/`：`pipeline.py`（状态与编排）、`validate_stage.py`、`validate_sources.py`、`validate_course.py`、`build_site.py`、`check_site.py`、`estimate_duration.py`；`scripts/lib/` 为共享工具。
- `assets/presets/`：`research-course`、`code-onboarding`、`beginner-tutorial` 三套预设。
- `assets/themes/`：`scientific-editorial`（默认）、`engineering-blueprint`、`classroom-clean`。
- `assets/web-template/`：精简 Vite + React + TS 底座（16:9 舞台、slide/step 游标、字幕层、token 契约）。

## 维护

- 本文件保持精简（不超过 500 行）；细节一律放 `references/`。
- 目录与文件名仅用小写字母、数字、连字符；frontmatter `name` 必须与目录名一致。
- 每次人工评审的结论必须固化到 reference / schema / validator / template / tests 之一（见 `development-workflow.md`），否则视为未完成。
