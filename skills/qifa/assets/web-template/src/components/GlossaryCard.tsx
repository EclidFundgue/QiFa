import type { GlossaryEntry } from "../types";

interface Props {
  glossary: GlossaryEntry[];
  onClose: () => void;
}

export default function GlossaryCard({ glossary, onClose }: Props) {
  if (glossary.length === 0) {
    return (
      <aside className="glossary" role="dialog" aria-modal="true" aria-labelledby="glossary-title">
        <header className="glossary-header">
          <h2 id="glossary-title">术语表</h2>
          <button type="button" onClick={onClose} aria-label="关闭术语表">关闭</button>
        </header>
        <p className="glossary-empty">本课程暂无术语。</p>
      </aside>
    );
  }
  return (
    <aside className="glossary" role="dialog" aria-modal="true" aria-labelledby="glossary-title">
      <header className="glossary-header">
        <div>
          <h2 id="glossary-title">术语表</h2>
          <p>{glossary.length} 个核心概念</p>
        </div>
        <button type="button" onClick={onClose} aria-label="关闭术语表">关闭</button>
      </header>
      <dl className="glossary-grid">
        {glossary.map((entry) => (
          <div className="glossary-card" key={entry.term}>
            <dt>
              {entry.term}
              {entry.translation && <span>{entry.translation}</span>}
            </dt>
            <dd>{entry.definition}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
