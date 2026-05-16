import { NextResponse } from "next/server";
import { findHobbyById, loadReport } from "@/lib/hobbies";

// GET /api/report?hobby=<id> -> Report | 404
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const hobbyId = searchParams.get("hobby");

  if (!hobbyId) {
    return NextResponse.json(
      { error: "missing `hobby` query param" },
      { status: 400 },
    );
  }

  const meta = await findHobbyById(hobbyId);
  if (!meta) {
    return NextResponse.json(
      { error: `unknown hobby id: ${hobbyId}` },
      { status: 404 },
    );
  }

  const report = await loadReport(hobbyId);
  if (!report) {
    return NextResponse.json(
      { error: `report not generated for hobby: ${hobbyId}` },
      { status: 404 },
    );
  }

  return NextResponse.json(report, {
    headers: { "Cache-Control": "no-store" },
  });
}
