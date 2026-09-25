# 生产模式工作流

默认模式。开头一次确认（`intake.md`），之后**全程不向用户提问**；每阶段"产出 → 校验 → 修复（最多 2 次）→ 推进"。

## 工作区

`pipeline.py init` 创建：

```text
<out>/<slug>/
├── project.yaml                 # 配置快照，生成后不再改写
├── .qifa/run-state.yaml         # 唯一可变状态文件
├── .qifa/logs/                  # 各阶段校验日志
├── 00-intake.md                 # intake 结论（含相关性判定与用户选择）
├── source/                      # paper.md、paper-src/、code/、media/、source-model.json
├── plan/                        # course-outline.json、chapter-plan-C*.json（每章一个）、visual-plan.json
├── script/                      # NN-<chapter-id>.md 讲稿（真相源）
├── presentation/                # Vite + React + TS 课程站点
├── review/                      # qa-report.json、qa-report.md
└── README-learner.md
```

## 阶段循环

| # | stage | 输入 | 产出 | 校验 |
| --- | --- | --- | --- | --- |
| 0 | `intake` | 用户请求、全局配置、preset | `00-intake.md`、`project.yaml`、`run-state.yaml` | `validate_stage.py` |
| 1 | `source-analysis` | 论文/仓库/媒体 | `source/*`、`source-model.json` | `validate_stage.py` + `validate_sources.py` |
| 2 | `curriculum` | source-model | `plan/course-outline.json` | + `validate_course.py` |
| 3 | `chapter-design` | course-outline | `plan/chapter-plan-C*.json` | + `validate_course.py` |
| 4 | `narrative` | chapter-plan | `script/NN-<id>.md`、术语表 | + `validate_course.py` |
| 5 | `visual-storyboard` | chapter-plan、素材 | `plan/visual-plan.json` | + `validate_course.py` |
| 6 | `web-generation` | 全部 plan + script | `presentation/`（`npm run build` 通过） | `build_site.py` + `check_site.py` |
| 7 | `automated-review` | 整个工作区 | `review/qa-report.json/md` | 全量复跑 + `quality-rubrics.md` |
| 8 | `package` | 产物 | 启动脚本、`README-learner.md` | `validate_stage.py` |

每阶段固定动作：

```bash
python3 <skill>/scripts/pipeline.py validate <stage>     # 打印问题清单，退出码 1 = 有 blocker
python3 <skill>/scripts/pipeline.py advance  --stage <stage>
```

`advance` 内部先校验：通过 → 该阶段 `validated`、游标推进；不通过 → `attempts + 1` 并停在原阶段，Agent 按问题清单修复后重试。`attempts` 超过 `policies.max_repair_attempts`（默认 2）后该阶段标记 `failed`，**终止运行**并在报告中说明。

## 修复与降级

- `blocker`：结构/schema 失败、引用指向不存在、链接断、资源缺失、构建失败。必须修；修不动则终止。
- `warning`：语义问题、时长偏差 > `duration_tolerance`、视频缺失降级、低风险一致性问题。**不修也可以**，但必须写进 `review/qa-report.md`，课件首屏显示"存在降级"提示。
- `info`：建议项，仅记录。
- 所有降级写入 `run-state` 对应阶段的 `degradations[]`，最终汇总进 `qa-report.json`。

## 收尾

```bash
python3 <skill>/scripts/pipeline.py report                        # 生成 review/qa-report.json + qa-report.md（含时长统计）
python3 <skill>/scripts/pipeline.py advance --stage automated-review
python3 <skill>/scripts/pipeline.py advance --stage package
```

交付 = 工作区目录整体：`presentation/`（可运行站点）、`start.sh` / `start.command` / `start.bat`、`README-learner.md`、`review/qa-report.md`、原始来源与中间产物（默认保留）。

## 禁止

- 中途向用户提问（除 intake 与硬错误终止说明）。
- 用"先生成再解释"的方式掩盖来源缺失；来源不足就降级（缩小 depth/duration）并在报告里写清。
- 跳过脚本校验直接推进阶段。
