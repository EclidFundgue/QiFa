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
- **文本页示意图**：`concept / comparison / summary` 默认走示意图组件（时间线 / 对比列 / 收束链，见模板 `assets/web-template/src/content/custom/PointFlow.tsx`），讲点只放关键词；不要退化成文字列表。
- **定制 TSX**（例外）：`diagram / formula-steps / code-walkthrough` 等复杂视觉，允许每页一个 TSX 覆盖默认渲染。
- 定制组件收到 `(slide, step, sentence, sentences)`：
  - `sentence` / `sentences` 是当前字幕与整页字幕列表——**图示高亮必须跟随当前这条字幕**（例如字幕讲到“相机+指令”就高亮这两个输入框，讲到“本体状态”就切到状态框）；字幕是拆句后的最小推进单位，也是讲稿的真相源。
  - `step` 是页内要点进度，只用于粗粒度揭示；两者冲突时以字幕为准。
  - 组件不得自行推进游标，也不得硬编码与讲稿不一致的节奏。
- **高亮语义**（`custom/focus.ts` 的 `focusOf` / `focusStyle`）：`on` = 当前字幕有明确指向时加 accent；`off` = 指向别处时压暗为陪衬；`neutral` = 导入、过渡、总括等没有指向的句子保持原始样式。**禁止“默认全部高亮”或整页常亮**——高亮是突出重点用的，不是装饰。
- 数据在 `course.json`，代码在 `custom/`；两者都不硬编码讲稿全文（讲稿在 `narrations.json`）。

## 交互与导航

- 16:9 舞台是**唯一缩放单元**：`useStageScale` 按宿主容器（不是窗口）测量 + `ResizeObserver`，`html/body/#root` 不滚动；任何内容都不得溢出舞台。
- 舞台内容统一放 `.stage-body`（超出时在舞台内滚动）；底部由 `.course-column` 串联字幕条、控件与进度。
- 侧栏导航：`.app-shell` 用网格把导航做成**占位列**（`grid-template-columns: <nav> minmax(0, 1fr)`，窄屏按断点收窄），不是覆盖舞台的浮层。除术语表（带遮罩、可关闭）外不允许其他固定浮层压住舞台。
- 键盘：`←/→/↑/↓/空格` 上一句/下一句（句读完推要点、要点到底翻页），`f` 全屏，`s` 字幕开关，`g` 术语表，`Esc` 关闭术语表。
- 页码按 slide 计数；URL hash 可定位到 `#c3/s07`。

## 字幕（逐句）

- **拆句主权在写稿**：讲稿按“一句话一行”书写（`references/narrative-design.md`），行就是一条字幕；`src/content/sentences.ts:splitSentences` 只做兜底——行内句末标点切一刀（兼容整段旧稿），单句 > 80 字才在逗号处硬切。
- **一条字幕 = 一件事**：建议每行 20–80 字，最多两行显示；不要把长句留给播放器硬切（历史问题：逗号处硬切产生“还有本体状态……，”这类半句字幕）。
- **一次只显示一句**：`下一步` 推进一句；页内要点按句序成比例展开（`useCourseCursor` 的 `derivedStep`），句读完再推进 step、最后翻页。
- 字幕条在舞台内部底部，反色底 + 顶部强调线，右侧带“句序 / 总句数”指示；内容仍来自 `narrations.json`，不单独存字幕文件。
- 字幕换行**不做两行平衡对齐**：第一行占满宽度再换下一行（`.narration-text` 不得设 `text-wrap: balance`）。

## 视觉验收（无头浏览器，可选）

字幕条占用舞台底部，纯构建检查发现不了“最后一条被压住”。有 `playwright` + chromium 时按下面的流程做一次逐页验收：

```bash
cd presentation && npm run build
python3 -m http.server 8791 --directory dist &
python3 <skill>/scripts/visual_audit.py <workspace> --out /tmp/qifa-shots
```

- 判定：`.stage-body` 的 `scrollHeight` 必须等于 `clientHeight`（不允许内容区出现内滚）；元素不得越过内容区边界。
- 设计画布 1280×720，扣掉页面内边距与字幕区后，**内容区约 1136×552**；定制 TSX 按这个尺寸设计。
- 4 条及以上讲点的页面由 `SlideRenderer` 自动加 `points-dense` 缩排（历史溢出场景：4 条长讲点被字幕条压住）。
- 没有浏览器依赖时降级为 `info`，在 qa-report 里注明“未做人工/无头视觉验收”，不阻塞发布。

## 主题边界

- 颜色、字体、圆角、阴影**只能**由 `assets/themes/<id>/tokens.css` 定义；`base.css` 只管结构与布局，不得重定义主题 token（历史上它覆盖过主题色）。

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
