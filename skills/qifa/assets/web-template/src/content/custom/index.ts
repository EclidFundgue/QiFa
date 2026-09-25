import type { ComponentType } from "react";
import type { Slide } from "../../types";

/**
 * 定制页面注册表：build_site.py 为每张 slide 生成 `./custom/<slide-id>.tsx` 路径，
 * 需要定制视觉时在此注册即可（未注册的 slide 走默认渲染器）。
 *
 * 定制组件收到 `slide`、`step`、`sentence`、`sentences`：
 * - `step` 是页内要点进度（与讲点对应），用于粗粒度揭示；
 * - `sentence` / `sentences` 是当前字幕与整页字幕列表，用来让图示高亮**跟随当前这条字幕**；
 *   字幕是讲稿拆句的结果，`sentence` 以 0 开始。
 * 组件不得自行推进游标，只根据传入值决定高亮。
 */
export const customSlides: Record<
  string,
  ComponentType<{ slide: Slide; step: number; sentence: number; sentences: string[] }>
> = {};
