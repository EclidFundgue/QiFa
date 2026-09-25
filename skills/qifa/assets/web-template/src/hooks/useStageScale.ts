import { useEffect, useState, type RefObject } from "react";

const DESIGN_WIDTH = 1280;
const DESIGN_HEIGHT = 720;

/**
 * 16:9 舞台等比缩放：以宿主容器（而不是整个窗口）测量可用空间，
 * 留出 24px 呼吸位，保证舞台永远不超出可视范围，也不会被侧栏遮挡。
 */
export function useStageScale(containerRef: RefObject<HTMLElement | null>) {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const update = () => {
      const availableWidth = Math.max(320, element.clientWidth - 24);
      const availableHeight = Math.max(180, element.clientHeight - 24);
      setScale(Math.min(availableWidth / DESIGN_WIDTH, availableHeight / DESIGN_HEIGHT));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [containerRef]);

  return { scale, width: DESIGN_WIDTH, height: DESIGN_HEIGHT };
}
