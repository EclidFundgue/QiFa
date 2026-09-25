# 开发模式工作流

仅当用户**明确**说"开发模式 / 停在某阶段 / 测试某阶段 / 跑回归"时使用；默认永远是 production。

## 与生产模式的区别

| | production | development |
| --- | --- | --- |
| 交互 | 只在开头 | 每个阶段产出后停下来评审 |
| 停止 | 不中途停 | `--stop-after <stage>` |
| 反馈 | 无 | 每条评审结论必须固化 |
| 产物 | 完整课程 | 阶段产物 + `review/feedback-log.md` |

## 启动

```bash
python3 <skill>/scripts/pipeline.py init --case tests/cases/paper-basic.yaml --no-install
```

case 文件（`tests/cases/*.yaml`）字段：

```yaml
name: paper-basic
mode: development
stop_after: curriculum
input: {paper: tests/fixtures/papers/tiny-paper.tex, repo: null}
config: {language: zh-CN, duration: 20, visual_style: scientific-editorial}
expect:
  no_blockers: true
  stages_done: [intake, source-analysis, curriculum]
  outline: {min_chapters: 3, max_chapters: 6, objectives_covered: true}
```

`stop_after` 只支持**阶段级**（阶段 ID 见 `production-workflow.md`）；不支持 `curriculum:3` 这类子步骤。要重做某一步就重跑该阶段并在 `feedback-log.md` 记录原因。

## 阶段评审与反馈固化

每个阶段结束后：

1. 产出阶段产物，跑 `validate <stage>`。
2. 停下来向用户展示产物摘要与问题清单，收集人工发现。
3. 把每条发现写进 `review/feedback-log.md`（格式见下）。
4. **固化**：每条发现必须落到以下之一，并标注是否已应用；落不进去就视为该轮未完成。
   - 论文/代码理解规则 → `paper-analysis.md` / `code-analysis.md`
   - 课程结构 → `curriculum-design.md` / `chapter-design.md`
   - 讲稿风格 → `narrative-design.md`
   - 视觉与页面 → `visual-design.md` / `web-implementation.md`
   - 字段缺失 → `references/schemas/*.schema.json`
   - 反复失败 → `scripts/validate_*.py` 规则
   - 课程风格偏好 → `assets/presets/*.yaml`
   - 页面设计有效做法 → `assets/web-template/`
   - 真实案例 → `tests/cases/` + `tests/expected-invariants/`

`feedback-log.md` 格式：

```markdown
## <时间> <阶段>
- 发现：<人工观察>
- 结论：<一般化规则>
- 固化位置：<文件路径>（已应用 / 待应用）
- 回归：<对应 case 或 fixture>
```

## 回归测试

- **P0（可进 CI，零 LLM、零网络）**：`tests/fixtures/workspaces/` 里的手写产物样例跑 schema、`validate_*`、`build_site`、`estimate_duration`、`check_site`；`tests/test_validation.py` 还负责仓库结构与本 skill 自身校验。
- **P1（人工触发）**：Agent 按 `cases/*.yaml` 端到端跑生产流程，用 `pipeline.py report --case <case> --check-expect` 判定 `expect` 不变量；结论写回 case 与 `tests/expected-invariants/<case>.md`。
- 新增能力必须同时新增 case 或 fixture，否则不算完成。
