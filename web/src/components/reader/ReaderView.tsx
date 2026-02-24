"use client";

import { useState, useEffect, useCallback } from "react";
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
}

const FONT_SIZE_KEY = "dich-truyen-font-size";
const DEFAULT_FONT_SIZE = 18;
const MIN_FONT_SIZE = 14;
const MAX_FONT_SIZE = 28;

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
}: ReaderViewProps) {
  const [sideBySide, setSideBySide] = useState(false);
  const [fontSize, setFontSize] = useState(DEFAULT_FONT_SIZE);

  // Load font size from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(FONT_SIZE_KEY);
    if (saved) {
      const parsed = parseInt(saved, 10);
      if (parsed >= MIN_FONT_SIZE && parsed <= MAX_FONT_SIZE) {
        setFontSize(parsed);
      }
    }
  }, []);

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

  const renderContent = (text: string) => {
    return text.split("\n").map((line, i) => (
      <p key={i} className={`mb-4 ${line.trim() === "" ? "h-4" : ""}`}>
        {line}
      </p>
    ));
  };

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

          {/* Center: chapter indicator */}
          <span className="text-[var(--text-secondary)] text-sm font-[var(--font-fira-code)]">
            Chapter {currentIndex}
          </span>

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
          /* Side-by-side mode */
          <div className="grid grid-cols-2 gap-6 mb-12">
            {/* Chinese original */}
            <div className="bg-[var(--bg-surface)] p-8 rounded-xl">
              <h2 className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] mb-4">
                原文 (Chinese)
              </h2>
              <div
                className="font-[var(--font-noto-serif)] text-[var(--text-secondary)] leading-relaxed"
                style={{ fontSize }}
              >
                {renderContent(rawContent.content)}
              </div>
            </div>

            {/* Vietnamese translation */}
            <div className="bg-[var(--bg-elevated)] p-8 rounded-xl">
              <h2 className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] mb-4">
                Bản dịch (Vietnamese)
              </h2>
              <div
                className="font-[var(--font-noto-serif)] text-[var(--text-primary)] leading-relaxed"
                style={{ fontSize }}
              >
                {renderContent(translatedContent.content)}
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
