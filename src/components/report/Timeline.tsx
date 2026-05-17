"use client";

import type { TimelineContent } from "@/lib/types";

interface Props {
  content: TimelineContent;
  neonColor: string;
}

export default function Timeline({ content, neonColor }: Props) {
  return (
    <ol className="relative pl-5">
      <span
        aria-hidden
        className="absolute left-1.5 top-1 bottom-1 w-px"
        style={{ background: `${neonColor}55` }}
      />
      {content.entries.map((e, i) => (
        <li key={i} className="relative pb-4 last:pb-0">
          <span
            aria-hidden
            className="absolute -left-[14px] top-1.5 w-2.5 h-2.5 rounded-full"
            style={{
              background: neonColor,
              boxShadow: `0 0 8px ${neonColor}`,
            }}
          />
          <div
            className="text-[10px] uppercase tracking-widest mb-0.5 font-mono"
            style={{ color: neonColor }}
          >
            {e.label}
          </div>
          <div className="text-sm font-semibold text-text mb-0.5">
            {e.title}
          </div>
          <p className="text-xs text-text/80 leading-relaxed">{e.detail}</p>
        </li>
      ))}
    </ol>
  );
}
