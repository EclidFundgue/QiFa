# QiFa

QiFa 是一个 OpenCode Agent Skill：把**论文**和/或**代码库**做成 **PPT 式可视化讲解网页课程**（`chapter → slide → step` 三级，16:9），含课堂口语讲稿（可开关字幕）、术语卡、公式分步、代码走读、图表放大，以及可选的讲解视频嵌入。

## 功能

- **输入**：本地 PDF、arXiv URL、arXiv LaTeX 源码、本地 LaTeX 工程、DOCX、网页文章；本地代码库路径、git URL（只读浅克隆）；论文与代码库可混合输入（会先做相关性检查）。
- **产出**：可运行的 Vite + React + TS 课程网页（`presentation/`）+ 三个跨平台启动脚本 + 面向学习者的 `README-learner.md` + QA 报告。
- **两种模式**：
  - `production`（默认）：开头一次性确认需求，中途不打断；每阶段"生成 → 校验 → 修复（最多 2 次）→ 推进"。
  - `development`（仅显式要求）：阶段级 `--stop-after`、人工评审、`feedback-log` 反馈固化、回归用例。
- **自动质检**：结构 / 来源 / 教学 / 章节 / 叙事 / 视觉 / 网页 / 集成 8 层；`blocker` 修复 2 次仍失败即终止，`warning` 降级发布并写入报告。
- **明确不做**：TTS 配音、录屏与视频合成、练习与自测、代码沙箱、修改用户仓库。

## 与相邻 Skill 的边界

| 需求 | 用哪个 |
| --- | --- |
| 论文/代码库 → PPT 式课程网页 | **QiFa** |
| 论文 → 带字幕的视频感演示（可录屏） | `paper-explainer` / `web-video-presentation` |
| 素材 → 单文件 HTML 长文 | `beautiful-article` |
| 通用页面 / dashboard / UI 设计 | `web-design-engineer` |
| 陪着你逐步读懂并**动手修改**代码库 | `guided-code-learning`（需显式调用） |

## 快速开始

在 OpenCode 会话中直接说：

- 「用 $qifa 把这篇论文做成一套 45 分钟的 PPT 式讲解课件：`~/papers/attention.pdf`，面向有 Python 基础的研究生」
- 「用 $qifa 把 `~/repos/tiny-cli` 做成新同学入职讲解课程，20 分钟，中文」
- 「用 $qifa 把这篇论文和它的官方实现一起讲：arXiv 2401.00001 + `https://github.com/xxx/yyy`」

详见 [examples/](examples/)。

## 安装

Skill 的加载路径为 `~/.config/opencode/skills/<name>/SKILL.md`（详见 [OpenCode Agent Skills 文档](https://opencode.ai/docs/skills/)）。技能机器名为 `qifa`（规范要求全小写），展示名为 QiFa。

全局安装（软链接，改动即时生效）：

```bash
git clone <repo-url> ~/projects/QiFa
mkdir -p ~/.config/opencode/skills
ln -s ~/projects/QiFa/skills/qifa ~/.config/opencode/skills/qifa
```

复制安装：

```bash
mkdir -p ~/.config/opencode/skills
cp -r skills/qifa ~/.config/opencode/skills/qifa
```

项目级安装（只对单个项目生效）：

```bash
mkdir -p .opencode/skills
cp -r /path/to/QiFa/skills/qifa .opencode/skills/qifa
```

Windows（PowerShell，复制安装）：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\opencode\skills" | Out-Null
Copy-Item -Recurse skills\qifa "$env:USERPROFILE\.config\opencode\skills\qifa"
```

### 依赖

- **Node ≥ 18 + npm**：课程产物（Vite + React）的安装与启动必需。
- **Python ≥ 3.10**：QiFa 自身脚本（质检、构建、时长统计）。脚本零第三方依赖即可运行；首次 `pipeline.py init` 会在平台缓存目录自动创建 `.venv` 并安装 `pyyaml + jsonschema`（可用 `--no-install` 关闭，失败自动降级并写报告）。
- 可选：`pdftotext`（poppler）、`pdfplumber`、`python-docx`、`beautifulsoup4` —— 缺哪个降级哪种输入，详见 `references/paper-analysis.md`。

## 使用

生产模式（默认，一次确认后全程自动）：

```bash
python3 skills/qifa/scripts/pipeline.py init \
  --input paper:~/papers/attention.pdf \
  --out ./qifa-output/attention
```

随后 Agent 按 `references/production-workflow.md` 逐阶段产出，并在每阶段调用：

```bash
python3 skills/qifa/scripts/pipeline.py validate source-analysis
python3 skills/qifa/scripts/pipeline.py advance  --stage source-analysis
python3 skills/qifa/scripts/pipeline.py report
```

开发模式（阶段级人工评审）：

```bash
python3 skills/qifa/scripts/pipeline.py init \
  --case tests/cases/paper-basic.yaml --no-install
```

CLI 速查：

| 命令 | 作用 |
| --- | --- |
| `init` | 建工作区、生成 `project.yaml` 与 `run-state.yaml` |
| `status` | 查看阶段状态（`--json` 供 Agent 读取） |
| `validate <stage>` | 跑该阶段的确定性校验 |
| `advance --stage <id>` | 校验通过才推进；不通过累计修复次数 |
| `report` | 汇总 `qa-report.json` + `qa-report.md` + 时长统计 |
| `estimate` | 只跑讲稿字数 / 时长统计 |

退出码：`0` 正常 / `1` 硬失败（含 blocker 校验不过）/ `2` 用法与配置错误。

## 目录结构

```text
QiFa/
├── README.md  LICENSE  THIRD_PARTY_LICENSES  .gitignore
├── skills/qifa/
│   ├── SKILL.md · agents/openai.yaml
│   ├── references/          # 生产/开发流程、论文与代码分析、课程设计、质检 rubric、schemas/
│   ├── scripts/             # pipeline 与 6 个校验/构建脚本 + lib/
│   └── assets/              # presets/ · themes/ · web-template/
├── examples/                # 三份示例（请求原文 + 运行摘要）
└── tests/                   # test_validation.py · cases/ · expected-invariants/ · fixtures/
```

## 配置

全局配置（跨项目默认，可选）：

| 平台 | 路径 |
| --- | --- |
| Windows | `%APPDATA%\qifa\config.yaml` |
| macOS | `~/Library/Application Support/qifa/config.yaml` |
| Linux | `$XDG_CONFIG_HOME/qifa/config.yaml`（默认 `~/.config/qifa/config.yaml`） |

可用环境变量 `QIFA_CONFIG` 覆盖。项目内 `project.yaml` 覆盖全局。持久字段：`audience / language / visual_style / depth`；`goal / duration` 属于单次任务。

## 开发与测试

零依赖（仅标准库）：

```bash
python3 tests/test_validation.py
```

分层：P0 = 仓库结构 + schema/校验器 + 构建脚本的确定性检查（零 LLM、零网络，可进 CI）；P1 = Agent 端到端跑 `tests/cases/*.yaml`，结论写回 case 与 `tests/expected-invariants/`。

## 许可与第三方

本项目 MIT，见 [LICENSE](LICENSE)。设计上参考了 MIT 许可的 [garden-skills](https://github.com/ConardLi/garden-skills)（web-video-presentation）与 [taste-skill](https://github.com/Leonxlnx/taste-skill)（design-taste-frontend），归属声明见 [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES)。
