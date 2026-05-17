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
  text: string;
}

export interface BudgetTier {
  name: string;
  price_range: string;
  items: string[];
  note: string;
}
export interface BudgetTiersContent {
  type: "budget_tiers";
  tiers: BudgetTier[];
}

export interface TimelineEntry {
  label: string;
  title: string;
  detail: string;
}
export interface TimelineContent {
  type: "timeline";
  entries: TimelineEntry[];
}

export interface ChecklistItem {
  title: string;
  detail: string;
}
export interface ChecklistContent {
  type: "checklist";
  items: ChecklistItem[];
}

export interface Card {
  title: string;
  description: string;
  meta: string;
  url: string | null;
}
export interface CardsContent {
  type: "cards";
  cards: Card[];
}

export interface QAItem {
  q: string;
  a: string;
}
export interface QAContent {
  type: "qa";
  items: QAItem[];
}

export type SectionContent =
  | MarkdownContent
  | BudgetTiersContent
  | TimelineContent
  | ChecklistContent
  | CardsContent
  | QAContent;

export type ContentType = SectionContent["type"];

export interface ReportSection {
  id: string;
  title: string;
  content: SectionContent;
  citations: string[]; // Post id 列表
  video_refs: string[]; // VideoRef id 列表
}

export interface VideoRef {
  id: string;
  url: string;
  title: string;
  author: string;
  likes: number;
  cover: string | null;
  publish_time: string | null;
}

export interface Report {
  hobby_id: string;
  hobby_name: string;
  category: HobbyCategory;
  neon_color: string;
  sections: ReportSection[];
  evidence: Record<string, Evidence>;
  videos: Record<string, VideoRef>;
}

// ---------- profile ----------
export type Profile = Record<string, string | number | undefined>;
