# 示例 01：论文 → 讲解课程

## 用户请求

> 用 $qifa 把这篇论文做成一套 45 分钟的 PPT 式讲解课件：`~/papers/attention-is-all-you-need.pdf`，面向有 Python 基础的人工智能研究生，中文，学术风格。

## QiFa 的预期行为

1. **intake**：能从请求推断出的字段不重复询问；补充确认目标学习者、目标、时长、语言、风格，并询问是否把长期字段保存为全局默认。
2. **source-analysis**：抽取论文结构、公式、图表与实验证据，写入 `source/source-model.json`；公式保留 LaTeX 原文，引用按 `[Eq.3, p.4]` 格式。
3. **curriculum / chapter-design**：45 分钟 → 5–7 章；每章承接学习目标，页面按 `chapter → slide → step` 组织。
4. **narrative**：写课堂口语讲稿（每页 80–220 字），首次出现的术语给"译名（原词）"。
5. **visual-storyboard**：登记每个图示/动效的教学目的，例如用分步动画解释注意力权重的形状变化。
6. **web-generation / automated-review**：生成 `presentation/`，`npm run build` 通过，输出 `review/qa-report.md`；时长偏差超过 30% 记 warning。

## 验收标准

- `python3 skills/qifa/scripts/pipeline.py report` 显示 0 个 blocker。
- 每个引用都能在 `source-model.json` 找到对应条目。
- 三个启动脚本可用：Windows 双击 `start.bat`，macOS 双击 `start.command`，Linux `bash start.sh`。
- 讲稿换算时长与 45 分钟目标偏差在容差内（或作为 warning 明确记录）。

## 备注

- 论文 PDF 无文本层（扫描件）时会降级处理并记 warning，不终止。
- 需要 TTS 配音／录屏成片，请改用 `paper-explainer` 或 `web-video-presentation`。
