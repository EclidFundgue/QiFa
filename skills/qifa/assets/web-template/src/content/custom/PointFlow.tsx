import type { CSSProperties } from "react";
import type { Slide } from "../../types";
import { focusOf } from "./focus";

interface Props {
  slide: Slide;
  step: number;
  sentence: number;
  sentences: string[];
}

const nodeBase: CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--slide-radius)",
  padding: "13px 16px",
  transition: "opacity 240ms ease, border-color 240ms ease, background 240ms ease"
};

const refsStyle: CSSProperties = {
  color: "var(--muted)",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  marginTop: 6,
  wordBreak: "break-all"
};

/** 把讲点文本拆成可用于对齐字幕的关键词（公式与标点先剥掉）。 */
function tokens(text: string): string[] {
  return text
    .replace(/\$[^$]*\$/g, " ")
    .split(/[\s、，。：；/（）()·+×→←|]+/)
    .map((t) => t.replace(/^[^\u4e00-\u9fffA-Za-z0-9_]+|[^\u4e00-\u9fffA-Za-z0-9_.-]+$/g, ""))
    .filter((t) => t.length >= 2);
}

function focusIndex(points: { text: string }[], current: string): number | null {
  if (!current) return null;
  for (let i = 0; i < points.length; i += 1) {
    if (tokens(points[i].text).some((token) => current.includes(token))) return i;
  }
  return null;
}

function splitLabel(text: string): [string, string] {
  const index = text.indexOf("：");
  if (index > 0 && index < text.length - 1) return [text.slice(0, index), text.slice(index + 1)];
  return ["", text];
}

function nodeStyle(focus: "neutral" | "on" | "off"): CSSProperties {
  if (focus === "on") {
    return {
      ...nodeBase,
      background: "color-mix(in srgb, var(--accent) 10%, var(--surface))",
      borderColor: "color-mix(in srgb, var(--accent) 60%, var(--border))"
    };
  }
  if (focus === "off") return { ...nodeBase, opacity: 0.4 };
  return nodeBase;
}

/** 通用示意图：文本页只放关键词，版式按页面类型选（时间线 / 对比列 / 收束链 / 卡片网格）。 */
export default function PointFlow({ slide, sentence, sentences }: Props) {
  const current = sentences[sentence] ?? "";
  const hot = focusIndex(slide.points, current);
  const mode =
    slide.kind === "comparison"
      ? "columns"
      : slide.kind === "summary"
        ? "chain"
        : slide.points.length > 3
          ? "grid"
          : "timeline";

  if (mode === "columns") {
    const labeled = slide.points.filter((point) => splitLabel(point.text)[0]);
    const footers = slide.points.filter((point) => !splitLabel(point.text)[0]);
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <h1 className="slide-title">{slide.title}</h1>
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: `repeat(${Math.max(1, labeled.length)}, minmax(0, 1fr))` }}>
          {labeled.map((point, index) => {
            const [label, detail] = splitLabel(point.text);
            return (
              <div key={index} style={nodeStyle(focusOf(hot, slide.points.indexOf(point)))}>
                <div style={{ color: "var(--accent)", fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{label}</div>
                <div style={{ fontSize: 17, lineHeight: 1.5 }}>{detail}</div>
                {point.refs.length > 0 && <div style={refsStyle}>{point.refs.map((ref) => ref.locator).join("；")}</div>}
              </div>
            );
          })}
        </div>
        {footers.map((point) => (
          <div
            key={point.text}
            style={{
              ...nodeStyle(focusOf(hot, slide.points.indexOf(point))),
              borderLeft: "3px solid var(--accent)",
              display: "grid",
              gap: 10,
              gridTemplateColumns: "minmax(0, 1fr) auto"
            }}
          >
            <div style={{ fontSize: 18, lineHeight: 1.5 }}>{point.text}</div>
            <div style={{ ...refsStyle, marginTop: 0, maxWidth: 520, textAlign: "right" }}>
              {point.refs.map((ref) => ref.locator).join("；")}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (mode === "grid") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <h1 className="slide-title">{slide.title}</h1>
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
          {slide.points.map((point, index) => (
            <div key={index} style={nodeStyle(focusOf(hot, index))}>
              <div style={{ fontSize: 18, lineHeight: 1.5 }}>{point.text}</div>
              {point.refs.length > 0 && <div style={refsStyle}>{point.refs.map((ref) => ref.locator).join("；")}</div>}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (mode === "chain") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <h1 className="slide-title">{slide.title}</h1>
        <div style={{ alignItems: "stretch", display: "flex", gap: 8 }}>
          {slide.points.map((point, index) => (
            <div key={index} style={{ alignItems: "center", display: "flex", flex: 1, gap: 8 }}>
              <div style={{ ...nodeStyle(focusOf(hot, index)), flex: 1 }}>
                <div style={{ fontSize: 18, lineHeight: 1.5 }}>{point.text}</div>
                {point.refs.length > 0 && <div style={refsStyle}>{point.refs.map((ref) => ref.locator).join("；")}</div>}
              </div>
              {index < slide.points.length - 1 && (
                <svg aria-hidden="true" height="18" viewBox="0 0 24 18" width="24">
                  <path d="M2 9h16m0 0l-5-5m5 5l-5 5" fill="none" stroke="var(--accent)" strokeLinecap="round" strokeWidth="2" />
                </svg>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <h1 className="slide-title">{slide.title}</h1>
      <div style={{ display: "flex", flexDirection: "column", gap: 0, position: "relative", paddingLeft: 26 }}>
        <div
          style={{
            background: "var(--accent)",
            borderRadius: 2,
            bottom: 14,
            left: 8,
            opacity: 0.45,
            position: "absolute",
            top: 14,
            width: 2
          }}
        />
        {slide.points.map((point, index) => (
          <div key={index} style={{ display: "flex", gap: 14, paddingBottom: 12 }}>
            <span
              style={{
                background: "var(--bg)",
                border: "2px solid var(--accent)",
                borderRadius: 999,
                color: "var(--accent)",
                flex: "0 0 auto",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                height: 22,
                lineHeight: "18px",
                marginLeft: -26,
                marginTop: 12,
                textAlign: "center",
                width: 22
              }}
            >
              {index + 1}
            </span>
            <div style={{ ...nodeStyle(focusOf(hot, index)), flex: 1 }}>
              <div style={{ fontSize: 18, lineHeight: 1.5 }}>{point.text}</div>
              {point.refs.length > 0 && <div style={refsStyle}>{point.refs.map((ref) => ref.locator).join("；")}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
