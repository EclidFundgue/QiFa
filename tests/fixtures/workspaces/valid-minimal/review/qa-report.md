# QA 报告

- 生成时间：2026-09-25T14:33:53
- 模式：production
- 摘要：blocker 0 / warning 3 / info 0 / 降级 0

## 时长

| 章节 | 汉字 | 英文词 | 估算分钟 |
| --- | --- | --- | --- |
| C01 | 680 | 27 | 3.0 |
| 合计 | - | - | 3.0 |

## 问题清单

- [warning] PED-DURATION（pedagogy）plan/course-outline.json：大纲声明 5 分钟，讲稿换算 3 分钟，差异超过 1.5 分钟 → 按讲稿重算每章 duration_estimate
- [warning] PED-DURATION（pedagogy）script/：讲稿换算 3 分钟，目标 20 分钟，偏差 85% 超过容差 30%
- [warning] WEB-DATA（web）presentation/src/content/narrations.json：缺少 narrations.json

## 降级与警告

无。
