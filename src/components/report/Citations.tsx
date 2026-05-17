"use client";

import { ExternalLink } from "lucide-react";
import type { Evidence } from "@/lib/types";

interface Props {
  ids: string[];
  evidence: Record<string, Evidence>;
  neonColor: string;
}

const platformLabel: Record<Evidence["platform"], string> = {
  xhs: "小红书",
  douyin: "抖音",
};

export default function Citations({ ids, evidence, neonColor }: Props) {
  const items = ids
    .map((id) => evidence[id])
    .filter((e): e is Evidence => Boolean(e));

  if (items.length === 0) return null;

  return (
    <div className="mt-4 pt-3 border-t border-textMuted/10">
      <div
        className="text-[10px] uppercase tracking-widest mb-2"
        style={{ color: neonColor }}
      >
        来源
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((e, i) => (
          <li key={i} className="text-xs">
            <a
              href={e.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-start gap-1.5 text-textMuted hover:text-text transition-colors"
            >
              <span
                className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono"
                style={{
                  background: `${neonColor}22`,
                  color: neonColor,
                }}
              >
                {platformLabel[e.platform]}
              </span>
              <span className="line-clamp-1 flex-1">{e.title}</span>
              <ExternalLink size={11} className="shrink-0 mt-0.5 opacity-60" />
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
