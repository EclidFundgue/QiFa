interface Props {
  /** 当前这一句字幕文本。 */
  text: string;
  /** 句序号（从 0 开始）。 */
  index: number;
  /** 本页总句数。 */
  total: number;
}

/** 页内字幕：一次只显示一句，句序由导航推进；内容来自讲稿，不单独存储。 */
export default function Subtitle({ text, index, total }: Props) {
  if (!text.trim()) return null;
  return (
    <p className="narration" lang="zh-CN" aria-live="polite">
      <span className="narration-text">{text}</span>
      {total > 1 && (
        <span className="narration-count" aria-label={`第 ${index + 1} 句，共 ${total} 句`}>
          {index + 1} / {total}
        </span>
      )}
    </p>
  );
}
