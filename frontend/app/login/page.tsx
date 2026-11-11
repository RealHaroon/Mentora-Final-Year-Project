"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthShell from "@/components/AuthShell";
import PasswordInput from "@/components/PasswordInput";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const formData = new FormData(e.currentTarget);
    const payload = {
      email: formData.get("email"),
      password: formData.get("password"),
    };
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail ?? "Login failed");
      }
      router.push("/dashboard");
      router.refresh(); // forces middleware/server components to re-read the new cookie
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      sideHeading="MENTORA"
      sideCopy="Welcome back. Continue where you left off — your AI timetable and career roadmap are ready."
      sideChecklist={[
        "Your Student Intelligence Profile (SIP) is synced",
        "Timetable auto-updated · Days remaining recalculated",
        "Notifications & session reminders waiting",
      ]}
    >
      <h2>Login to Mentora</h2>
      <p className="subhead">Enter your registered email and password</p>

      {error && <div className="form-error">{error}</div>}

      <form id="login-form" name="login-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="email">Email Address</label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="student@example.com"
            required
            autoComplete="email"
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <PasswordInput
            id="password"
            name="password"
            placeholder="Your password"
            required
            minLength={8}
            autoComplete="current-password"
          />
        </div>

        <div className="flex-between" style={{ marginBottom: 20, marginTop: -10 }}>
          <span />
          <Link href="/forgot-password" className="small-muted">
            Forgot password?
          </Link>
        </div>

        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Logging in…" : "Login →"}
        </button>
      </form>

      <div className="divider-or">or continue with</div>
      <button className="btn btn-outline btn-block" disabled>
        Continue with Google
      </button>

      <p className="auth-legal">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="link-inline">
          Register now
        </Link>
      </p>
    </AuthShell>
  );
}
