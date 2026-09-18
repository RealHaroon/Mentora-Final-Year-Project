import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "mentora_session";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const backendRes = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    const err = await backendRes.json().catch(() => ({ detail: "Registration failed" }));
    return NextResponse.json({ detail: err.detail }, { status: backendRes.status });
  }

  // Registering also logs the student in immediately — same cookie as /auth/login.
  const { access_token } = await backendRes.json();
  const res = NextResponse.json({ success: true });
  res.cookies.set(COOKIE_NAME, access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}
