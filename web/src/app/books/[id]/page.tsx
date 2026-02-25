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
  PlayCircle,
  Package,
  Loader2,
  FileDown,
  Check,
} from "lucide-react";
import { getBook, getExportStatus, startExport, getExportDownloadUrl } from "@/lib/api";
import type { BookDetail, ExportStatus } from "@/lib/types";
import ChapterTable from "@/components/book/ChapterTable";
import { useToast } from "@/components/ui/ToastProvider";

const EXPORT_FORMATS = ["epub", "azw3", "mobi", "pdf"];

export default function BookDetailPage() {
  const params = useParams();
  const bookId = params.id as string;
  const [book, setBook] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastReadChapter, setLastReadChapter] = useState<number | null>(null);

  // Export state
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null);
  const [selectedFormat, setSelectedFormat] = useState("epub");
  const [exporting, setExporting] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (bookId) {
      getBook(bookId)
        .then(setBook)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));

      getExportStatus(bookId)
        .then(setExportStatus)
        .catch(() => {}); // silently fail — export status is optional

      // Check for last-read chapter
      const saved = localStorage.getItem(`dich-truyen-last-read-${bookId}`);
      if (saved) {
        setLastReadChapter(parseInt(saved, 10));
      }
    }
  }, [bookId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const result = await startExport(bookId, selectedFormat);
      if (result.success) {
        toast.showSuccess(`Export to ${selectedFormat.toUpperCase()} completed!`);
        // Refresh export status
        const updated = await getExportStatus(bookId);
        setExportStatus(updated);
      } else {
        toast.showError(result.error_message || "Export failed");
      }
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

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

  const existingExports = exportStatus?.formats
    ? Object.entries(exportStatus.formats)
    : [];

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
        {lastReadChapter !== null && (
          <Link
            href={`/books/${book.id}/read?chapter=${lastReadChapter}`}
            className="inline-flex items-center gap-2 bg-[var(--color-cta)] hover:bg-[var(--color-cta-hover)] text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            <PlayCircle size={14} aria-hidden="true" />
            Continue Reading (Ch. {lastReadChapter})
          </Link>
        )}
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

      {/* Export section */}
      <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6 mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Package size={18} className="text-[var(--color-primary)]" />
          <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)]">
            Export
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-3 mb-4">
          {/* Format selector */}
          <div className="flex gap-2">
            {EXPORT_FORMATS.map((fmt) => (
              <button
                key={fmt}
                onClick={() => setSelectedFormat(fmt)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider
                  transition-all duration-150 cursor-pointer
                  ${
                    selectedFormat === fmt
                      ? "bg-[var(--color-primary)] text-white"
                      : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-hover)]"
                  }`}
              >
                {fmt}
              </button>
            ))}
          </div>

          {/* Export button */}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="inline-flex items-center gap-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)]
              text-white rounded-lg px-4 py-1.5 text-sm font-medium transition-colors cursor-pointer
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Package size={14} />
                Export {selectedFormat.toUpperCase()}
              </>
            )}
          </button>
        </div>

        {/* Existing exports */}
        {existingExports.length > 0 && (
          <div>
            <p className="text-[var(--text-muted)] text-xs uppercase tracking-wider mb-2">
              Available Downloads
            </p>
            <div className="flex flex-wrap gap-2">
              {existingExports.map(([fmt, path]) => {
                const filename = path.split(/[\\/]/).pop() || `export.${fmt}`;
                return (
                  <a
                    key={fmt}
                    href={getExportDownloadUrl(bookId, filename)}
                    className="inline-flex items-center gap-2 bg-[var(--bg-elevated)] hover:bg-[var(--border-hover)]
                      text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-lg px-3 py-2
                      text-sm transition-colors"
                    download
                  >
                    <FileDown size={14} />
                    <span className="font-[var(--font-fira-code)] text-xs uppercase">{fmt}</span>
                    <Check size={12} className="text-[var(--color-success)]" />
                  </a>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Chapter table */}
      <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)] mb-4">
        Chapters
      </h2>
      <ChapterTable bookId={book.id} chapters={book.chapters} />
    </div>
  );
}
