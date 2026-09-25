/**
 * 把一页讲稿拆成一句一屏的字幕。
 *
 * 拆句的主权在写稿：**一句话一行，行就是一条字幕**（见 narrative-design.md 格式）。
 * 播放器只做两层兜底，不再主动按逗号切碎句子：
 * 1. 行内按句末标点（。！？；…）再切一刀——兼容整段写法的旧讲稿；
 * 2. 某句超过 80 字（约两行）时，才在逗号/顿号处硬切，保证字幕放得下。
 *
 * 纯函数、无依赖：演示层用它驱动字幕，讲稿始终是唯一真相源。
 */
const ENDINGS = new Set(["。", "！", "？", "；", "!", "?", ";", "…"]);
const SOFT_CUTS = ["，", "、", ",", " "];
const MAX_LINE_CHARS = 80;

function splitLine(line: string): string[] {
  const sentences: string[] = [];
  let buffer = "";
  for (const char of line) {
    buffer += char;
    if (ENDINGS.has(char)) {
      if (buffer.trim()) sentences.push(buffer.trim());
      buffer = "";
    }
  }
  if (buffer.trim()) sentences.push(buffer.trim());

  const result: string[] = [];
  for (const sentence of sentences) {
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
  return result;
}

export function splitSentences(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .flatMap(splitLine);
}
