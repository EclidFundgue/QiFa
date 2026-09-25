# tests

开发模式的回归资产。**P0** 零 LLM、零网络，可进 CI：

```bash
python3 tests/test_validation.py
```

- `test_validation.py`：仓库结构、skill 自检、schema 解析、case 契约、CLI 冒烟、fixture 全链路、development `init`、依赖契约。
- `fixtures/workspaces/tiny-course/`：手写的最小完整工作区（1 章 4 页），用于跑 `validate_*`、`build_site.py`、`check_site.py --no-build-check`、`estimate_duration.py`；必须保持零问题（含 warning）。

**P1** 人工触发（Agent 按 case 端到端跑，零网络断言不了）：

- `cases/*.yaml`：端到端案例，含 `mode`、`input`、`expect` 不变量。
- `expected-invariants/<case>.md`：该 case 实际跑出的结论与人工评审记录。

新增能力必须同时新增 case 或 fixture，否则不算完成（见 `references/development-workflow.md`）。
