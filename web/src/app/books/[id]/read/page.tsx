"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { getBook, getChapterTranslated, getChapterRaw } from "@/lib/api";
import type { BookDetail, ChapterContent, ChapterDetail } from "@/lib/types";
import ReaderView from "@/components/reader/ReaderView";

function ReaderContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const bookId = params.id as string;
  const chapterParam = searchParams.get("chapter");

  const [book, setBook] = useState<BookDetail | null>(null);
  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [translatedContent, setTranslatedContent] =
    useState<ChapterContent | null>(null);
  const [rawContent, setRawContent] = useState<ChapterContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadChapterContent = useCallback(
    async (bookIdArg: string, chapterIndex: number) => {
      try {
        const translated = await getChapterTranslated(bookIdArg, chapterIndex);
        setTranslatedContent(translated);

        // Try to load raw content too (for side-by-side)
        try {
          const raw = await getChapterRaw(bookIdArg, chapterIndex);
          setRawContent(raw);
        } catch {
          setRawContent(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load chapter");
      }
    },
    []
  );

  // Load book data
  useEffect(() => {
    if (bookId) {
      getBook(bookId)
        .then((bookData) => {
          setBook(bookData);

          // Determine chapter to show
          let chapterIndex = chapterParam ? parseInt(chapterParam, 10) : null;

          if (!chapterIndex) {
            // Default to first translated chapter
            const firstTranslated = bookData.chapters.find(
              (c) =>
                c.has_translated &&
                (c.status === "translated" ||
                  c.status === "formatted" ||
                  c.status === "exported")
            );
            chapterIndex = firstTranslated?.index || 1;
          }

          const ch = bookData.chapters.find((c) => c.index === chapterIndex);
          setChapter(ch || null);

          // Load content
          return loadChapterContent(bookId, chapterIndex);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [bookId, chapterParam, loadChapterContent]);

  const navigateToChapter = useCallback(
    (chapterIndex: number) => {
      setLoading(true);
      setError(null);
      router.push(`/books/${bookId}/read?chapter=${chapterIndex}`, {
        scroll: true,
      });
    },
    [bookId, router]
  );

  // Determine prev/next translated chapters
  const getAdjacentChapter = (
    direction: "prev" | "next"
  ): number | null => {
    if (!book || !chapter) return null;
    const currentIdx = book.chapters.findIndex(
      (c) => c.index === chapter.index
    );
    if (currentIdx === -1) return null;

    if (direction === "prev") {
      for (let i = currentIdx - 1; i >= 0; i--) {
        if (book.chapters[i].has_translated) {
          return book.chapters[i].index;
        }
      }
    } else {
      for (let i = currentIdx + 1; i < book.chapters.length; i++) {
        if (book.chapters[i].has_translated) {
          return book.chapters[i].index;
        }
      }
    }
    return null;
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4">
        <div className="skeleton h-5 w-32 mb-8 mx-auto" />
        <div className="skeleton h-8 w-2/3 mb-8 mx-auto" />
        <div className="space-y-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="skeleton h-4"
              style={{ width: `${[95, 88, 72, 91, 85, 78, 93, 80, 87, 75, 90, 82][i]}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (error || !book || !translatedContent || !chapter) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4">
        <a
          href={`/books/${bookId}`}
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm mb-6 inline-block"
        >
          ← Back to book
        </a>
        <div className="bg-[rgba(239,68,68,0.1)] border border-[var(--color-error)] rounded-xl p-4">
          <p className="text-[var(--color-error)] text-sm">
            {error || "Chapter not found"}
          </p>
        </div>
      </div>
    );
  }

  const translatedChaptersList = book.chapters
    .filter((c) => c.has_translated)
    .map((c) => ({ index: c.index, title: c.title_vi || c.title_cn }));

  return (
    <ReaderView
      bookId={bookId}
      bookTitle={book.title_vi || book.title}
      chapter={chapter}
      translatedContent={translatedContent}
      rawContent={rawContent}
      currentIndex={chapter.index}
      totalChapters={book.chapters.length}
      onNavigate={navigateToChapter}
      prevChapter={getAdjacentChapter("prev")}
      nextChapter={getAdjacentChapter("next")}
      translatedChapters={translatedChaptersList}
    />
  );
}

export default function ReaderPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-3xl mx-auto py-12 px-4">
          <div className="skeleton h-5 w-32 mb-8 mx-auto" />
          <div className="skeleton h-8 w-2/3 mb-8 mx-auto" />
          <div className="space-y-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="skeleton h-4"
                style={{ width: `${[95, 88, 72, 91, 85, 78, 93, 80, 87, 75, 90, 82][i]}%` }}
              />
            ))}
          </div>
        </div>
      }
    >
      <ReaderContent />
    </Suspense>
  );
}
