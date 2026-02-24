"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, FileText, CheckCircle2 } from "lucide-react";
import { getBooks } from "@/lib/api";
import type { BookSummary } from "@/lib/types";
import StatCard from "@/components/dashboard/StatCard";
import BookCard from "@/components/library/BookCard";
import BookCardSkeleton from "@/components/library/BookCardSkeleton";

export default function Home() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBooks()
      .then(setBooks)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalBooks = books.length;
  const totalChapters = books.reduce((sum, b) => sum + b.total_chapters, 0);
  const totalTranslated = books.reduce(
    (sum, b) => sum + b.translated_chapters,
    0
  );
  const completionPct =
    totalChapters > 0 ? Math.round((totalTranslated / totalChapters) * 100) : 0;

  const recentBooks = [...books]
    .sort((a, b) => {
      const ta = a.updated_at ?? a.created_at ?? "";
      const tb = b.updated_at ?? b.created_at ?? "";
      return tb.localeCompare(ta);
    })
    .slice(0, 3);

  return (
    <div>
      <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)] mb-2">
        Dashboard
      </h1>
      <p className="text-[var(--text-secondary)] mb-8">Welcome to Dịch Truyện</p>

      {/* Stats */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-28 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard
            label="Total Books"
            value={totalBooks}
            icon={BookOpen}
            color="var(--text-primary)"
          />
          <StatCard
            label="Total Chapters"
            value={totalChapters}
            icon={FileText}
            color="var(--text-primary)"
          />
          <StatCard
            label="Completion"
            value={`${completionPct}%`}
            icon={CheckCircle2}
            color="var(--color-primary)"
          />
        </div>
      )}

      {/* Recent Books */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)]">
          Recent Books
        </h2>
        {books.length > 3 && (
          <Link
            href="/library"
            className="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] text-sm font-medium transition-colors duration-150"
          >
            View all →
          </Link>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <BookCardSkeleton key={i} />
          ))}
        </div>
      ) : recentBooks.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {recentBooks.map((book) => (
            <BookCard key={book.id} book={book} />
          ))}
        </div>
      ) : (
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-8 text-center mb-8">
          <BookOpen
            size={36}
            className="text-[var(--text-muted)] mx-auto mb-3"
          />
          <p className="text-[var(--text-secondary)] text-sm">
            No books yet. Start by running the pipeline CLI.
          </p>
        </div>
      )}

      {/* Quick Actions */}
      <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)] mb-4">
        Quick Actions
      </h2>
      <div className="flex gap-4">
        <Link
          href="/library"
          className="
            inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium
            bg-[var(--bg-surface)] border border-[var(--border-default)]
            text-[var(--text-secondary)] hover:text-[var(--text-primary)]
            hover:border-[var(--border-hover)] hover:bg-[var(--bg-elevated)]
            transition-all duration-150 cursor-pointer
          "
        >
          <BookOpen size={16} />
          Browse Library
        </Link>
        <Link
          href="/settings"
          className="
            inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium
            bg-[var(--bg-surface)] border border-[var(--border-default)]
            text-[var(--text-secondary)] hover:text-[var(--text-primary)]
            hover:border-[var(--border-hover)] hover:bg-[var(--bg-elevated)]
            transition-all duration-150 cursor-pointer
          "
        >
          Open Settings
        </Link>
      </div>
    </div>
  );
}
