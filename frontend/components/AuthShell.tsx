import type { ReactNode } from "react";
import Link from "next/link";

type AuthShellProps = {
  sideHeading: string;
  sideCopy: string;
  sideChecklist: string[];
  children: ReactNode;
};

export default function AuthShell({ sideHeading, sideCopy, sideChecklist, children }: AuthShellProps) {
  return (
    <div className="auth-shell">
      <aside className="auth-side">
        <div className="brand">MENTORA</div>
        <div className="side-nav">
          <Link href="/">Home</Link>
          <Link href="/exam-prep">Exam Prep</Link>
          <Link href="/career">Career</Link>
        </div>
        <div className="side-content">
          <h2>{sideHeading}</h2>
          <p>{sideCopy}</p>
          <ul className="check-list">
            {sideChecklist.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <p className="footer-copy">© 2025 Mentora · A Smart Platform, From Classroom to Career</p>
      </aside>

      <main className="auth-main">
        {/* .auth-side (the only home link, above) is display:none under
            960px — found 2026-11-14: below that width there was no way
            back to "/" from login/register at all. Hidden on wider
            screens via CSS since .auth-side already covers it there. */}
        <Link href="/" className="auth-mobile-home">← MENTORA</Link>
        <div className="auth-form-wrap">{children}</div>
      </main>
    </div>
  );
}
