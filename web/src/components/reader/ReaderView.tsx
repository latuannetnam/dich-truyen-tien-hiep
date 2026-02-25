"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Columns2,
  AArrowDown,
  AArrowUp,
} from "lucide-react";
import type { ChapterContent, ChapterDetail } from "@/lib/types";

interface ReaderViewProps {
  bookId: string;
  bookTitle: string;
  chapter: ChapterDetail;
  translatedContent: ChapterContent;
  rawContent: ChapterContent | null;
  currentIndex: number;
  totalChapters: number;
  onNavigate: (chapterIndex: number) => void;
  prevChapter: number | null;
  nextChapter: number | null;
  translatedChapters: { index: number; title: string }[];
}

const FONT_SIZE_KEY = "dich-truyen-font-size";
const DEFAULT_FONT_SIZE = 18;
const MIN_FONT_SIZE = 14;
const MAX_FONT_SIZE = 28;
const LAST_READ_KEY_PREFIX = "dich-truyen-last-read-";

export default function ReaderView({
  bookId,
  bookTitle,
  chapter,
  translatedContent,
  rawContent,
  currentIndex,
  totalChapters,
  onNavigate,
  prevChapter,
  nextChapter,
  translatedChapters,
}: ReaderViewProps) {
  const [sideBySide, setSideBySide] = useState(false);
  const [fontSize, setFontSize] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_FONT_SIZE;
    const saved = localStorage.getItem(FONT_SIZE_KEY);
    if (saved) {
      const parsed = parseInt(saved, 10);
      if (parsed >= MIN_FONT_SIZE && parsed <= MAX_FONT_SIZE) {
        return parsed;
      }
    }
    return DEFAULT_FONT_SIZE;
  });

  const leftPaneRef = useRef<HTMLDivElement>(null);
  const rightPaneRef = useRef<HTMLDivElement>(null);
  const isSyncingScroll = useRef(false);

  // Save reading progress
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(
        `${LAST_READ_KEY_PREFIX}${bookId}`,
        String(currentIndex)
      );
    }
  }, [bookId, currentIndex]);

  const changeFontSize = useCallback(
    (delta: number) => {
      setFontSize((prev) => {
        const next = Math.min(MAX_FONT_SIZE, Math.max(MIN_FONT_SIZE, prev + delta));
        localStorage.setItem(FONT_SIZE_KEY, String(next));
        return next;
      });
    },
    []
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft" && prevChapter !== null) {
        onNavigate(prevChapter);
      } else if (e.key === "ArrowRight" && nextChapter !== null) {
        onNavigate(nextChapter);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [prevChapter, nextChapter, onNavigate]);

  // Synced scrolling for side-by-side mode
  const handleScroll = useCallback((source: "left" | "right") => {
    if (isSyncingScroll.current) return;
    isSyncingScroll.current = true;

    const sourceEl = source === "left" ? leftPaneRef.current : rightPaneRef.current;
    const targetEl = source === "left" ? rightPaneRef.current : leftPaneRef.current;

    if (sourceEl && targetEl) {
      const scrollPercent =
        sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight || 1);
      targetEl.scrollTop =
        scrollPercent * (targetEl.scrollHeight - targetEl.clientHeight);
    }

    requestAnimationFrame(() => {
      isSyncingScroll.current = false;
    });
  }, []);

  const renderContent = (text: string) => {
    return text.split("\n").map((line, i) => (
      <p key={i} className={`mb-4 ${line.trim() === "" ? "h-4" : ""}`}>
        {line}
      </p>
    ));
  };

  // Split content into paragraphs for aligned mode
  const splitParagraphs = (text: string): string[] => {
    return text
      .split(/\n\n+/)
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
  };

  const chineseParagraphs = rawContent ? splitParagraphs(rawContent.content) : [];
  const vietnameseParagraphs = splitParagraphs(translatedContent.content);
  const maxParagraphs = Math.max(chineseParagraphs.length, vietnameseParagraphs.length);

  return (
    <div className="min-h-screen">
      {/* Sticky toolbar */}
      <div className="sticky top-0 bg-[var(--bg-primary)] z-10 py-3 border-b border-[var(--border-default)] mb-8">
        <div className="flex items-center justify-between max-w-6xl mx-auto px-4">
          {/* Left: back link */}
          <a
            href={`/books/${bookId}`}
            className="flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150"
          >
            <ChevronLeft size={16} />
            <span className="text-sm truncate max-w-[200px]">{bookTitle}</span>
          </a>

          {/* Center: chapter dropdown */}
          <select
            value={currentIndex}
            onChange={(e) => onNavigate(parseInt(e.target.value, 10))}
            className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-3 py-1.5 text-[var(--text-secondary)] text-sm font-[var(--font-fira-code)] focus:border-[var(--color-primary)] outline-none cursor-pointer max-w-[200px]"
            aria-label="Jump to chapter"
          >
            {translatedChapters.map((ch) => (
              <option key={ch.index} value={ch.index}>
                Ch. {ch.index} — {ch.title}
              </option>
            ))}
          </select>

          {/* Right: controls */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => changeFontSize(-2)}
              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors duration-150 cursor-pointer"
              title="Decrease font size"
            >
              <AArrowDown size={16} />
            </button>
            <button
              onClick={() => changeFontSize(2)}
              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors duration-150 cursor-pointer"
              title="Increase font size"
            >
              <AArrowUp size={16} />
            </button>
            <button
              onClick={() => setSideBySide(!sideBySide)}
              className={`p-1.5 rounded-md transition-colors duration-150 cursor-pointer ${
                sideBySide
                  ? "text-[var(--color-primary)] bg-[var(--color-primary-subtle)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"
              }`}
              title="Toggle side-by-side view"
            >
              <Columns2 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4">
        {/* Chapter title */}
        <h1
          className="font-[var(--font-noto-serif)] text-xl font-semibold text-[var(--text-primary)] mb-6 text-center"
          style={{ fontSize: fontSize + 4 }}
        >
          {chapter.title_vi || chapter.title_cn}
        </h1>

        {sideBySide && rawContent ? (
          /* Paragraph-aligned side-by-side mode */
          <div className="mb-12">
            {/* Column headers */}
            <div className="grid grid-cols-2 gap-6 mb-4">
              <h2 className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
                原文 (Chinese)
              </h2>
              <h2 className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
                Bản dịch (Vietnamese)
              </h2>
            </div>

            {/* Synced scroll panes */}
            <div className="grid grid-cols-2 gap-6" style={{ maxHeight: "70vh" }}>
              <div
                ref={leftPaneRef}
                onScroll={() => handleScroll("left")}
                className="bg-[var(--bg-surface)] p-8 rounded-xl overflow-y-auto"
                style={{ maxHeight: "70vh" }}
              >
                <div
                  className="font-[var(--font-noto-serif)] text-[var(--text-secondary)] leading-relaxed"
                  style={{ fontSize }}
                >
                  {/* Paragraph-aligned rows */}
                  {Array.from({ length: maxParagraphs }).map((_, i) => (
                    <div
                      key={i}
                      className="mb-6 pb-6 border-b border-[var(--border-default)]/30 last:border-0"
                    >
                      <p className="whitespace-pre-wrap">
                        {chineseParagraphs[i] || ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div
                ref={rightPaneRef}
                onScroll={() => handleScroll("right")}
                className="bg-[var(--bg-elevated)] p-8 rounded-xl overflow-y-auto"
                style={{ maxHeight: "70vh" }}
              >
                <div
                  className="font-[var(--font-noto-serif)] text-[var(--text-primary)] leading-relaxed"
                  style={{ fontSize }}
                >
                  {Array.from({ length: maxParagraphs }).map((_, i) => (
                    <div
                      key={i}
                      className="mb-6 pb-6 border-b border-[var(--border-default)]/30 last:border-0"
                    >
                      <p className="whitespace-pre-wrap">
                        {vietnameseParagraphs[i] || ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Single column mode */
          <div className="max-w-3xl mx-auto mb-12">
            <div
              className="font-[var(--font-noto-serif)] text-[var(--text-primary)] leading-relaxed"
              style={{ fontSize, lineHeight: 1.8 }}
            >
              {renderContent(translatedContent.content)}
            </div>
          </div>
        )}

        {/* Bottom navigation */}
        <div className="flex justify-between items-center max-w-3xl mx-auto py-8 border-t border-[var(--border-default)]">
          {prevChapter !== null ? (
            <button
              onClick={() => onNavigate(prevChapter)}
              className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 cursor-pointer"
            >
              <ChevronLeft size={16} />
              <span className="text-sm">Previous</span>
            </button>
          ) : (
            <div />
          )}

          <span className="text-[var(--text-muted)] text-sm font-[var(--font-fira-code)]">
            {currentIndex}/{totalChapters}
          </span>

          {nextChapter !== null ? (
            <button
              onClick={() => onNavigate(nextChapter)}
              className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150 cursor-pointer"
            >
              <span className="text-sm">Next</span>
              <ChevronRight size={16} />
            </button>
          ) : (
            <div />
          )}
        </div>
      </div>
    </div>
  );
}
