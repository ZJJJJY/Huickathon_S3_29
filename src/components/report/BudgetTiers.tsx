"use client";

import type { BudgetTiersContent } from "@/lib/types";

interface Props {
  content: BudgetTiersContent;
  neonColor: string;
}

export default function BudgetTiers({ content, neonColor }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {content.tiers.map((t, i) => (
        <div
          key={i}
          className="rounded-xl border p-3 flex flex-col gap-2"
          style={{
            borderColor: `${neonColor}44`,
            background: `linear-gradient(160deg, ${neonColor}14, transparent 70%)`,
          }}
        >
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-semibold text-text">{t.name}</span>
            <span
              className="text-xs font-mono"
              style={{ color: neonColor }}
            >
              {t.price_range}
            </span>
          </div>
          <ul className="text-xs text-text/85 space-y-1 list-disc pl-4 marker:text-textMuted">
            {t.items.map((it, j) => (
              <li key={j}>{it}</li>
            ))}
          </ul>
          {t.note && (
            <p className="text-[11px] text-textMuted leading-relaxed">
              {t.note}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
