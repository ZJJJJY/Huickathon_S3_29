import { NextResponse } from "next/server";
import { getAllHobbies } from "@/lib/hobbies";

// GET /api/random -> { hobby_id }
export const dynamic = "force-dynamic";

export async function GET() {
  const all = await getAllHobbies();
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
