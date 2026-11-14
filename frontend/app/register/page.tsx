"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthShell from "@/components/AuthShell";
import PasswordInput from "@/components/PasswordInput";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const formData = new FormData(e.currentTarget);
    const password = formData.get("password");
    const confirmPassword = formData.get("confirm_password");
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    const payload = {
      first_name: formData.get("first_name"),
      last_name: formData.get("last_name"),
      email: formData.get("email"),
      password,
      confirm_password: confirmPassword,
      university: formData.get("university"),
      exam_goal: formData.get("exam_goal"),
    };
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail ?? "Registration failed");
      }
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      sideHeading="MENTORA"
      sideCopy="Pakistan's first AI-powered platform that takes you from exam prep to career — all in one place."
      sideChecklist={[
        "Personalized exam timetables updated daily",
        "AI career fit from your CV · 50+ career paths",
        "YouTube playlists auto-curated per topic",
        "FLAN-T5 powered MCQ tests on your weak topics",
      ]}
    >
      <h2>Create your account</h2>
      <p className="subhead">Start your journey from classroom to career</p>

      {error && <div className="form-error">{error}</div>}

      <form id="register-form" name="register-form" onSubmit={handleSubmit}>
        <div className="field-row">
          <div className="field">
            <label htmlFor="first_name">First Name</label>
            <input
              type="text"
              id="first_name"
              name="first_name"
              placeholder="e.g. Raimal"
              required
              autoComplete="given-name"
            />
          </div>
          <div className="field">
            <label htmlFor="last_name">Last Name</label>
            <input
              type="text"
              id="last_name"
              name="last_name"
              placeholder="e.g. Raja"
              required
              autoComplete="family-name"
            />
          </div>
        </div>

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
            placeholder="Min. 8 characters"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>

        <div className="field">
          <label htmlFor="confirm_password">Confirm Password</label>
          <PasswordInput
            id="confirm_password"
            name="confirm_password"
            placeholder="Repeat password"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>

        <div className="field">
          <label htmlFor="university">University / Institution</label>
          <input
            type="text"
            id="university"
            name="university"
            placeholder="University of Sindh, Laar Campus"
            required
            autoComplete="organization"
          />
        </div>

        <div className="field">
          <label htmlFor="exam_goal">I am preparing for</label>
          <select id="exam_goal" name="exam_goal" required defaultValue="">
            <option value="" disabled>
              Select an exam or career goal
            </option>
            <optgroup label="University Entry Tests">
              <option value="sindh_university">University Entry Test (Sindh Univ.)</option>
              <option value="mehran_university">Mehran University</option>
              <option value="lumhs">LUMHS (Hyderabad)</option>
              <option value="karachi_university">Karachi University</option>
              <option value="iqra_university">Iqra University</option>
              <option value="tando_jam_university">Tando Jam University</option>
            </optgroup>
            <optgroup label="Medical College Entry Tests">
              <option value="mdcat">MDCAT (Sindh)</option>
            </optgroup>
            <optgroup label="Job / Competitive Tests">
              <option value="pms_spsc_ppsc">PMS / SPSC / PPSC</option>
              <option value="issb">ISSB</option>
              <option value="army_navy_paf">Army / Navy / PAF</option>
            </optgroup>
          </select>
        </div>

        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Creating account…" : "Create Account →"}
        </button>
      </form>

      <p className="auth-legal">
        By registering, you agree to Mentora&apos;s <a href="#">Terms of Service</a> and{" "}
        <a href="#">Privacy Policy</a>
      </p>
      <p className="auth-legal">
        Already have an account?{" "}
        <Link href="/login" className="link-inline">
          Login here
        </Link>
      </p>
    </AuthShell>
  );
}
