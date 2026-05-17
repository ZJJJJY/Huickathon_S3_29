"use client";

import { Check } from "lucide-react";
import type { ChecklistContent } from "@/lib/types";

interface Props {
  content: ChecklistContent;
  neonColor: string;
}

export default function Checklist({ content, neonColor }: Props) {
  return (
    <ul className="flex flex-col gap-2">
      {content.items.map((it, i) => (
        <li
          key={i}
          className="flex gap-3 rounded-xl border border-textMuted/15 bg-bg/40 p-3"
        >
          <div
            className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
            style={{
              background: `${neonColor}22`,
              color: neonColor,
            }}
          >
            <Check size={14} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-text">{it.title}</div>
            <p className="text-xs text-text/80 leading-relaxed mt-0.5">
              {it.detail}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
