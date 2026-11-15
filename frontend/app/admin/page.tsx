import type { Metadata } from "next";
import { cookies } from "next/headers";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import TopicVideoManager from "@/components/TopicVideoManager";
import { apiFetchServer } from "@/lib/api";
import type { TopicVideoEntry } from "@/lib/types";

export const metadata: Metadata = {
  title: "Admin",
};

// Was buried inside Dashboard Settings as one of several toggled panels
// (password/profile/notifications) — moved to its own page 2026-11-15 so
// it reads as what it actually is: the one place controlling what Exam
// Prep's "Suggested Video" shows, for every student, per topic.
export const dynamic = "force-dynamic";

export default async function AdminPage() {
  const token = (await cookies()).get("mentora_session")?.value;
  let initialTopics: TopicVideoEntry[] | null = null;
  try {
    const data = await apiFetchServer<{ topics: TopicVideoEntry[] }>("/exam/topic-videos", token);
    initialTopics = data.topics;
  } catch {
    initialTopics = null; // TopicVideoManager retries client-side
  }

  return (
    <>
      <SiteHeader variant="app" />

      <section className="page-heading">
        <div className="container">
          <div>
            <h1>Admin</h1>
            <p>Manage the real videos Exam Prep suggests for each topic</p>
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 32 }}>
        <div className="container">
          <TopicVideoManager initialTopics={initialTopics} />
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
