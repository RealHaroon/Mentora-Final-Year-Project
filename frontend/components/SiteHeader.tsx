"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type SiteHeaderProps = {
  variant: "public" | "app";
};

type DropdownKey = "career" | "dashboard";

export default function SiteHeader({ variant }: SiteHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<DropdownKey | null>(null);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/");
    router.refresh();
  }

  const isHome = pathname === "/";
  const isExamPrep = pathname.startsWith("/exam-prep");
  const isCareer = pathname.startsWith("/career");
  const isLearningPortal = pathname.startsWith("/learning-portal");
  const isDashboard = pathname.startsWith("/dashboard");

  // Close the mobile menu / any open dropdown whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
    setOpenDropdown(null);
  }, [pathname]);

  // Click-toggle dropdowns close when you click anywhere else on the page.
  useEffect(() => {
    if (!openDropdown) return;
    function handleClickOutside(e: MouseEvent) {
      if (!(e.target as HTMLElement).closest(".nav-dropdown")) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [openDropdown]);

  function toggleDropdown(key: DropdownKey) {
    setOpenDropdown((current) => (current === key ? null : key));
  }

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

          {/* Was a dropdown listing all 9 exam_goal names as separate
              links, every one pointing at this exact same href with no
              differentiation — found 2026-11-14 while fixing exam_goal
              itself to actually mean something. The real exam-goal picker
              now lives in Settings (account state, not a page section);
              this is just the page link, like Learning Portal below. */}
          <Link href="/exam-prep" className={isExamPrep ? "active" : undefined}>
            Exam Prep
          </Link>

          <div className={`nav-dropdown${isCareer ? " active" : ""}${openDropdown === "career" ? " open" : ""}`}>
            <button type="button" aria-expanded={openDropdown === "career"} onClick={() => toggleDropdown("career")}>
              Career ▾
            </button>
            <div className="nav-dropdown-panel" onClick={() => setOpenDropdown(null)}>
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
            <div className={`nav-dropdown active${openDropdown === "dashboard" ? " open" : ""}`}>
              <button type="button" aria-expanded={openDropdown === "dashboard"} onClick={() => toggleDropdown("dashboard")}>
                Dashboard ▾
              </button>
              <div className="nav-dropdown-panel" onClick={() => setOpenDropdown(null)}>
                <Link href="/dashboard#profile" className="current">
                  Student Profile (SIP)
                </Link>
                <Link href="/dashboard#weekly-snapshot">Exam History</Link>
                <Link href="/dashboard#score-trend">Performance Charts</Link>
                <Link href="/dashboard#notifications">Notifications</Link>
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
          ) : (
            <>
              {isDashboard ? (
                <a href="#settings" className="btn btn-ghost-light btn-sm">
                  Settings
                </a>
              ) : (
                <Link href="/dashboard" className="btn btn-ghost-light btn-sm">
                  My Profile
                </Link>
              )}
              <button type="button" className="btn btn-ghost-light btn-sm" onClick={handleLogout}>
                Logout
              </button>
            </>
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
