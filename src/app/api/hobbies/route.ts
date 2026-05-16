import { NextResponse } from "next/server";
import { loadHobbies } from "@/lib/hobbies";

// GET /api/hobbies -> HobbiesJSON
// Read fresh from disk each request so dev edits show up without restart.
export const dynamic = "force-dynamic";

export async function GET() {
  const data = await loadHobbies();
  return NextResponse.json(data, {
    headers: { "Cache-Control": "no-store" },
  });
}
