/**
 * 把一页讲稿拆成一句一屏的字幕。
 *
 * 规则：
 * - 以中文句号/问号/叹号/分号为句末，保留标点；换行与多余空白先归一化。
 * - 过长的句子（> 46 字）在靠后的逗号/顿号处再切一刀，保证字幕不超过两行。
 *
 * 纯函数、无依赖：演示层用它驱动字幕，讲稿始终是唯一真相源。
 */
const ENDINGS = new Set(["。", "！", "？", "；", "!", "?", ";", "…"]);
const SOFT_CUTS = ["，", "、", ",", " "];
const MAX_LINE_CHARS = 46;

export function splitSentences(text: string): string[] {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return [];

  const raw: string[] = [];
  let buffer = "";
  for (const char of normalized) {
    buffer += char;
    if (ENDINGS.has(char)) {
      if (buffer.trim()) raw.push(buffer.trim());
      buffer = "";
    }
  }
  if (buffer.trim()) raw.push(buffer.trim());

  const result: string[] = [];
  for (const sentence of raw) {
    let rest = sentence;
    while (rest.length > MAX_LINE_CHARS) {
      const window = rest.slice(0, MAX_LINE_CHARS);
      let cut = -1;
      for (const mark of SOFT_CUTS) {
        cut = Math.max(cut, window.lastIndexOf(mark));
      }
      if (cut < 20) break;
      result.push(rest.slice(0, cut + 1).trim());
      rest = rest.slice(cut + 1).trim();
    }
    if (rest) result.push(rest);
  }
  return result.filter(Boolean);
}
