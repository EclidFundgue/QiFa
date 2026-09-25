import type { Slide } from "../types";
import ChartZoom from "./ChartZoom";
import CodeWalkthrough from "./CodeWalkthrough";
import FormulaSteps from "./FormulaSteps";
import VideoEmbed from "./VideoEmbed";

interface SlideRendererProps {
  slide: Slide;
  step: number;
}

function refLabel(refs: { locator: string }[]): string {
  return refs.map((ref) => ref.locator).join("；");
}

export default function SlideRenderer({ slide, step }: SlideRendererProps) {
  const hasSteps = slide.steps.length > 1;
  const visibleCount = hasSteps ? Math.max(1, step + 1) : slide.points.length;

  if (slide.kind === "code-walkthrough") {
    return <CodeWalkthrough slide={slide} step={step} />;
  }
  if (slide.kind === "formula-steps") {
    return <FormulaSteps slide={slide} step={step} />;
  }
  if (slide.kind === "video") {
    return <VideoEmbed slide={slide} />;
  }

  const visuals = slide.visuals.filter((visual) => visual.asset);
  return (
    <div>
      <h1 className={slide.kind === "title" ? "slide-title" : "slide-title"}>{slide.title}</h1>
      {slide.kind === "title" && slide.points.length === 0 && <p className="slide-goal" />}
      <ul className={slide.points.length > 3 ? "points points-dense" : "points"}>
        {slide.points.map((point, pointIndex) => (
          <li key={`${slide.id}-${pointIndex}`} className={pointIndex >= visibleCount && hasSteps ? "hidden-step" : ""}>
            {point.text}
            {point.refs.length > 0 && <span className="refs">[{refLabel(point.refs)}]</span>}
          </li>
        ))}
      </ul>
      {visuals.map((visual) =>
        visual.type === "diagram" || visual.type === "chart" || visual.type === "image" ? (
          <ChartZoom key={visual.id} visual={visual} />
        ) : null
      )}
    </div>
  );
}
