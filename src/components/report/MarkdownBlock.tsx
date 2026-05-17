"use client";

import type { MarkdownContent } from "@/lib/types";

interface Props {
  content: MarkdownContent;
}

// 极简 markdown：段落 + **bold** + 行首 - 列表。
// 不引入 markdown 库，保持 bundle 小；离线生成的文本受控。
export default function MarkdownBlock({ content }: Props) {
  const blocks = parseBlocks(content.text);
  return (
    <div className="text-sm leading-relaxed text-text/90 space-y-3">
      {blocks.map((b, i) =>
        b.type === "ul" ? (
          <ul key={i} className="space-y-1 pl-4 list-disc marker:text-textMuted">
            {b.items.map((it, j) => (
              <li key={j}>{renderInline(it)}</li>
            ))}
          </ul>
        ) : (
          <p key={i}>{renderInline(b.text)}</p>
        ),
      )}
    </div>
  );
}

type Block =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] };

function parseBlocks(src: string): Block[] {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const out: Block[] = [];
  let buf: string[] = [];
  let list: string[] | null = null;

  const flushPara = () => {
    if (buf.length) {
      out.push({ type: "p", text: buf.join(" ").trim() });
      buf = [];
    }
  };
  const flushList = () => {
    if (list && list.length) {
      out.push({ type: "ul", items: list });
    }
    list = null;
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushPara();
      flushList();
      continue;
    }
    const m = line.match(/^[-*]\s+(.*)$/);
    if (m) {
      flushPara();
      if (!list) list = [];
      list.push(m[1]);
    } else {
      flushList();
      buf.push(line);
    }
  }
  flushPara();
  flushList();
  return out;
}

function renderInline(text: string) {
  // **bold** 切片
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return (
        <strong key={i} className="text-text font-semibold">
          {p.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{p}</span>;
  });
}
