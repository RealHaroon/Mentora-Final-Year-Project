import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Exam Prep",
};

export default function ExamPrepLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
