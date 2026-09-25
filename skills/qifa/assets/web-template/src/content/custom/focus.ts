import type { CSSProperties } from "react";

/**
 * 高亮语义（见 references/web-implementation.md）：
 * - `on`：当前字幕有明确指向 → 加 accent、正常亮度；
 * - `off`：当前字幕指向别处 → 压暗为陪衬；
 * - `neutral`：当前字幕没有明确指向（导入、过渡、总括）→ 保持原始样式，
 *   既不高亮也不压暗，禁止“默认全部高亮”。
 */
export type Focus = "neutral" | "on" | "off";

export function focusOf<T extends string | number>(hot: T | null | undefined, key: T): Focus {
  if (hot === null || hot === undefined) return "neutral";
  return hot === key ? "on" : "off";
}

export function focusStyle(focus: Focus, base: CSSProperties): CSSProperties {
  const transition = "opacity 240ms ease, border-color 240ms ease, background 240ms ease";
  if (focus === "on") {
    return {
      ...base,
      border: "1px solid var(--accent)",
      background: "color-mix(in srgb, var(--accent) 12%, var(--surface))",
      opacity: 1,
      transition
    };
  }
  if (focus === "off") {
    return { ...base, opacity: 0.45, transition };
  }
  return base;
}
