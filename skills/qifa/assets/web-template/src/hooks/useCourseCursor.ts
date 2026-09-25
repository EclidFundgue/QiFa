import { useEffect, useMemo, useState } from "react";
import { splitSentences } from "../content/sentences";
import type { SlideWithChapter } from "../types";

const STORAGE_KEY = "qifa-cursor";

function maxStep(slide: SlideWithChapter | undefined): number {
  return Math.max(0, (slide?.slide.steps.length ?? 0) - 1);
}

/** 一页的讲稿拆成句；空讲稿也保留一个空句，保证游标逻辑简单。 */
function sentencesOf(slide: SlideWithChapter | undefined): string[] {
  const list = splitSentences(slide?.slide.narration ?? "");
  return list.length > 0 ? list : [""];
}

function readHash(slides: SlideWithChapter[]): number | null {
  const match = window.location.hash.match(/#c(\d+)\/s(\d+)/i);
  if (!match) return null;
  const targetChapter = `C${String(Number(match[1])).padStart(2, "0")}`;
  const targetSlide = Number(match[2]) - 1;
  let seen = 0;
  for (let i = 0; i < slides.length; i += 1) {
    if (slides[i].chapterId !== targetChapter) continue;
    if (seen === targetSlide) return i;
    seen += 1;
  }
  return null;
}

function readStorage(): number | null {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  const value = Number(raw);
  return Number.isFinite(value) && value >= 0 ? value : null;
}

/**
 * 课程游标：页（index）+ 句（sentence）+ 额外步（step）。
 *
 * 字幕一次只显示一句，一次“下一步”推进一句；句读完后继续推进要点（step），
 * 要点也到底才翻页。页内的要点按句序成比例展开：讲得越多，露出的要点越多。
 */
export function useCourseCursor(slides: SlideWithChapter[]) {
  const [index, setIndex] = useState(() => {
    const fromHash = readHash(slides);
    if (fromHash !== null) return Math.min(fromHash, Math.max(0, slides.length - 1));
    const stored = readStorage();
    if (stored !== null) return Math.min(stored, Math.max(0, slides.length - 1));
    return 0;
  });
  const [step, setStep] = useState(0);
  const [sentence, setSentence] = useState(0);

  const current = slides[index];
  const sentences = useMemo(() => sentencesOf(current), [current]);
  const total = sentences.length;
  const lastStep = maxStep(current);
  const derivedStep = lastStep === 0 ? 0 : Math.min(lastStep, Math.floor((sentence * (lastStep + 1)) / total));
  const visibleStep = Math.min(lastStep, Math.max(step, derivedStep));

  const go = (target: number) => {
    if (slides.length === 0) return;
    const clamped = Math.min(Math.max(target, 0), slides.length - 1);
    setIndex(clamped);
    setStep(0);
    setSentence(0);
  };

  const next = () => {
    if (!current) return;
    if (sentence < total - 1) {
      setSentence(sentence + 1);
      return;
    }
    if (visibleStep < lastStep) {
      setStep(visibleStep + 1);
      return;
    }
    if (index < slides.length - 1) go(index + 1);
  };

  const prev = () => {
    if (!current) return;
    if (step > derivedStep) {
      setStep(step - 1);
      return;
    }
    if (sentence > 0) {
      setSentence(sentence - 1);
      return;
    }
    if (index > 0) {
      const target = slides[index - 1];
      setIndex(index - 1);
      setStep(maxStep(target));
      setSentence(sentencesOf(target).length - 1);
    }
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "ArrowRight" || event.key === " " || event.key === "PageDown") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        prev();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        prev();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  useEffect(() => {
    if (!current) return;
    window.localStorage.setItem(STORAGE_KEY, String(index));
    const chapterNumber = Number(current.chapterId.replace(/\D/g, "")) || 1;
    const slideNumber = slides.filter((item) => item.chapterId === current.chapterId).indexOf(current) + 1;
    window.history.replaceState(null, "", `#c${chapterNumber}/s${slideNumber}`);
  }, [index, current, slides]);

  const progress = useMemo(
    () => (slides.length <= 1 ? 1 : index / (slides.length - 1)),
    [index, slides.length]
  );

  return { step: visibleStep, current, go, next, prev, progress, sentence, sentences };
}
