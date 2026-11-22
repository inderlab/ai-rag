import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

type YTPlayer = {
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
  playVideo: () => void;
  destroy: () => void;
};

type YTNamespace = {
  Player: new (el: HTMLElement, options: { videoId: string; playerVars?: Record<string, number> }) => YTPlayer;
};

declare global {
  interface Window {
    YT?: YTNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

export type PlayerHandle = { seekTo: (seconds: number) => void };

let apiReady: Promise<YTNamespace> | null = null;

function loadApi(): Promise<YTNamespace> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (!apiReady) {
    apiReady = new Promise((resolve) => {
      window.onYouTubeIframeAPIReady = () => resolve(window.YT!);
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(script);
    });
  }
  return apiReady;
}

const YouTubePlayer = forwardRef<PlayerHandle, { videoId: string; start?: number }>(({ videoId, start = 0 }, ref) => {
  const holder = useRef<HTMLDivElement>(null);
  const player = useRef<YTPlayer | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadApi().then((YT) => {
      if (cancelled || !holder.current) return;
      const el = document.createElement("div");
      holder.current.appendChild(el);
      player.current = new YT.Player(el, { videoId, playerVars: { rel: 0, start: Math.floor(start) } });
    });
    return () => {
      cancelled = true;
      player.current?.destroy();
      player.current = null;
      if (holder.current) holder.current.innerHTML = "";
    };
  }, [videoId, start]);

  useImperativeHandle(ref, () => ({
    seekTo(seconds: number) {
      player.current?.seekTo(seconds, true);
      player.current?.playVideo();
    },
  }));

  return (
    <div className="aspect-video w-full overflow-hidden rounded-lg bg-black [&_iframe]:h-full [&_iframe]:w-full" ref={holder} />
  );
});

YouTubePlayer.displayName = "YouTubePlayer";

export default YouTubePlayer;
