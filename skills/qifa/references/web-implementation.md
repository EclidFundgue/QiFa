# 网页实现（web-generation）

目标：把 plan + 讲稿变成可运行的 `presentation/`（Vite + React + TS，16:9，`chapter → slide → step`）。

## 构建流程

1. `build_site.py` 把 `assets/web-template/` 拷贝到工作区 `presentation/`（已存在则只更新生成物）。
2. 生成站点数据：
   - `src/content/course.json`：课程元信息 + 章节 + slide + step + 讲点 + 引用（来自 plan）。
   - `src/content/narrations.json`：按 slide 锚点提取的讲稿（来自 `script/`）。
   - `public/media/`：从 `source/media/` 拷贝登记过的素材。
   - `src/styles/tokens.css`：从所选主题拷贝。
3. Agent 为需要定制视觉的 slide 写 `src/content/custom/<slide-id>.tsx`，并在 `src/content/custom/index.ts` 注册。
4. `npm install && npm run build` 必须通过（blocker 级 QA 项）。

## 混合管线

- **数据驱动**（默认）：`title / concept / comparison / summary / video` 由渲染器按数据渲染。
- **定制 TSX**（例外）：`diagram / formula-steps / code-walkthrough` 等复杂视觉，允许每页一个 TSX 覆盖默认渲染。
- 数据在 `course.json`，代码在 `custom/`；两者都不硬编码讲稿全文（讲稿在 `narrations.json`）。

## 交互与导航

- 16:9 舞台等比缩放适配窗口；窄屏可切换"单页滚动"阅读模式（可选）。
- 键盘：`←/→` 上一页/下一页，`↓/↑` 页内 step，`f` 全屏，`s` 字幕开关，`g` 术语表。
- 侧栏按章导航；页码按 slide 计数；URL hash 可定位到 `#c3/s07`。
- 字幕：默认显示、可开关；内容来自 `narrations.json`，逐 slide 对应讲稿。

## 无障碍与离线

- 页面 `lang` 与课程语言一致；图片有 `alt`；按钮有可读标签；焦点可见。
- 不依赖外部 CDN 资源（字体、图标、脚本必须本地或随包构建），保证离线可用。
- 视频有 poster 与文字替代；颜色对比度满足可读性。

## 启动与交付

工作区根提供三个启动脚本（`start.sh` / `start.command` / `start.bat`）：

1. 检测 Node ≥ 18，缺失则给出安装指引并退出。
2. 首次运行自动 `npm install`（有 `node_modules` 则跳过）。
3. `npm run dev -- --open`，端口被占用自动换端口。

## 自检清单

- [ ] `npm run build` 无错误。
- [ ] 所有页面可键盘导航；字幕开关有效。
- [ ] 无外链资源；断网可打开已构建产物。
- [ ] 素材路径全部存在（`check_site.py` 通过）。
- [ ] 定制 TSX 只覆盖登记的视觉，不越权改全局样式。
