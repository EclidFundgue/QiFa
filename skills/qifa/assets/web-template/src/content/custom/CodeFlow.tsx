import type { CSSProperties, ReactNode } from "react";
import type { Point, Slide } from "../../types";
import { focusOf, focusStyle } from "./focus";

interface Props {
  slide: Slide;
  step: number;
  sentence: number;
  sentences: string[];
}

const cardBase: CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--slide-radius)",
  padding: "9px 13px 10px",
  flex: 1,
  minWidth: 0,
  transition: "opacity 240ms ease, border-color 240ms ease, background 240ms ease"
};

/** 从讲点文本里抽出可与字幕对齐的关键词（去掉 markdown 代码标记与标点）。 */
function tokens(text: string): string[] {
  return text
    .replace(/`/g, "")
    .replace(/\$[^$]*\$/g, " ")
    .split(/[\s、，。：；/（）()·+×→←|]+/)
    .map((token) => token.replace(/^[^\u4e00-\u9fffA-Za-z0-9_]+|[^\u4e00-\u9fffA-Za-z0-9_.-]+$/g, ""))
    .filter((token) => token.length >= 2);
}

function focusIndex(points: Point[], current: string): number | null {
  if (!current) return null;
  for (let i = 0; i < points.length; i += 1) {
    if (tokens(points[i].text).some((token) => current.includes(token))) return i;
  }
  return null;
}

function renderText(text: string): ReactNode {
  const parts = text.split(/(`[^`]*`)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
          return <code key={index}>{part.slice(1, -1)}</code>;
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

/**
 * 代码走读页通用组件：把讲点排成带连接线的符号流程，字幕指向哪个讲点就高亮哪个；
 * 有 steps 时，未到的分组压暗，当前分组正常，形成粗粒度推进。
 * 用法：在 `custom/index.ts` 把 `kind: "code-walkthrough"` 的 slide 注册到本组件。
 */
export default function CodeFlow({ slide, step, sentence, sentences }: Props) {
  const current = sentences[sentence] ?? "";
  const hot = focusIndex(slide.points, current);
  const hasSteps = slide.steps.length > 1;
  const purpose = slide.visuals.find((visual) => visual.purpose)?.purpose ?? "";

  const pointStepIndex = (point: Point): number => {
    if (!point.step_id) return -1;
    return slide.steps.findIndex((item) => item.id === point.step_id);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, height: "100%", minHeight: 0 }}>
      <div>
        <h1 className="slide-title" style={{ marginBottom: purpose ? 5 : 0 }}>
          {slide.title}
        </h1>
        {purpose && (
          <p style={{ color: "var(--muted)", fontSize: 12.5, lineHeight: 1.4, margin: 0 }}>{purpose}</p>
        )}
      </div>
      {hasSteps && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {slide.steps.map((item, index) => {
            const active = index <= step;
            return (
              <span
                key={item.id}
                style={{
                  border: `1px solid ${active ? "color-mix(in srgb, var(--accent) 55%, var(--border))" : "var(--border)"}`,
                  background: active ? "color-mix(in srgb, var(--accent) 12%, var(--surface))" : "transparent",
                  color: active ? "var(--text)" : "var(--muted)",
                  borderRadius: 999,
                  fontFamily: "var(--font-mono)",
                  fontSize: 11.5,
                  opacity: active ? 1 : 0.65,
                  padding: "3px 10px"
                }}
              >
                {index + 1}. {item.label}
              </span>
            );
          })}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", paddingLeft: 26, position: "relative", flex: 1, minHeight: 0 }}>
        <div
          style={{
            background: "var(--accent)",
            borderRadius: 2,
            bottom: 10,
            left: 8,
            opacity: 0.35,
            position: "absolute",
            top: 12,
            width: 2
          }}
        />
        {slide.points.map((point, index) => {
          const groupIndex = pointStepIndex(point);
          const dimmed = hasSteps && groupIndex > step && hot === null;
          const focus = hot !== null ? focusOf(hot, index) : dimmed ? "off" : "neutral";
          return (
            <div key={`${slide.id}-${index}`} style={{ display: "flex", gap: 12, paddingBottom: index < slide.points.length - 1 ? 8 : 0 }}>
              <span
                style={{
                  background: "var(--bg)",
                  border: "2px solid var(--accent)",
                  borderRadius: 999,
                  color: "var(--accent)",
                  flex: "0 0 auto",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  height: 20,
                  lineHeight: "16px",
                  marginLeft: -26,
                  marginTop: 9,
                  textAlign: "center",
                  width: 20
                }}
              >
                {index + 1}
              </span>
              <div style={focusStyle(focus, cardBase)}>
                <div style={{ fontSize: 16.5, lineHeight: 1.5 }}>{renderText(point.text)}</div>
                {point.refs.length > 0 && (
                  <div
                    style={{
                      color: "var(--muted)",
                      fontFamily: "var(--font-mono)",
                      fontSize: 10.5,
                      marginTop: 5,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap"
                    }}
                  >
                    {point.refs.map((ref) => ref.locator).join("；")}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
