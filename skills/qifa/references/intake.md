# Intake（开头一次性确认）

production 模式只在开头与用户交互一次。目标：把 5 件事问清或推断出，生成 `project.yaml`，然后全程不再提问。

## 必确认的 5 件事

1. **目标学习者及其基础**：受众是谁、已具备什么（如"有 Python 基础的人工智能研究生"）。
2. **课程目标**：学完能做什么（如"理解论文方法并能复现核心算法"）。
3. **期望深度与课程时长**：先根据来源规模自动推荐（见下），给出 2–3 个时长档让用户选。
4. **输出语言**：默认 `zh-CN`；请求里出现英文或用户用英文提问则 `en`。
5. **视觉风格或用途**：三选一（默认按内容类型）：
   - `scientific-editorial`：论文/研究类，默认。
   - `engineering-blueprint`：代码/工程类。
   - `classroom-clean`：入门/通识类。

## 推断优先，不重复询问

| 字段 | 推断来源 |
| --- | --- |
| `input.paper` / `input.repo` | 用户消息中的路径、URL、粘贴内容 |
| `language` | 用户消息语言；中文请求 → `zh-CN` |
| `goal` | 请求中的动词（"讲透 / 能复现 / 能上手改"） |
| `audience` / `depth` | 请求中提到的身份与用途；缺省 `intermediate` |
| `visual_style` | 内容类型；论文 → `scientific-editorial`，纯代码 → `engineering-blueprint` |
| `duration` | 来源规模推荐（见下）；用户未选则取默认档并写入报告 |

推断不出的字段用默认值并在 `00-intake.md` 与 `qa-report.md` 标注"使用了默认值"。

## 时长推荐

按来源规模给三档，推荐中间档：

| 来源规模 | 20 分钟 | 45 分钟（推荐） | 90 分钟 |
| --- | --- | --- | --- |
| 单篇论文（8–15 页） | 1 个核心贡献 | 方法 + 1 组实验 | 方法推导 + 全部实验 + 相关工作 |
| 中型仓库（1–5k 行） | 跑通主流程 | 架构 + 3–5 条调用链 | 全模块走读 + 扩展点 |
| 论文 + 官方实现 | 对应关系总览 | 论文方法 ↔ 代码映射 | 方法推导 + 实现细节 + 复现实务 |

时长是**软预算**：讲稿字数换算（中文 240 字/分钟、英文 130 词/分钟），偏差超过 `duration_tolerance`（默认 30%）记 warning。

## 全局配置流程

全局配置路径：Windows `%APPDATA%\qifa\config.yaml`、macOS `~/Library/Application Support/qifa/config.yaml`、Linux `$XDG_CONFIG_HOME/qifa/config.yaml`（默认 `~/.config/qifa/config.yaml`）；`QIFA_CONFIG` 可覆盖。持久字段仅：`audience / language / visual_style / depth`。

1. **首次运行**：完整收集 5 项 → 问用户"是否把这 4 个长期字段保存为全局默认？"→ 按回答写或不写。
2. **之后的运行**：先问"检测到默认配置 <摘要>，直接使用 / 修改？"
   - 使用 → 只确认本次项目字段（`goal / duration / input`）。
   - 修改 → 重新完整收集；结束后再问"是否覆盖全局默认？"
3. 没有全局配置时按首次运行处理。

## 论文 + 代码混合输入

先做相关性检查并写入 `source-model.relevance`：

- `related`：章节设计必须按 `mapping` 交叉引用论文与代码的对应部分。
- `partial`：只讲有映射的部分，其余作为附录简述；仍属同一门课。
- `none`：在开头问用户选哪种：(1) **分开讲**（两次独立运行，各自工作区）、(2) 只讲论文、(3) 只讲代码、(4) 放弃。选择写入 `00-intake.md`。

## 输出目录

默认 `<cwd>/qifa-output/<slug>/`；`--out` 指定工作区目录。slug 取论文标题或仓库名，kebab-case；无来源标题时用 `course`。

## `00-intake.md` 必含

- 输入清单（类型 + 来源 + 是否可访问）
- 5 项确认结果与推断来源
- 使用了哪些默认值
- 相关性判定与用户选择（混合输入时）
- 选用的 preset 与时长档
- 全局配置是否加载/保存
