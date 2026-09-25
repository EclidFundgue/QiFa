import { useEffect, useMemo, useState } from "react";
import type { SlideWithChapter } from "../types";

const STORAGE_KEY = "qifa-cursor";

function maxStep(slide: SlideWithChapter | undefined): number {
  return Math.max(0, (slide?.slide.steps.length ?? 0) - 1);
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

export function useCourseCursor(slides: SlideWithChapter[]) {
  const [index, setIndex] = useState(() => {
    const fromHash = readHash(slides);
    if (fromHash !== null) return Math.min(fromHash, Math.max(0, slides.length - 1));
    const stored = readStorage();
    if (stored !== null) return Math.min(stored, Math.max(0, slides.length - 1));
    return 0;
  });
  const [step, setStep] = useState(0);

  const current = slides[index];

  const go = (target: number) => {
    if (slides.length === 0) return;
    const clamped = Math.min(Math.max(target, 0), slides.length - 1);
    setIndex(clamped);
    setStep(0);
  };

  const next = () => {
    if (!current) return;
    if (step < maxStep(current)) {
      setStep(step + 1);
      return;
    }
    if (index < slides.length - 1) go(index + 1);
  };

  const prev = () => {
    if (step > 0) {
      setStep(step - 1);
      return;
    }
    if (index > 0) {
      setIndex(index - 1);
      setStep(maxStep(slides[index - 1]));
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

  return { index, step, current, go, next, prev, progress };
}
