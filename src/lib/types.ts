import type { HobbyCategory } from "./theme";

// Schema for data/hobbies.json
export interface HobbyMeta {
  id: string;
  name: string;
  emoji: string;
  one_liner: string;
  neon_color: string;
}

export interface CategoryGroup {
  category: HobbyCategory;
  label: string;
  hobbies: HobbyMeta[];
}

export type HobbiesJSON = CategoryGroup[];

// Schema for data/reports/<hobby_id>.json
// ReportContent is intentionally `unknown` — the final report structure is
// not yet decided, so the rest of the app treats it as an opaque blob.
export type ReportContent = unknown;

export interface Report {
  hobby_id: string;
  hobby_name: string;
  category: HobbyCategory;
  neon_color: string;
  content: ReportContent;
}

// Profile (survey answers) is stored in localStorage. Schema is open for now.
export type Profile = Record<string, string | number | undefined>;
