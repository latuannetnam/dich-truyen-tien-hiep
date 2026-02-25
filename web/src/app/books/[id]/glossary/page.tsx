"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, BookOpen, Loader2 } from "lucide-react";
import { getBook, getGlossary } from "@/lib/api";
import type { BookDetail, GlossaryResponseType } from "@/lib/types";
import GlossaryEditor from "@/components/glossary/GlossaryEditor";

export default function GlossaryPage() {
  const params = useParams();
  const bookId = params.id as string;
  const [book, setBook] = useState<BookDetail | null>(null);
  const [glossary, setGlossary] = useState<GlossaryResponseType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [bookData, glossaryData] = await Promise.all([
        getBook(bookId),
        getGlossary(bookId),
      ]);
      setBook(bookData);
      setGlossary(glossaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [bookId]);

  useEffect(() => {
    if (bookId) loadData();
  }, [bookId, loadData]);

  const handleRefresh = useCallback(async () => {
    try {
      const data = await getGlossary(bookId);
      setGlossary(data);
    } catch (err) {
      console.error("Failed to refresh glossary:", err);
    }
  }, [bookId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2
          size={32}
          className="animate-spin text-[var(--color-primary)]"
        />
      </div>
    );
  }

  if (error || !book || !glossary) {
    return (
      <div>
        <Link
          href={`/books/${bookId}`}
          className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 mb-6"
        >
          <ChevronLeft size={16} />
          <span className="text-sm">Back to Book</span>
        </Link>
        <div className="bg-[rgba(239,68,68,0.1)] border border-[var(--color-error)] rounded-xl p-4">
          <p className="text-[var(--color-error)] text-sm">
            {error || "Not found"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Back link */}
      <Link
        href={`/books/${bookId}`}
        className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 mb-6"
      >
        <ChevronLeft size={16} />
        <span className="text-sm">Back to Book Detail</span>
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BookOpen
            size={28}
            className="text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="font-[var(--font-fira-code)] text-2xl font-bold text-[var(--text-primary)]">
              Glossary
            </h1>
            <p className="text-[var(--text-secondary)] text-sm">
              {book.title} — {glossary.total} terms
            </p>
          </div>
        </div>
      </div>

      <GlossaryEditor
        bookId={bookId}
        data={glossary}
        onRefresh={handleRefresh}
      />
    </div>
  );
}
