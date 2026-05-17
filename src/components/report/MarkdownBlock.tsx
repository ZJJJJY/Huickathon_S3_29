"use client";

import type { MarkdownContent } from "@/lib/types";

interface Props {
  content: MarkdownContent;
}

// 极简 markdown：标题(##/###/####) + 段落 + **bold** + 行首 - 无序列表 + 1. 有序列表。
// 不引入 markdown 库，保持 bundle 小；离线生成的文本受控。
export default function MarkdownBlock({ content }: Props) {
  const blocks = parseBlocks(content.text);
  return (
    <div className="text-sm leading-relaxed text-text/90 space-y-3">
      {blocks.map((b, i) => {
        if (b.type === "heading") {
          if (b.level <= 2) {
            return (
              <h3 key={i} className="text-base font-semibold text-text mt-2">
                {renderInline(b.text)}
              </h3>
            );
          }
          if (b.level === 3) {
            return (
              <h4 key={i} className="text-sm font-semibold text-text/95 mt-1">
                {renderInline(b.text)}
              </h4>
            );
          }
          return (
            <h5 key={i} className="text-sm font-medium text-text/90">
              {renderInline(b.text)}
            </h5>
          );
        }
        if (b.type === "ul") {
          return (
            <ul key={i} className="space-y-1 pl-4 list-disc marker:text-textMuted">
              {b.items.map((it, j) => (
                <li key={j}>{renderInline(it)}</li>
              ))}
            </ul>
          );
        }
        if (b.type === "ol") {
          return (
            <ol key={i} className="space-y-1 pl-5 list-decimal marker:text-textMuted">
              {b.items.map((it, j) => (
                <li key={j}>{renderInline(it)}</li>
              ))}
            </ol>
          );
        }
        return <p key={i}>{renderInline(b.text)}</p>;
      })}
    </div>
  );
}

type Block =
  | { type: "p"; text: string }
  | { type: "heading"; level: number; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] };

function parseBlocks(src: string): Block[] {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const out: Block[] = [];
  let buf: string[] = [];
  let ul: string[] | null = null;
  let ol: string[] | null = null;

  const flushPara = () => {
    if (buf.length) {
      out.push({ type: "p", text: buf.join(" ").trim() });
      buf = [];
    }
  };
  const flushUl = () => {
    if (ul && ul.length) out.push({ type: "ul", items: ul });
    ul = null;
  };
  const flushOl = () => {
    if (ol && ol.length) out.push({ type: "ol", items: ol });
    ol = null;
  };
  const flushAll = () => {
    flushPara();
    flushUl();
    flushOl();
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushAll();
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flushAll();
      out.push({ type: "heading", level: h[1].length, text: h[2].trim() });
      continue;
    }
    const u = line.match(/^[-*]\s+(.*)$/);
    if (u) {
      flushPara();
      flushOl();
      if (!ul) ul = [];
      ul.push(u[1]);
      continue;
    }
    const o = line.match(/^\d+\.\s+(.*)$/);
    if (o) {
      flushPara();
      flushUl();
      if (!ol) ol = [];
      ol.push(o[1]);
      continue;
    }
    flushUl();
    flushOl();
    buf.push(line);
  }
  flushAll();
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
