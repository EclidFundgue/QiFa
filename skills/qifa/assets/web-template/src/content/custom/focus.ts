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

/** `detect` 的显式终止信号：结构讲完（总括 / 过渡 / 结论），此后整页不再高亮。 */
export const STOP = -1;

/** `detect` 的逐条中性信号：本条是侧支/举例，本句不高亮，但之后可以恢复。 */
export const NEUTRAL = -2;

/**
 * 逐条字幕求焦点（规则见 references/highlight-rules.md）：
 * - 一旦出现 STOP → 此后整页中性，后续命中也不复活；
 * - 本条是 NEUTRAL → 本句中性，之前/之后的焦点不受影响；
 * - 本条有指向且不低于已讲顺序 → 它就是当前焦点；
 * - 回指已讲过的元素（序号更小）→ 不改焦点，不二次聚焦；
 * - 本条无指向 → 沿用最近一次焦点（粘滞），不得空掉。
 */
export function focusAt(
  sentences: string[],
  sentence: number,
  detect: (text: string) => number | null
): number | null {
  let focus: number | null = null;
  let maxFocus = -1;
  let stopped = false;
  for (let i = 0; i <= sentence; i += 1) {
    const hit = detect(sentences[i] ?? "");
    if (hit === STOP) {
      stopped = true;
      focus = null;
      continue;
    }
    if (stopped) continue;
    if (hit === null || hit === undefined) continue;
    if (hit === NEUTRAL) {
      if (i === sentence) focus = null;
      continue;
    }
    if (hit < maxFocus) continue; // 回指：保持当前焦点
    focus = hit;
    maxFocus = hit;
  }
  return focus;
}

/**
 * 常用检测器（规则见 references/highlight-rules.md）：
 * 按 stops（终止）→ neutrals（本条中性）→ rules（元素序号）的顺序做 includes 匹配。
 * 只有"首次介绍"的关键词放进 rules，避免已介绍过的元素被词面重复命中。
 */
export function detector(
  rules: [string, number][],
  stops: string[] = [],
  neutrals: string[] = []
): (text: string) => number | null {
  return (text: string) => {
    if (!text) return null;
    for (const word of stops) if (text.includes(word)) return STOP;
    for (const word of neutrals) if (text.includes(word)) return NEUTRAL;
    for (const [word, index] of rules) if (text.includes(word)) return index;
    return null;
  };
}
