"use client";

import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar";
import ErrorBoundary from "@/components/ui/ErrorBoundary";

export default function LayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isReaderPage = pathname.includes("/read");

  if (isReaderPage) {
    return (
      <main className="min-h-screen">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
    );
  }

  return (
    <>
      <Sidebar />
      <main className="ml-60 min-h-screen p-8">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
    </>
  );
}
