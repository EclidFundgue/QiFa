import type { Slide } from "../types";

interface Props {
  slide: Slide;
}

/** 本地视频嵌入：静音可看，带控件与文字替代。 */
export default function VideoEmbed({ slide }: Props) {
  const video = slide.visuals.find((visual) => visual.type === "video" && visual.asset) ?? slide.visuals[0];
  return (
    <div>
      <h1 className="slide-title">{slide.title}</h1>
      {video?.asset ? (
        <figure style={{ margin: 0 }}>
          <video className="media-frame" src={video.asset} controls preload="metadata" aria-label={video.purpose}>
            您的浏览器不支持视频播放。
          </video>
          <figcaption className="refs">{video.purpose}</figcaption>
        </figure>
      ) : (
        <p className="slide-goal">该页未提供视频素材（已降级为讲解）。</p>
      )}
    </div>
  );
}
