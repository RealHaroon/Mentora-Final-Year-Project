import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "mentora_session";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const backendRes = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    const err = await backendRes.json().catch(() => ({ detail: "Login failed" }));
    return NextResponse.json({ detail: err.detail }, { status: backendRes.status });
  }

  const { access_token } = await backendRes.json();
  const res = NextResponse.json({ success: true });
  res.cookies.set(COOKIE_NAME, access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // 7 days — matches the backend's JWT expiry
  });
  return res;
}
