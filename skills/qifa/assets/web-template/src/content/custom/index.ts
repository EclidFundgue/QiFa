import type { ComponentType } from "react";
import type { Slide } from "../../types";

/**
 * 定制页面注册表：build_site.py 为每张 slide 生成 `./custom/<slide-id>.tsx` 路径，
 * 需要定制视觉时在此注册即可（未注册的 slide 走默认渲染器）。
 */
export const customSlides: Record<string, ComponentType<{ slide: Slide }>> = {};
