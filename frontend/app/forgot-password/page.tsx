"use client";

import { useState } from "react";
import Link from "next/link";
import AuthShell from "@/components/AuthShell";
import PasswordInput from "@/components/PasswordInput";
import { apiFetch, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [requestError, setRequestError] = useState<string | null>(null);
  const [requestSuccess, setRequestSuccess] = useState<string | null>(null);
  const [requestLoading, setRequestLoading] = useState(false);

  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);
  const [resetLoading, setResetLoading] = useState(false);

  async function handleRequestReset(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setRequestError(null);
    setRequestSuccess(null);
    setRequestLoading(true);
    const formData = new FormData(e.currentTarget);
    try {
      await apiFetch<{ detail: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: formData.get("email") }),
      });
      setRequestSuccess("If that email is registered, a reset code has been sent.");
    } catch (err) {
      setRequestError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setRequestLoading(false);
    }
  }

  async function handleResetPassword(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setResetError(null);
    setResetSuccess(null);

    const formData = new FormData(e.currentTarget);
    const newPassword = formData.get("new_password");
    const confirmPassword = formData.get("confirm_password");
    if (newPassword !== confirmPassword) {
      setResetError("Passwords do not match");
      return;
    }

    setResetLoading(true);
    try {
      await apiFetch<{ detail: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          reset_code: formData.get("reset_code"),
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      setResetSuccess("Password reset — you can log in with your new password now.");
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setResetError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setResetLoading(false);
    }
  }

  return (
    <AuthShell
      sideHeading="MENTORA"
      sideCopy="Password reset is quick and secure. Check your inbox for the reset link."
      sideChecklist={[
        "Reset link sent to your registered email",
        "Link expires in 30 minutes for security",
        "Your progress and data are safely stored",
      ]}
    >
      <Link href="/login" className="small-muted">
        ← Back to Login
      </Link>
      <h2 style={{ marginTop: 14 }}>Forgot your password?</h2>
      <p className="subhead">Enter your registered email address and we&apos;ll send you a reset link</p>

      {requestError && <div className="form-error">{requestError}</div>}
      {requestSuccess && <div className="form-success">{requestSuccess}</div>}

      <form id="request-reset-form" name="request-reset-form" onSubmit={handleRequestReset}>
        <div className="field">
          <label htmlFor="email">Registered Email Address</label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="student@example.com"
            required
            autoComplete="email"
          />
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={requestLoading}>
          {requestLoading ? "Sending…" : "Send Reset Link →"}
        </button>
      </form>

      <div className="step-divider" />

      <div className="step-label">Step 2 — Enter Reset Code</div>

      {resetError && <div className="form-error">{resetError}</div>}
      {resetSuccess && <div className="form-success">{resetSuccess}</div>}

      <form id="reset-password-form" name="reset-password-form" onSubmit={handleResetPassword}>
        <div className="field">
          <label htmlFor="reset_code">Reset Code (from email)</label>
          <input
            type="text"
            id="reset_code"
            name="reset_code"
            placeholder="6-digit code"
            required
            pattern="[0-9]{6}"
            maxLength={6}
            inputMode="numeric"
          />
        </div>
        <div className="field">
          <label htmlFor="new_password">New Password</label>
          <PasswordInput
            id="new_password"
            name="new_password"
            placeholder="Min. 8 characters"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>
        <div className="field">
          <label htmlFor="confirm_password">Confirm New Password</label>
          <PasswordInput
            id="confirm_password"
            name="confirm_password"
            placeholder="Repeat password"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>
        <button type="submit" className="btn btn-outline btn-block" disabled={resetLoading}>
          {resetLoading ? "Resetting…" : "Reset Password →"}
        </button>
      </form>

      <div className="demo-note">
        No email service is wired up yet — the reset code is printed to the backend's
        terminal log for local testing.
      </div>
    </AuthShell>
  );
}
