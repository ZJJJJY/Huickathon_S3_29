// Centralized theme tokens. Keep visual constants here so components stay consistent.

export type HobbyCategory =
  | "skill_growth"
  | "physical"
  | "crafting"
  | "collecting"
  | "outdoor"
  | "social_competitive";

export const categoryLabels: Record<HobbyCategory, string> = {
  skill_growth: "技能成长型",
  physical: "体能体验型",
  crafting: "创作手工型",
  collecting: "收藏鉴赏型",
  outdoor: "自然户外型",
  social_competitive: "社交竞技型",
};

export const categoryColors: Record<HobbyCategory, string> = {
  skill_growth: "#3EE8FF",
  physical: "#FF6B35",
  crafting: "#FFD23F",
  collecting: "#A855F7",
  outdoor: "#34D399",
  social_competitive: "#FF3EA5",
};

export const theme = {
  bg: "#0A0A0F",
  bgCard: "#13131A",
  text: "#F5F5F7",
  textMuted: "#8B8B95",
  category: categoryColors,
};

// Standard glow used across cards / buttons.
export function neonGlow(color: string, strength: "soft" | "strong" = "soft") {
  const blur = strength === "strong" ? 20 : 12;
  const spread = strength === "strong" ? 2 : 0;
  return `0 0 ${blur}px ${spread}px ${color}`;
}
