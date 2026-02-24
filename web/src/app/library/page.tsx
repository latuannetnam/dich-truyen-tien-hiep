"use client";

import { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";
import { getBooks } from "@/lib/api";
import type { BookSummary } from "@/lib/types";
import BookCard from "@/components/library/BookCard";
import BookCardSkeleton from "@/components/library/BookCardSkeleton";

export default function LibraryPage() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBooks()
      .then(setBooks)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)] mb-6">
        Library
      </h1>

      {/* Error state */}
      {error && (
        <div className="bg-[rgba(239,68,68,0.1)] border border-[var(--color-error)] rounded-xl p-4 mb-6">
          <p className="text-[var(--color-error)] text-sm">
            Failed to load books: {error}
          </p>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <BookCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Loaded state */}
      {!loading && !error && books.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {books.map((book) => (
            <BookCard key={book.id} book={book} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && books.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <BookOpen
            size={48}
            className="text-[var(--text-muted)] mb-4"
          />
          <h2 className="font-[var(--font-fira-code)] text-xl font-semibold text-[var(--text-secondary)] mb-2">
            No books yet
          </h2>
          <p className="text-[var(--text-muted)] text-sm max-w-md">
            Run{" "}
            <code className="font-[var(--font-fira-code)] text-[var(--color-primary)] bg-[var(--color-primary-subtle)] px-1.5 py-0.5 rounded">
              dich-truyen pipeline --url &quot;...&quot;
            </code>{" "}
            to start translating your first book.
          </p>
        </div>
      )}
    </div>
  );
}
