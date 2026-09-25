export type RefKind = "paper" | "code" | "media";

export interface SourceRef {
  kind: RefKind;
  locator: string;
  source_id: string;
}

export interface Point {
  text: string;
  step_id: string;
  refs: SourceRef[];
}

export interface Visual {
  id: string;
  type: string;
  purpose: string;
  asset: string;
  refs: SourceRef[];
}

export interface Step {
  id: string;
  label: string;
}

export interface Slide {
  id: string;
  title: string;
  kind: string;
  points: Point[];
  steps: Step[];
  visuals: Visual[];
  media_refs: string[];
  narration: string;
  custom: string;
}

export interface Chapter {
  id: string;
  title: string;
  goal: string;
  slides: Slide[];
}

export interface GlossaryEntry {
  term: string;
  translation: string;
  definition: string;
}

export interface Course {
  course: {
    title: string;
    language: string;
    audience: string;
    goal: string;
    theme: string;
    duration_minutes: number;
  };
  glossary: GlossaryEntry[];
  chapters: Chapter[];
  has_degradations: boolean;
}

export interface SlideWithChapter {
  chapterId: string;
  chapterTitle: string;
  slide: Slide;
}
