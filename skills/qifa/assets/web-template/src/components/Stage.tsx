import type { ReactNode } from "react";
import { useStageScale } from "../hooks/useStageScale";

interface StageProps {
  children: ReactNode;
}

/** 16:9 固定舞台，内容按设计尺寸等比缩放。 */
export default function Stage({ children }: StageProps) {
  const { scale, width, height } = useStageScale();
  return (
    <div
      style={{
        width: `${width * scale}px`,
        height: `${height * scale}px`,
        position: "relative",
        overflow: "hidden"
      }}
    >
      <div
        className="stage"
        style={{
          width: `${width}px`,
          height: `${height}px`,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
          position: "absolute",
          top: 0,
          left: 0
        }}
      >
        {children}
      </div>
    </div>
  );
}
