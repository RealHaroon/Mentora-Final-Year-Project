"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type SiteHeaderProps = {
  variant: "public" | "app";
};

export default function SiteHeader({ variant }: SiteHeaderProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const isHome = pathname === "/";
  const isExamPrep = pathname.startsWith("/exam-prep");
  const isCareer = pathname.startsWith("/career");
  const isLearningPortal = pathname.startsWith("/learning-portal");
  const isDashboard = pathname.startsWith("/dashboard");

  // Close the mobile menu whenever the route changes (e.g. after tapping a link).
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <header className="site-header">
      <div className="container">
        <Link href="/" className="brand">
          MENTORA
        </Link>
        <nav className="main-nav">
          <Link href="/" className={isHome ? "active" : undefined}>
            Home
          </Link>

          <div className={`nav-dropdown${isExamPrep ? " active" : ""}`}>
            <button type="button">Exam Prep ▾</button>
            <div className="nav-dropdown-panel">
              <div className="group-label">University Entry Tests</div>
              <Link href="/exam-prep" className={isExamPrep ? "current" : undefined}>
                Sindh University
              </Link>
              <Link href="/exam-prep">Mehran University</Link>
              <Link href="/exam-prep">LUMS</Link>
              <Link href="/exam-prep">Karachi University</Link>
              <Link href="/exam-prep">Iqra University</Link>
              <Link href="/exam-prep">Tando Jam University</Link>
              <div className="group-label">Job / Competitive Tests</div>
              <Link href="/exam-prep">PMS / SPSC / PPSC</Link>
              <Link href="/exam-prep">ISSB</Link>
              <Link href="/exam-prep">Army / Navy / PAF</Link>
            </div>
          </div>

          <div className={`nav-dropdown${isCareer ? " active" : ""}`}>
            <button type="button">Career ▾</button>
            <div className="nav-dropdown-panel">
              <Link href="/career" className={isCareer ? "current" : undefined}>
                Career Counseling
              </Link>
              <Link href="/career#mock-interview">Mock Interview</Link>
            </div>
          </div>

          <Link href="/learning-portal" className={isLearningPortal ? "active" : undefined}>
            Learning Portal
          </Link>

          {isDashboard ? (
            <div className="nav-dropdown active">
              <button type="button">Dashboard ▾</button>
              <div className="nav-dropdown-panel">
                <Link href="/dashboard" className="current">
                  Student Profile (SIP)
                </Link>
                <Link href="/dashboard">Exam History</Link>
                <Link href="/dashboard">Performance Charts</Link>
                <Link href="/dashboard">Notifications</Link>
              </div>
            </div>
          ) : (
            <Link href="/dashboard">Dashboard</Link>
          )}
        </nav>

        <button
          type="button"
          className="mobile-nav-toggle"
          aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={menuOpen}
          aria-controls="mobile-nav-panel"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "✕" : "☰"}
        </button>

        <div className="header-actions">
          {variant === "public" ? (
            <>
              <Link href="/login" className="btn btn-ghost-light btn-sm">
                Login
              </Link>
              <Link href="/register" className="btn btn-primary btn-sm">
                Sign Up →
              </Link>
            </>
          ) : isDashboard ? (
            <a href="#settings" className="btn btn-ghost-light btn-sm">
              Settings
            </a>
          ) : (
            <Link href="/dashboard" className="btn btn-ghost-light btn-sm">
              My Profile
            </Link>
          )}
        </div>
      </div>

      {menuOpen && (
        <div id="mobile-nav-panel" className="mobile-nav-panel">
          <div className="container">
            <Link href="/" className={isHome ? "active" : undefined}>
              Home
            </Link>
            <Link href="/exam-prep" className={isExamPrep ? "active" : undefined}>
              Exam Prep
            </Link>
            <Link href="/career" className={isCareer ? "active" : undefined}>
              Career
            </Link>
            <Link href="/learning-portal" className={isLearningPortal ? "active" : undefined}>
              Learning Portal
            </Link>
            <Link href="/dashboard" className={isDashboard ? "active" : undefined}>
              Dashboard
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
