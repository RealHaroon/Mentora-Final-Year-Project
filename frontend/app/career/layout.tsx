import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Career Counseling",
};

export default function CareerLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
