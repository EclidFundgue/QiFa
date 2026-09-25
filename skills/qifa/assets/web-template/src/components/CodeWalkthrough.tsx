import type { Slide } from "../types";

interface Props {
  slide: Slide;
  step: number;
}

/** 代码逐步走读：按 step 逐条显示讲点，未到的条目变暗。 */
export default function CodeWalkthrough({ slide, step }: Props) {
  const hasSteps = slide.steps.length > 1;
  const visibleCount = hasSteps ? Math.max(1, step + 1) : slide.points.length;
  return (
    <div>
      <h1 className="slide-title">{slide.title}</h1>
      {slide.visuals.length > 0 && (
        <p className="slide-goal">{slide.visuals.map((visual) => visual.purpose).join(" / ")}</p>
      )}
      <div className="code">
        {slide.points.map((point, index) => (
          <div key={`${slide.id}-${index}`} style={{ opacity: index >= visibleCount && hasSteps ? 0.25 : 1 }}>
            <span className="refs">{point.refs.map((ref) => `[${ref.locator}]`).join(" ")} </span>
            {point.text}
          </div>
        ))}
      </div>
    </div>
  );
}
