interface Props {
  text: string;
}

/** 页内字幕：讲稿的可开关投影。 */
export default function Subtitle({ text }: Props) {
  return (
    <p className="narration" lang="zh-CN">
      {text}
    </p>
  );
}
