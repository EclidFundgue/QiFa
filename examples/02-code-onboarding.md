# 示例 02：代码库 → 入职讲解课程

## 用户请求

> 用 $qifa 把 `~/repos/tiny-cli` 做成新同学入职讲解课程，20 分钟，中文，工程风格。

## QiFa 的预期行为

1. **intake**：识别为纯代码库输入（`relevance.relation = not-applicable`），推荐 `beginner-tutorial` 或 `code-onboarding` preset。
2. **source-analysis**：只读分析仓库：模块地图、入口、3–5 条主调用链、关键符号；引用一律 `path:符号`（如 `main.py:main`），不记录行号。
3. **curriculum**：按"问题 → 结构 → 路径 → 细节"组织章节，而不是按目录遍历。
4. **chapter-design / narrative**：代码走读页逐条揭示，讲稿解释每一步的设计取舍。
5. **web-generation**：生成站点与启动脚本；`check_site.py` 验证资源、链接、键盘导航与离线可用性。

## 验收标准

- 每个 `entrypoints` / `symbols` 引用都真实存在于仓库。
- 至少一条端到端调用链（入口 → 关键函数）讲清楚。
- 不包含练习与自测；想动手改代码的学习者会被建议显式调用 `guided-code-learning`。
- 全程不修改用户仓库；git URL 输入只做浅克隆。

## 备注

- 代码引用不写 commit hash、不写行号，避免漂移。
- 需要"陪着手改代码"的交互式学习，请用 `guided-code-learning`（需显式调用）。
