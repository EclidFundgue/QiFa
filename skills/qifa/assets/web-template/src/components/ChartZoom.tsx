import { useState } from "react";
import type { Visual } from "../types";

interface Props {
  visual: Visual;
}

/** 图表/图片：点击放大，再点还原。 */
export default function ChartZoom({ visual }: Props) {
  const [zoomed, setZoomed] = useState(false);
  if (!visual.asset) return null;
  return (
    <figure style={{ margin: "20px 0 0" }}>
      <button
        type="button"
        className={`media-frame${zoomed ? " zoomed" : ""}`}
        onClick={() => setZoomed((value) => !value)}
        aria-label={`${visual.purpose}（点击${zoomed ? "缩小" : "放大"}）`}
        style={{ padding: 0, width: "100%" }}
      >
        <img src={visual.asset} alt={visual.purpose} />
      </button>
      <figcaption className="refs">
        {visual.purpose}
        {visual.refs.length > 0 && ` · ${visual.refs.map((ref) => ref.locator).join("；")}`}
      </figcaption>
    </figure>
  );
}
