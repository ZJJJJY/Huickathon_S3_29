"use client";

import { ArrowUpRight } from "lucide-react";
import type { CardsContent } from "@/lib/types";

interface Props {
  content: CardsContent;
  neonColor: string;
}

export default function Cards({ content, neonColor }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {content.cards.map((c, i) => {
        const inner = (
          <div
            className="rounded-xl border p-3 h-full flex flex-col gap-1.5 transition-colors"
            style={{
              borderColor: `${neonColor}33`,
              background: `linear-gradient(150deg, ${neonColor}10, transparent 75%)`,
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-semibold text-text line-clamp-2">
                {c.title}
              </div>
              {c.url && (
                <ArrowUpRight
                  size={14}
                  style={{ color: neonColor }}
                  className="shrink-0 mt-0.5"
                />
              )}
            </div>
            <p className="text-xs text-text/80 leading-relaxed line-clamp-3">
              {c.description}
            </p>
            {c.meta && (
              <div
                className="text-[11px] font-mono mt-auto"
                style={{ color: neonColor }}
              >
                {c.meta}
              </div>
            )}
          </div>
        );
        return c.url ? (
          <a key={i} href={c.url} target="_blank" rel="noreferrer">
            {inner}
          </a>
        ) : (
          <div key={i}>{inner}</div>
        );
      })}
    </div>
  );
}
