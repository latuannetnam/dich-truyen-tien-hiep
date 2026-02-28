"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  RotateCcw,
  Settings2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react";
import { getResumableBooks, startPipeline, getStyles } from "@/lib/api";
import type { ResumableBook, StyleSummary } from "@/lib/types";

export default function ResumableSection() {
  const [books, setBooks] = useState<ResumableBook[]>([]);
  const router = useRouter();

  const fetchBooks = useCallback(() => {
    getResumableBooks()
      .then(setBooks)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchBooks();
    const interval = setInterval(fetchBooks, 30000);
    return () => clearInterval(interval);
  }, [fetchBooks]);

  if (books.length === 0) return null;

  return (
    <div className="mb-8">
      <h2 className="flex items-center gap-2 font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)] mb-4">
        <RotateCcw size={18} className="text-[var(--color-warning)]" />
        Resumable ({books.length})
      </h2>
      <div className="space-y-3">
        {books.map((book) => (
          <ResumableCard key={book.book_id} book={book} router={router} onResume={fetchBooks} />
        ))}
      </div>
    </div>
  );
}

function ResumableCard({
  book,
  router,
  onResume,
}: {
  book: ResumableBook;
  router: ReturnType<typeof useRouter>;
  onResume: () => void;
}) {
  const [showOptions, setShowOptions] = useState(false);
  const [resuming, setResuming] = useState(false);

  const pct =
    book.total_chapters > 0
      ? Math.round((book.translated / book.total_chapters) * 100)
      : 0;

  const handleResume = async (overrides?: Record<string, unknown>) => {
    setResuming(true);
    try {
      const request = {
        book_dir: book.book_dir,
        ...(book.last_settings || {}),
        ...overrides,
      };
      const job = await startPipeline(request);
      router.push(`/pipeline/${job.id}`);
    } catch {
      setResuming(false);
    }
  };

  const displayTitle = book.title_vi || book.title || book.book_id;

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5 transition-all duration-200 hover:border-[var(--border-hover)]">
      <div className="flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-[var(--text-primary)] text-sm font-medium truncate mb-1.5">
            {displayTitle}
          </p>

          {/* Progress bar */}
          <div className="mb-2">
            <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
              <span>
                {book.translated}/{book.total_chapters} chapters
              </span>
              <span>{pct}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-[var(--bg-elevated)] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[#14B8A6] transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Status badges */}
          <div className="flex items-center gap-3 text-xs">
            {book.pending > 0 && (
              <span className="inline-flex items-center gap-1 text-[var(--text-muted)]">
                <Clock size={11} />
                {book.pending} pending
              </span>
            )}
            {book.crawled > 0 && (
              <span className="inline-flex items-center gap-1 text-[var(--color-warning)]">
                <AlertCircle size={11} />
                {book.crawled} crawled
              </span>
            )}
            {book.translated > 0 && (
              <span className="inline-flex items-center gap-1 text-[var(--color-success)]">
                <CheckCircle2 size={11} />
                {book.translated} translated
              </span>
            )}
            {book.errors > 0 && (
              <span className="inline-flex items-center gap-1 text-[var(--color-error)]">
                <XCircle size={11} />
                {book.errors} errors
              </span>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowOptions(!showOptions)}
            className="
              inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
              bg-[var(--bg-elevated)] border border-[var(--border-default)]
              text-[var(--text-secondary)] hover:text-[var(--text-primary)]
              hover:border-[var(--border-hover)] transition-all duration-150 cursor-pointer
            "
            title="Options"
          >
            <Settings2 size={13} />
            {showOptions ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          <button
            onClick={() => handleResume()}
            disabled={resuming}
            className="
              inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium
              bg-[var(--color-primary)] text-white
              hover:bg-[var(--color-primary-hover)] transition-all duration-150
              disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer
            "
          >
            <RotateCcw size={13} className={resuming ? "animate-spin" : ""} />
            {resuming ? "Resuming…" : "Resume"}
          </button>
        </div>
      </div>

      {/* Options panel */}
      {showOptions && (
        <OptionsPanel
          book={book}
          onResume={(overrides) => handleResume(overrides)}
          resuming={resuming}
        />
      )}
    </div>
  );
}

function OptionsPanel({
  book,
  onResume,
  resuming,
}: {
  book: ResumableBook;
  onResume: (overrides: Record<string, unknown>) => void;
  resuming: boolean;
}) {
  const settings = book.last_settings || {};
  const [style, setStyle] = useState(settings.style || "tien_hiep");
  const [workers, setWorkers] = useState(settings.workers || 3);
  const [chapters, setChapters] = useState(settings.chapters || "");
  const [translateOnly, setTranslateOnly] = useState(
    settings.translate_only || false
  );
  const [force, setForce] = useState(false);
  const [styles, setStyles] = useState<StyleSummary[]>([]);

  useEffect(() => {
    getStyles()
      .then(setStyles)
      .catch(() => {});
  }, []);

  return (
    <div className="mt-4 pt-4 border-t border-[var(--border-default)]">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Style */}
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">
            Style
          </label>
          <select
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="
              w-full px-3 py-2 rounded-lg text-sm
              bg-[var(--bg-elevated)] border border-[var(--border-default)]
              text-[var(--text-primary)]
              focus:outline-none focus:border-[var(--color-primary)]
            "
          >
            {styles.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Workers */}
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">
            Workers
          </label>
          <input
            type="number"
            min={1}
            max={10}
            value={workers}
            onChange={(e) => setWorkers(Number(e.target.value))}
            className="
              w-full px-3 py-2 rounded-lg text-sm
              bg-[var(--bg-elevated)] border border-[var(--border-default)]
              text-[var(--text-primary)]
              focus:outline-none focus:border-[var(--color-primary)]
            "
          />
        </div>

        {/* Chapters */}
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">
            Chapters
          </label>
          <input
            type="text"
            placeholder="e.g. 1-100"
            value={chapters}
            onChange={(e) => setChapters(e.target.value)}
            className="
              w-full px-3 py-2 rounded-lg text-sm
              bg-[var(--bg-elevated)] border border-[var(--border-default)]
              text-[var(--text-primary)] placeholder:text-[var(--text-muted)]
              focus:outline-none focus:border-[var(--color-primary)]
            "
          />
        </div>

        {/* Checkboxes */}
        <div className="flex flex-col justify-end gap-2">
          <label className="inline-flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer">
            <input
              type="checkbox"
              checked={translateOnly}
              onChange={(e) => setTranslateOnly(e.target.checked)}
              className="rounded accent-[var(--color-primary)]"
            />
            Translate only
          </label>
          <label className="inline-flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="rounded accent-[var(--color-primary)]"
            />
            Force re-translate
          </label>
        </div>
      </div>

      <div className="mt-3 flex justify-end">
        <button
          onClick={() =>
            onResume({
              style,
              workers,
              chapters: chapters || undefined,
              translate_only: translateOnly,
              force,
            })
          }
          disabled={resuming}
          className="
            inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium
            bg-[var(--color-primary)] text-white
            hover:bg-[var(--color-primary-hover)] transition-all duration-150
            disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer
          "
        >
          <RotateCcw size={13} className={resuming ? "animate-spin" : ""} />
          {resuming ? "Resuming…" : "Resume with options"}
        </button>
      </div>
    </div>
  );
}
