import { useEffect, useMemo, useState } from "react";
import GlossaryCard from "./components/GlossaryCard";
import SlideRenderer from "./components/SlideRenderer";
import Stage from "./components/Stage";
import Subtitle from "./components/Subtitle";
import { customSlides } from "./content/custom";
import courseData from "./content/course.json";
import { useCourseCursor } from "./hooks/useCourseCursor";
import type { Course, SlideWithChapter } from "./types";

export default function App() {
  const course = courseData as unknown as Course;
  const slides: SlideWithChapter[] = useMemo(
    () =>
      course.chapters.flatMap((chapter) =>
        chapter.slides.map((slide) => ({
          chapterId: chapter.id,
          chapterTitle: chapter.title,
          slide
        }))
      ),
    [course]
  );
  const { index, step, current, go, next, prev, progress } = useCourseCursor(slides);
  const [showSubtitle, setShowSubtitle] = useState(true);
  const [showGlossary, setShowGlossary] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "s" || event.key === "S") setShowSubtitle((value) => !value);
      if (event.key === "g" || event.key === "G") setShowGlossary((value) => !value);
      if (event.key === "f" || event.key === "F") {
        if (document.fullscreenElement) void document.exitFullscreen();
        else void document.documentElement.requestFullscreen();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!current) {
    return <p>课程数据为空。</p>;
  }

  const Custom = customSlides[current.slide.id];

  return (
    <>
      {course.has_degradations && (
        <div className="degradation-banner" role="status">
          本课程存在降级项（部分内容以更保守的方式呈现），详见 review/qa-report.md
        </div>
      )}
      <Stage>
        {Custom ? <Custom slide={current.slide} /> : <SlideRenderer slide={current.slide} step={step} />}
        {showSubtitle && current.slide.narration && <Subtitle text={current.slide.narration} />}
        <div className="controls">
          <button type="button" onClick={prev} aria-label="上一页">
            ← 上一页
          </button>
          <button type="button" onClick={() => setShowSubtitle((value) => !value)} aria-pressed={showSubtitle}>
            字幕（s）
          </button>
          <button type="button" onClick={() => setShowGlossary((value) => !value)} aria-pressed={showGlossary}>
            术语表（g）
          </button>
          <button type="button" onClick={next} aria-label="下一页">
            下一页 →
          </button>
        </div>
        <div className="progress" aria-hidden="true">
          <span style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
      </Stage>
      <nav className="side-nav" aria-label="课程导航">
        {course.chapters.map((chapter) => (
          <div key={chapter.id}>
            <p className="chapter">
              {chapter.id} · {chapter.title}
            </p>
            {chapter.slides.map((slide) => {
              const target = slides.findIndex((item) => item.slide.id === slide.id);
              return (
                <button
                  type="button"
                  key={slide.id}
                  className={slide.id === current.slide.id ? "active" : ""}
                  onClick={() => go(target)}
                >
                  {slide.id} {slide.title}
                </button>
              );
            })}
          </div>
        ))}
      </nav>
      {showGlossary && <GlossaryCard glossary={course.glossary} />}
      <span hidden>{index}</span>
    </>
  );
}
