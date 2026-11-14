"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import PasswordInput from "@/components/PasswordInput";
import type { NotificationPrefs } from "@/lib/types";

type Panel = null | "profile" | "password" | "notifications";

const DEFAULT_PREFS: NotificationPrefs = {
  weak_topic_alerts: true,
  content_updates: true,
  session_reminders: true,
  career_match_updates: true,
};

type DashboardSettingsProps = {
  initialFirstName: string;
  initialLastName: string;
  initialUniversity: string;
  initialExamGoal: string;
};

export default function DashboardSettings({
  initialFirstName,
  initialLastName,
  initialUniversity,
  initialExamGoal,
}: DashboardSettingsProps) {
  const router = useRouter();
  const [panel, setPanel] = useState<Panel>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);

  function togglePanel(next: Panel) {
    setError(null);
    setSuccess(null);
    setPanel((current) => (current === next ? null : next));
    if (next === "notifications" && prefs === null) {
      apiFetch<NotificationPrefs>("/users/me/notification-prefs")
        .then(setPrefs)
        .catch(() => setPrefs(DEFAULT_PREFS));
    }
  }

  async function handleNotificationPrefsSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!prefs) return;
    setError(null);
    setLoading(true);
    try {
      const saved = await apiFetch<NotificationPrefs>("/users/me/notification-prefs", {
        method: "PATCH",
        body: JSON.stringify(prefs),
      });
      setPrefs(saved);
      setSuccess("Notification preferences saved");
      setPanel(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your preferences");
    } finally {
      setLoading(false);
    }
  }

  async function handleProfileSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const formData = new FormData(e.currentTarget);
    try {
      await apiFetch("/users/me", {
        method: "PATCH",
        body: JSON.stringify({
          first_name: formData.get("first_name"),
          last_name: formData.get("last_name"),
          university: formData.get("university"),
          exam_goal: formData.get("exam_goal"),
        }),
      });
      setSuccess("Profile updated");
      setPanel(null);
      router.refresh(); // re-fetches the server-rendered header with the new values
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update your profile");
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const formData = new FormData(e.currentTarget);
    const newPassword = formData.get("new_password");
    const confirmPassword = formData.get("confirm_password");
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: formData.get("current_password"),
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      setSuccess("Password changed");
      setPanel(null);
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't change your password");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteAccount() {
    if (!window.confirm("Delete your account permanently? This cannot be undone.")) return;
    setLoading(true);
    try {
      await apiFetch("/users/me", { method: "DELETE" });
      await fetch("/api/auth/logout", { method: "POST" });
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete your account");
      setLoading(false);
    }
  }

  return (
    <div id="settings" style={{ marginTop: 36 }}>
      <h4 style={{ margin: "0 0 14px" }}>Settings</h4>

      {error && <div className="form-error">{error}</div>}
      {success && <div className="form-success">{success}</div>}

      <div className="settings-grid">
        <button className="btn btn-outline btn-sm" onClick={() => togglePanel("profile")}>
          👤 Account
        </button>
        <button className="btn btn-outline btn-sm" onClick={() => togglePanel("notifications")}>
          🔔 Notification Prefs
        </button>
        <Link href="/exam-prep" className="btn btn-outline btn-sm">
          📊 Study Preferences
        </Link>
        <button className="btn btn-outline btn-sm" onClick={() => togglePanel("password")}>
          🔒 Change Password
        </button>
        <button
          className="btn btn-sm"
          style={{ background: "var(--red-100)", color: "var(--red-600)" }}
          onClick={handleDeleteAccount}
          disabled={loading}
        >
          🗑 Delete Account
        </button>
      </div>

      {panel === "profile" && (
        <form onSubmit={handleProfileSubmit} className="panel mt-24">
          <div className="field-row">
            <div className="field">
              <label htmlFor="settings_first_name">First Name</label>
              <input id="settings_first_name" name="first_name" defaultValue={initialFirstName} required />
            </div>
            <div className="field">
              <label htmlFor="settings_last_name">Last Name</label>
              <input id="settings_last_name" name="last_name" defaultValue={initialLastName} required />
            </div>
          </div>
          <div className="field">
            <label htmlFor="settings_university">University / Institution</label>
            <input id="settings_university" name="university" defaultValue={initialUniversity} required />
          </div>
          <div className="field">
            <label htmlFor="settings_exam_goal">I am preparing for</label>
            {/* Matches /register's exact same options — was previously set
                once at registration with no way to ever change it again. */}
            <select id="settings_exam_goal" name="exam_goal" defaultValue={initialExamGoal} required>
              <optgroup label="University Entry Tests">
                <option value="sindh_university">University Entry Test (Sindh Univ.)</option>
                <option value="mehran_university">Mehran University</option>
                <option value="lums">LUMS</option>
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
            <p className="small-muted" style={{ margin: "6px 0 0" }}>
              Changes which subjects Exam Prep offers — MDCAT, for example,
              doesn't test Mathematics.
            </p>
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Saving…" : "Save changes"}
          </button>
        </form>
      )}

      {panel === "notifications" && (
        <form onSubmit={handleNotificationPrefsSubmit} className="panel mt-24">
          {prefs === null ? (
            <p className="small-muted">Loading…</p>
          ) : (
            <>
              <label className="mcq-option">
                <input
                  type="checkbox"
                  checked={prefs.weak_topic_alerts}
                  onChange={(e) => setPrefs({ ...prefs, weak_topic_alerts: e.target.checked })}
                />{" "}
                Weak-topic alerts (e.g. "flagged at risk")
              </label>
              <label className="mcq-option">
                <input
                  type="checkbox"
                  checked={prefs.content_updates}
                  onChange={(e) => setPrefs({ ...prefs, content_updates: e.target.checked })}
                />{" "}
                Content updates (new playlists, materials)
              </label>
              <label className="mcq-option">
                <input
                  type="checkbox"
                  checked={prefs.session_reminders}
                  onChange={(e) => setPrefs({ ...prefs, session_reminders: e.target.checked })}
                />{" "}
                Session reminders
              </label>
              <label className="mcq-option">
                <input
                  type="checkbox"
                  checked={prefs.career_match_updates}
                  onChange={(e) => setPrefs({ ...prefs, career_match_updates: e.target.checked })}
                />{" "}
                Career match updates
              </label>
              <button type="submit" className="btn btn-primary mt-24" disabled={loading}>
                {loading ? "Saving…" : "Save preferences"}
              </button>
            </>
          )}
        </form>
      )}

      {panel === "password" && (
        <form onSubmit={handlePasswordSubmit} className="panel mt-24">
          <div className="field">
            <label htmlFor="current_password">Current Password</label>
            <PasswordInput id="current_password" name="current_password" required />
          </div>
          <div className="field">
            <label htmlFor="new_password">New Password</label>
            <PasswordInput id="new_password" name="new_password" minLength={8} required />
          </div>
          <div className="field">
            <label htmlFor="confirm_password">Confirm New Password</label>
            <PasswordInput id="confirm_password" name="confirm_password" minLength={8} required />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Saving…" : "Change password"}
          </button>
        </form>
      )}
    </div>
  );
}
