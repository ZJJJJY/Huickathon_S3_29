import { NextResponse } from "next/server";
import { getAllHobbies } from "@/lib/hobbies";

// GET /api/random -> { hobby_id }
// Picks one hobby uniformly at random from the full manifest.
export async function GET() {
  const all = getAllHobbies();
  if (all.length === 0) {
    return NextResponse.json(
      { error: "no hobbies available" },
      { status: 500 },
    );
  }
  const pick = all[Math.floor(Math.random() * all.length)];
  return NextResponse.json(
    { hobby_id: pick.id },
    { headers: { "Cache-Control": "no-store" } },
  );
}
