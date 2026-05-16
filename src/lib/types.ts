import type { HobbyCategory } from "./theme";

// ---------- hobbies.json ----------
export type TimeWindow = "6m" | "1y" | "2y" | "unlimited";

export interface HobbyMeta {
  id: string;
  name: string;
  emoji: string;
  one_liner: string;
  neon_color: string;
  time_window: TimeWindow;
}

export interface CategoryGroup {
  category: HobbyCategory;
  label: string;
  hobbies: HobbyMeta[];
}

export type HobbiesJSON = CategoryGroup[];

// ---------- reports/<hobby_id>.json ----------
// 与 tools/report-generator/lib/schemas.py 保持同步。

export type Platform = "xhs" | "douyin";

export interface Evidence {
  platform: Platform;
  url: string;
  title: string;
  author: string;
  likes: number;
  snippet: string;
  cover: string | null;
}

// 6 种 content 形态 (按 content_type 区分)
export interface MarkdownContent {
  type: "markdown";
  text: s