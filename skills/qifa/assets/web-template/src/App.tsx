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
  const { step, current, go, next, prev, progress, sentence, sentences } = useCourseCursor(slides);
  const [showSubtitle, setShowSubtitle] = useState(true);
  const [showGlossary, setShowGlossary] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "s" || event.key === "S") setShowSubtitle((value) => !value);
      if (event.key === "g" || event.key === "G") setShowGlossary((value) => !value);
      if (event.key === "Escape") setShowGlossary(false);
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
  const currentIndex = slides.findIndex((item) => item.slide.id === current.slide.id);
  const progressPercent = Math.round(progress * 100);

  return (
    <>
      {course.has_degradations && (
        <div className="degradation-banner" role="status">
          本课程存在降级项（部分内容以更保守的方式呈现），详见 review/qa-report.md
        </div>
      )}
      <div className="app-shell">
        <main className="course-column">
          <Stage>
            <div className="stage-body">
              {Custom ? (
                <Custom slide={current.slide} step={step} sentence={sentence} sentences={sentences} />
              ) : (
                <SlideRenderer slide={current.slide} step={step} />
              )}
            </div>
            {showSubtitle && (
              <Subtitle
                text={sentences[sentence] ?? ""}
                index={sentence}
                total={sentences.length}
              />
            )}
          </Stage>
          <section className="control-dock" aria-label="课程播放控制">
            <div className="course-status">
              <span className="status-chapter">{current.chapterTitle}</span>
              <span className="status-count">
                {currentIndex + 1} / {slides.length}
              </span>
            </div>
            <div
              className="progress"
              role="progressbar"
              aria-label="课程进度"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progressPercent}
            >
              <span style={{ width: `${progressPercent}%` }} />
            </div>
            <div className="controls">
              <button className="control-step" type="button" onClick={prev} aria-label="上一句或上一页">
                <span aria-hidden="true">←</span> 上一步
              </button>
              <div className="control-options">
                <button type="button" onClick={() => setShowSubtitle((value) => !value)} aria-pressed={showSubtitle}>
                  字幕 <kbd>S</kbd>
                </button>
                <button type="button" onClick={() => setShowGlossary((value) => !value)} aria-pressed={showGlossary}>
                  术语表 <kbd>G</kbd>
                </button>
              </div>
              <button className="control-step control-next" type="button" onClick={next} aria-label="下一句或下一页">
                下一步 <span aria-hidden="true">→</span>
              </button>
            </div>
          </section>
        </main>
        <nav className="side-nav" id="course-nav" aria-label="课程导航">
          <header className="nav-header">
            <div>
              <p>课程大纲</p>
              <span>{course.chapters.length} 章 · {slides.length} 节</span>
            </div>
          </header>
          <div className="nav-scroll">
            {course.chapters.map((chapter, chapterIndex) => (
              <section
                className={`nav-chapter${chapter.id === current.chapterId ? " active" : ""}`}
                key={chapter.id}
              >
                <div className="chapter-heading">
                  <span>{String(chapterIndex + 1).padStart(2, "0")}</span>
                  <p>{chapter.title}</p>
                </div>
                <div className="chapter-slides">
                  {chapter.slides.map((slide, slideIndex) => {
                    const target = slides.findIndex((item) => item.slide.id === slide.id);
                    return (
                      <button
                        type="button"
                        key={slide.id}
                        className={slide.id === current.slide.id ? "active" : ""}
                        aria-current={slide.id === current.slide.id ? "step" : undefined}
                        onClick={() => go(target)}
                      >
                        <span className="nav-slide-id">{String(slideIndex + 1).padStart(2, "0")}</span>
                        <span className="nav-slide-title">{slide.title}</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
          <footer className="nav-footer">
            <span>方向键切换</span>
            <span>F 全屏</span>
          </footer>
        </nav>
      </div>
      {showGlossary && (
        <>
          <div className="glossary-backdrop" onClick={() => setShowGlossary(false)} aria-hidden="true" />
          <GlossaryCard glossary={course.glossary} onClose={() => setShowGlossary(false)} />
        </>
      )}
    </>
  );
}
