import type { GlossaryEntry } from "../types";

interface Props {
  glossary: GlossaryEntry[];
}

export default function GlossaryCard({ glossary }: Props) {
  if (glossary.length === 0) {
    return (
      <aside className="glossary" aria-label="术语表">
        <p>本课程暂无术语表。</p>
      </aside>
    );
  }
  return (
    <aside className="glossary" aria-label="术语表">
      <h2 style={{ fontSize: 16, margin: 0 }}>术语表</h2>
      <dl>
        {glossary.map((entry) => (
          <div key={entry.term}>
            <dt>
              {entry.term}
              {entry.translation ? `（${entry.translation}）` : ""}
            </dt>
            <dd>{entry.definition}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
