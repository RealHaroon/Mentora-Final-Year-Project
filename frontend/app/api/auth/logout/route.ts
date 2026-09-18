import { NextRequest, NextResponse } from "next/server";

export async function POST(_req: NextRequest) {
  const res = NextResponse.json({ success: true });
  res.cookies.delete("mentora_session");
  return res;
}
