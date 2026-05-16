import { NextResponse } from "next/server";
import { findHobbyById, loadReport } from "@/lib/hobbies";

// GET /api/report?hobby=<id> -> Report | 404
// Reads the pre-generated report JSON for a single hobby.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const hobbyId = searchParams.get("hobby");

  if (!hobbyId) {
    return NextResponse.json(
      { error: "missing `hobby` query param" },
      { status: 400 },
    );
  }

  if (!findHobbyById(hobbyId)) {
    return NextResponse.json(
      { error: `unknown hobby id: ${hobbyId}` },
      { status: 404 },
    );
  }

  const report = await loadReport(hobbyId);
  if (!report) {
    // Hobby is in the manifest but its pre-generated JSON is not on disk yet
    // (offline pipeline lands in T7). Per architecture_minimal §4.2 we 404
    // here; the report page handles the empty state.
    return NextResponse.json(
      { error: `report not generated for hobby: ${hobbyId}` },
      { status: 404 },
    );
  }

  return NextResponse.json(report, {
    headers: { "Cache-Control": "public, max-age=86400, immutable" },
  });
}
