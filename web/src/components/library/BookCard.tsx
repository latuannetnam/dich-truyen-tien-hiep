"use client";

import { useRouter } from "next/navigation";
import type { BookSummary } from "@/lib/types";

interface BookCardProps {
  book: BookSummary;
}

export default function BookCard({ book }: BookCardProps) {
  const router = useRouter();
  const progress =
    book.total_chapters > 0
      ? (book.translated_chapters / book.total_chapters) * 100
      : 0;

  const statusBadge = () => {
    if (book.translated_chapters === book.total_chapters && book.total_chapters > 0) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(16,185,129,0.12)] text-[var(--color-success)]">
          Completed
        </span>
      );
    }
    if (book.translated_chapters > 0) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-primary-subtle)] text-[var(--color-primary)]">
          Translating
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[rgba(59,130,246,0.12)] text-[var(--color-info)]">
        Pending
      </span>
    );
  };

  return (
    <div
      onClick={() => router.push(`/books/${book.id}`)}
      className="
        bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6
        hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5
        transition-all duration-200 cursor-pointer
      "
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 mr-3">
          <h3 className="font-[var(--font-fira-code)] text-[var(--text-primary)] font-semibold text-base truncate">
            {book.title}
          </h3>
          <p className="text-[var(--color-primary)] text-sm mt-0.5 truncate">
            {book.title_vi}
          </p>
        </div>
        {statusBadge()}
      </div>

      {/* Author */}
      <p className="text-[var(--text-muted)] text-xs mb-4">
        {book.author_vi || book.author}
      </p>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="h-1.5 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Chapter count */}
      <div className="flex items-center justify-between">
        <span className="text-[var(--text-secondary)] text-xs">
          {book.translated_chapters}/{book.total_chapters} chapters
        </span>
        <span className="text-[var(--text-muted)] text-xs">
          {Math.round(progress)}%
        </span>
      </div>
    </div>
  );
}
