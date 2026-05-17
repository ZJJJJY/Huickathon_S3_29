import type { VideoRef } from "@/lib/types";
import { Play } from "lucide-react";

interface Props {
  video: VideoRef;
  sectionTitle: string;
  neonColor: string;
}

export default function VideoRefCard({ video, sectionTitle, neonColor }: Props) {
  const likes =
    video.likes >= 10000
      ? `${(video.likes / 10000).toFixed(1)}w`
      : video.likes > 0
      ? `${video.likes}`
      : null;

  return (
    <a
      href={video.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-2xl overflow-hidden mt-4 hover:opacity-90 transition-opacity"
      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
    >
      <div className="flex items-stretch gap-0">
        {/* Left content */}
        <div className="flex-1 min-w-0 p-4 flex flex-col gap-2">
          {/* Top label */}
          <span className="text-[11px] font-medium" style={{ color: neonColor }}>
            {sectionTitle} · 抖音参考
          </span>

          {/* Title with opening quote mark */}
          <div className="relative pl-5">
            <span
              className="absolute left-0 top-0 text-3xl leading-none font-serif"
              style={{ color: neonColor, opacity: 0.7 }}
            >
              "
            </span>
            <p className="text-[15px] font-bold leading-snug line-clamp-2 text-white">
              {video.title || "（无标题）"}
            </p>
          </div>

          {/* Author row */}
          <div className="flex items-center gap-2 mt-auto">
            {/* Avatar placeholder */}
            <div
              className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-[9px] font-bold text-bg"
              style={{ background: neonColor }}
            >
              {video.author?.[0] ?? "D"}
            </div>
            <span className="text-xs text-textMuted truncate">
              {video.author}
            </span>
            {likes && (
              <span className="text-xs text-textMuted/50 ml-auto flex-shrink-0">
                ♥ {likes}
              </span>
            )}
          </div>
        </div>

        {/* Right thumbnail */}
        {video.cover && (
          <div className="flex-shrink-0 w-24 relative self-stretch">
            <img
              src={video.cover}
              alt=""
              className="w-full h-full object-cover"
            />
            {/* Play button overlay */}
            <div className="absolute inset-0 flex items-center justify-center bg-black/20">
              <div className="w-8 h-8 rounded-full bg-white/80 flex items-center justify-center">
                <Play size={14} className="text-gray-900 ml-0.5" fill="currentColor" />
              </div>
            </div>
          </div>
        )}
      </div>
    </a>
  );
}
