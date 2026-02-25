"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  CheckCircle2,
  Download,
  Clock,
  AlertCircle,
  BookOpen,
} from "lucide-react";
import { getBook } from "@/lib/api";
import type { BookDetail } from "@/lib/types";
import ChapterTable from "@/components/book/ChapterTable";

export default function BookDetailPage() {
  const params = useParams();
  const bookId = params.id as string;
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (bookId) {
      getBook(bookId)
        .then(setBook)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [bookId]);

  if (loading) {
    return (
      <div>
        <div className="skeleton h-5 w-24 mb-6" />
        <div className="skeleton h-8 w-2/3 mb-3" />
        <div className="skeleton h-5 w-1/3 mb-2" />
        <div className="skeleton h-4 w-1/4 mb-8" />
        <div className="skeleton h-3 w-full mb-6 rounded-full" />
        <div className="grid grid-cols-4 gap-4 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-96 rounded-xl" />
      </div>
    );
  }

  if (error || !book) {
    return (
      <div>
        <Link
          href="/library"
          className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 mb-6"
        >
          <ChevronLeft size={16} />
          <span className="text-sm">Library</span>
        </Link>
        <div className="bg-[rgba(239,68,68,0.1)] border border-[var(--color-error)] rounded-xl p-4">
          <p className="text-[var(--color-error)] text-sm">
            {error || "Book not found"}
          </p>
        </div>
      </div>
    );
  }

  const translated = book.chapters.filter(
    (c) => c.status === "translated" || c.status === "formatted" || c.status === "exported"
  ).length;
  const crawled = book.chapters.filter((c) => c.status === "crawled").length;
  const pending = book.chapters.filter((c) => c.status === "pending").length;
  const errors = book.chapters.filter((c) => c.status === "error").length;
  const progress =
    book.chapters.length > 0
      ? (translated / book.chapters.length) * 100
      : 0;

  const stats = [
    {
      label: "Translated",
      value: translated,
      icon: CheckCircle2,
      color: "var(--color-success)",
    },
    {
      label: "Crawled",
      value: crawled,
      icon: Download,
      color: "var(--color-warning)",
    },
    {
      label: "Pending",
      value: pending,
      icon: Clock,
      color: "var(--color-info)",
    },
    {
      label: "Error",
      value: errors,
      icon: AlertCircle,
      color: "var(--color-error)",
    },
  ];

  return (
    <div>
      {/* Back link */}
      <Link
        href="/library"
        className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 mb-6"
      >
        <ChevronLeft size={16} />
        <span className="text-sm">Library</span>
      </Link>

      {/* Book header */}
      <h1 className="font-[var(--font-fira-code)] text-2xl font-bold text-[var(--text-primary)] mb-1">
        {book.title}
      </h1>
      <p className="text-[var(--color-primary)] text-lg mb-1">{book.title_vi}</p>
      <p className="text-[var(--text-secondary)] text-sm mb-6">
        {book.author_vi || book.author}
      </p>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[var(--text-secondary)] text-sm">
            Translation Progress
          </span>
          <span className="text-[var(--text-primary)] text-sm font-[var(--font-fira-code)] font-medium">
            {translated}/{book.chapters.length} ({Math.round(progress)}%)
          </span>
        </div>
        <div className="h-2 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 mb-6">
        <Link
          href={`/books/${book.id}/glossary`}
          className="inline-flex items-center gap-2 border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-4 py-2 text-sm transition-colors"
        >
          <BookOpen size={14} aria-hidden="true" />
          Edit Glossary
        </Link>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon size={14} style={{ color: stat.color }} />
                <span className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
                  {stat.label}
                </span>
              </div>
              <span
                className="text-2xl font-bold font-[var(--font-fira-code)]"
                style={{ color: stat.color }}
              >
                {stat.value}
              </span>
            </div>
          );
        })}
      </div>

      {/* Chapter table */}
      <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)] mb-4">
        Chapters
      </h2>
      <ChapterTable bookId={book.id} chapters={book.chapters} />
    </div>
  );
}
