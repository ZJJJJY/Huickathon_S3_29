import { promises as fs } from "node:fs";
import path from "node:path";
import hobbiesJson from "@/data/hobbies.json";
import type { HobbiesJSON, HobbyMeta, Report } from "./types";

// Type-safe access to the static seed.
export const hobbiesData = hobbiesJson as HobbiesJSON;

export function getAllHobbies(): HobbyMeta[] {
  return hobbiesData.flatMap((group) => group.hobbies);
}

export function findHobbyById(id: string): HobbyMeta | undefined {
  return getAllHobbies().find((h) => h.id === id);
}

// Reports are stored as separate JSON files so the seed can be regenerated
// independently of hobbies.json. Returns null when the report is missing.
export async function loadReport(hobbyId: string): Promise<Report | null> {
  // Defensive: only allow the slug pattern we ship in hobbies.json.
  if (!/^[a-z0-9_-]+$/.test(hobbyId)) return null;

  const reportPath = path.join(
    process.cwd(),
    "src",
    "data",
    "reports",
    `${hobbyId}.json`,
  );
  try {
    const raw = await fs.readFile(reportPath, "utf-8");
    return JSON.parse(raw) as Report;
  } catch {
    return null;
  }
}
