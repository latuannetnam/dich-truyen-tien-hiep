"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  RotateCcw,
  Settings2,
  ChevronDown,
  ChevronUp,
  Activity,
} from "lucide-react";
import {
  getResumableBooks,
  getPipelineJobs,
  startPipeline,
  getStyles,
} from "@/lib/api";
import type { BookDetail, ResumableBook, PipelineJob, StyleSummary } from "@/lib/types";

interface ResumeBannerProps {
  bookId: string;
  bookDetail: BookDetail;
}

export default function ResumeBanner({ bookId, bookDetail }: ResumeBannerProps) {
  const router = useRouter();
  const [resumableInfo, setResumableInfo] = useState<ResumableBook | null>(null);
  const [activeJob, setActiveJob] = useState<PipelineJob | null>(null);
  const [showOptions, setShowOptions] = useState(false);
  const [resuming, setResuming] = useState(false);

  // Calculate remaining chapters
  const translated = bookDetail.chapters.filter(
    (c) => c.status === "translated" || c.status === "formatted" || c.status === "exported"
  ).length;
  const remaining = bookDetail.chapters.length - translated;

  // Fetch resumable info and check for active jobs
  useEffect(() => {
    getResumableBooks()
      .then((books) => {
        const match = books.find((b) => b.book_id === bookId);
        if (match) setResumableInfo(match);
      })
      .catch(() => {});

    getPipelineJobs()
      .then((jobs) => {
        const active = jobs.find(
          (j) =>
            (j.status === "running" || j.status === "pending") &&
            j.book_dir?.includes(bookId)
        );
        if (active) setActiveJob(active);
      })
      .catch(() => {});
  }, [bookId]);

  if (remaining <= 0) return null;

  // If there's an active job, show "View Active Job" banner instead
  if (activeJob) {
    return (
      <div className="mb-6 bg-[var(--color-primary-subtle)] border border-[var(--color-primary)]/30 rounded-xl p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <Activity size={18} className="text-[var(--color-primary)] shrink-0 animate-pulse" />
            <p className="text-sm text-[var(--text-primary)]">
              Translation in progress —{" "}
              <span className="font-medium font-[var(--font-fira-code)]">
                {remaining}
              </span>{" "}
              chapters remaining
            </p>
          </div>
          <Link
            href={`/pipeline/${activeJob.id}`}
            className="
              inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium
              bg-[var(--color-primary)] text-white
              hover:bg-[var(--color-primary-hover)] transition-all duration-150
            "
          >
            <Activity size={12} />
            View Active Job
          </Link>
        </div>
      </div>
    );
  }

  const handleResume = async (overrides?: Record<string, unknown>) => {
    setResuming(true);
    try {
      const settings = resumableInfo?.last_settings || {};
      const request = {
        book_dir: resumableInfo?.book_dir || bookId,
        ...settings,
        ...overrides,
      };
      const job = await startPipeline(request);
      router.push(`/pipeline/${job.id}`);
    } catch {
      setResuming(false);
    }
  };

  return (
    <div className="mb-6 bg-[rgba(234,179,8,0.08)] border border-[rgba(234,179,8,0.3)] rounded-xl p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <AlertTriangle
            size={18}
            className="text-[var(--color-warning)] shrink-0"
          />
          <p className="text-sm text-[var(--text-primary)]">
            Translation incomplete —{" "}
            <span className="font-medium font-[var(--font-fira-code)]">
              {remaining}
            </span>{" "}
            chapters remaining
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowOptions(!showOptions)}
            className="
              inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
              bg-[var(--bg-surface)] border border-[var(--border-default)]
              text-[var(--text-secondary)] hover:text-[var(--text-primary)]
              hover:border-[var(--border-hover)] transition-all duration-150 cursor-pointer
            "
          >
            <Settings2 size={12} />
            Options
            {showOptions ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          </button>
          <button
            onClick={() => handleResume()}
            disabled={resuming}
            className="
              inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium
              bg-[var(--color-primary)] text-white
              hover:bg-[var(--color-primary-hover)] transition-all duration-150
              disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer
            "
          >
            <RotateCcw size={12} className={resuming ? "animate-spin" : ""} />
            {resuming ? "Resuming…" : "Resume"}
          </button>
        </div>
      </div>

      {/* Expandable options form */}
      {showOptions && (
        <ResumeOptionsForm
          resumableInfo={resumableInfo}
          onResume={(overrides) => handleResume(overrides)}
          resuming={resuming}
        />
      )}
    </div>
  );
}

function ResumeOptionsForm({
  resumableInfo,
  onResume,
  resuming,
}: {
  resumableInfo: ResumableBook | null;
  onResume: (overrides: Record<string, unknown>) => void;
  resuming: boolean;
}) {
  const settings = resumableInfo?.last_settings || {};
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
    <div className="mt-4 pt-3 border-t border-[rgba(234,179,8,0.2)]">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">
            Style
          </label>
          <select
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="
              w-full px-3 py-1.5 rounded-lg text-sm
              bg-[var(--bg-surface)] border border-[var(--border-default)]
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
              w-full px-3 py-1.5 rounded-lg text-sm
              bg-[var(--bg-surface)] border border-[var(--border-default)]
              text-[var(--text-primary)]
              focus:outline-none focus:border-[var(--color-primary)]
            "
          />
        </div>
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
              w-full px-3 py-1.5 rounded-lg text-sm
              bg-[var(--bg-surface)] border border-[var(--border-default)]
              text-[var(--text-primary)] placeholder:text-[var(--text-muted)]
              focus:outline-none focus:border-[var(--color-primary)]
            "
          />
        </div>
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
            inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium
            bg-[var(--color-primary)] text-white
            hover:bg-[var(--color-primary-hover)] transition-all duration-150
            disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer
          "
        >
          <RotateCcw size={12} className={resuming ? "animate-spin" : ""} />
          {resuming ? "Resuming…" : "Resume with options"}
        </button>
      </div>
    </div>
  );
}
