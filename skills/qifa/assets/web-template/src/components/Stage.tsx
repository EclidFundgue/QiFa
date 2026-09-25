import { useRef, type ReactNode } from "react";
import { useStageScale } from "../hooks/useStageScale";

interface StageProps {
  children: ReactNode;
}

/**
 * 16:9 舞台：唯一缩放单元。
 *
 * 结构（三层）：
 *   .stage-area   ← 由 App 分配的实际可用区域（侧栏占位后剩下的空间）
 *   .stage-fitter ← 尺寸 = 缩放后的真实像素，让布局系统看到真实占位
 *   .stage        ← 1280×720 设计画布，从左上角缩放
 *
 * 舞台内部：.stage-body 负责滚动，底部只为字幕保留空间；播放控件由 App
 * 放在舞台外部，避免遮挡课程内容。
 */
export default function Stage({ children }: StageProps) {
  const areaRef = useRef<HTMLDivElement>(null);
  const { scale, width, height } = useStageScale(areaRef);
  return (
    <div className="stage-area" ref={areaRef}>
      <div className="stage-fitter" style={{ width: `${width * scale}px`, height: `${height * scale}px` }}>
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
    </div>
  );
}
