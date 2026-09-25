import katex from "katex";
import type { ReactNode } from "react";
import type { Slide } from "../types";

interface Props {
  slide: Slide;
  step: number;
}

/** 用 $...$ 包裹的片段按 KaTeX 渲染，其余原样输出。 */
export function MathText({ text }: { text: string }): ReactNode {
  const parts = text.split(/(\$[^$]+\$)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
          const html = katex.renderToString(part.slice(1, -1), { throwOnError: false });
          return <span key={index} dangerouslySetInnerHTML={{ __html: html }} />;
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

export default function FormulaSteps({ slide, step }: Props) {
  const visibleCount = slide.steps.length > 1 ? Math.max(1, step + 1) : slide.points.length;
  return (
    <div>
      <h1 className="slide-title">{slide.title}</h1>
      <ul className="points">
        {slide.points.map((point, index) => (
          <li key={`${slide.id}-${index}`} style={{ opacity: index >= visibleCount && slide.steps.length > 1 ? 0.25 : 1 }}>
            <MathText text={point.text} />
            {point.refs.length > 0 && <span className="refs">[{point.refs.map((ref) => ref.locator).join("；")}]</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
