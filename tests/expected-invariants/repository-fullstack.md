# repository-fullstack 不变量

- `source-analysis` 完成时：`entrypoints` 与 `dataflow` 非空，且每个符号都能在仓库中找到。
- `degradations` 可以为空；若有降级（如入口不明确），必须逐条写入 `run-state` 与 `qa-report`。
- 当前夹具为占位（`tiny-cli` 不是全栈仓库）；替换为真实全栈夹具后，应补充前后端调用链断言。
