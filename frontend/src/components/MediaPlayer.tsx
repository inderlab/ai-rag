import { forwardRef, useImperativeHandle, useRef } from "react";
import type { PlayerHandle } from "./YouTubePlayer";

type Props = { src: string; start?: number };

const MediaPlayer = forwardRef<PlayerHandle, Props>(({ src, start = 0 }, ref) => {
  const el = useRef<HTMLVideoElement>(null);

  useImperativeHandle(ref, () => ({
    seekTo(seconds: number) {
      if (!el.current) return;
      el.current.currentTime = seconds;
      void el.current.play().catch(() => undefined);
    },
  }));

  return (
    <video
      ref={el}
      src={start ? `${src}#t=${Math.floor(start)}` : src}
      controls
      preload="metadata"
      className="aspect-video w-full rounded-lg bg-black"
    />
  );
});

MediaPlayer.displayName = "MediaPlayer";

export default MediaPlayer;
