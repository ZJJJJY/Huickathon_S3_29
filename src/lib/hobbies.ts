import { promises as fs } from "node:fs";
import path from "node:path";
import type { HobbiesJSON, HobbyMeta, Report } from "./types";

const DATA_DIR = path.join(process.cwd(), "src", "data");
const HOBBIES_PATH = path.join(DATA_DIR, "hobbies.json");

// Read hobbies.json fresh from disk every call. Avoids Next.js's compile-time
// JSON import cache which has been stuck on stale data in dev.
export async function loadHobbies(): Promise<HobbiesJSON> {
  const raw = await fs.readFile(HOBBIES_PATH, "utf-8");
  return JSON.parse(raw) as HobbiesJSON;
}

export async function getAllHobbies(): Promise<HobbyMeta[]> {
  const data = await loadHobbies();
  return data.flatMap((group) => group.hobbies);
}

export async function findHobbyById(id: string): Promise<HobbyMeta | undefined> {
  const all = await getAllHobbies();
  return all.find((h) => h.id === id);
}

export async function loadReport(hobbyId: string): Promise<Report | null> {
  // Defensive: only allow the slug pattern we ship in hobbies.json.
  if (!/^[a-z0-9_-]+$/.test(hobbyId)) return null;

  const reportPath = path.join(DATA_DIR, "reports", `${hobbyId}.json`);
  try {
    const raw = await fs.readFile(reportPath, "utf-8");
    return JSON.parse(raw) as Report;
  } catch {
    return null;
  }
}
