"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { QAContent } from "@/lib/types";

interface Props {
  content: QAContent;
  neonColor: string;
}

export default function QA({ content, neonColor }: Props) {
  return (
    <ul className="flex flex-col gap-2">
      {content.items.map((it, i) => (
        <QARow key={i} q={it.q} a={it.a} neonColor={neonColor} />
      ))}
    </ul>
  );
}

function QARow({
  q,
  a,
  neonColor,
}: {
  q: string;
  a: string;
  neonColor: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <li
      className="rounded-xl border border-textMuted/15 bg-bg/40 overflow-hidden"
      style={{
        borderColor: open ? `${neonColor}55` : undefined,
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 p-3 text-left"
      >
        <span className="text-sm font-semibold text-text">{q}</span>
        <ChevronDown
          size={16}
          className="shrink-0 transition-transform"
          style={{
            color: neonColor,
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
          }}
        />
      </button>
      {open && (
        <div className="px-3 pb-3 text-xs leading-relaxed text-text/85 whitespace-pre-line">
          {a}
        </div>
      )}
    </li>
  );
}
