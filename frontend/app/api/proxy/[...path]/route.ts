import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const COOKIE_NAME = "mentora_session";

async function forward(req: NextRequest, path: string[]) {
  const token = cookies().get(COOKIE_NAME)?.value;
  const url = `${API_URL}/${path.join("/")}${req.nextUrl.search}`;

  const init: RequestInit = {
    method: req.method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    const contentType = req.headers.get("content-type") ?? "";
    if (contentType.includes("multipart/form-data")) {
      // Re-encoding via FormData lets fetch set a fresh, correct boundary.
      init.body = await req.formData();
    } else {
      init.body = await req.text();
      if (contentType) {
        init.headers = { ...init.headers, "Content-Type": contentType };
      }
    }
  }

  const res = await fetch(url, init);
  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }
  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params.path);
}
export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params.path);
}
export async function PATCH(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params.path);
}
export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return forward(req, params.path);
}
