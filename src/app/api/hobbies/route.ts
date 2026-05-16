import { NextResponse } from "next/server";
import { hobbiesData } from "@/lib/hobbies";

// GET /api/hobbies -> HobbiesJSON
// Returns the full category + hobby manifest used by the pick page.
export async function GET() {
  return NextResponse.json(hobbiesData, {
    headers: { "Cache-Control": "public, max-age=3600" },
  });
}
