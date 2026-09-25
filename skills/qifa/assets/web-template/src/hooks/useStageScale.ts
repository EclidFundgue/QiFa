import { useEffect, useState } from "react";

const DESIGN_WIDTH = 1280;
const DESIGN_HEIGHT = 720;

/** 16:9 舞台等比缩放：适配窗口，保持设计尺寸坐标。 */
export function useStageScale() {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const update = () => {
      const availableWidth = window.innerWidth - 32;
      const availableHeight = window.innerHeight - 32;
      setScale(Math.min(availableWidth / DESIGN_WIDTH, availableHeight / DESIGN_HEIGHT));
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return { scale, width: DESIGN_WIDTH, height: DESIGN_HEIGHT };
}
