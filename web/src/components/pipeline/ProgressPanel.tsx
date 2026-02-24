"use client";

import { CheckCircle2, Loader2, XCircle, Clock } from "lucide-react";
import type { PipelineProgress } from "@/lib/types";

interface ProgressPanelProps {
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: PipelineProgress;
  startedAt: number | null;
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; label: string; pulse?: boolean }> = {
    pending: { bg: "bg-[var(--color-warning)]/15", text: "text-[var(--color-warning)]", label: "Pending" },
    running: { bg: "bg-[var(--color-primary)]/15", text: "text-[var(--color-primary)]", label: "Running", pulse: true },
    completed: { bg: "bg-[var(--color-success)]/15", text: "text-[var(--color-success)]", label: "Completed" },
    failed: { bg: "bg-[var(--color-error)]/15", text: "text-[var(--color-error)]", label: "Failed" },
    cancelled: { bg: "bg-[var(--color-warning)]/15", text: "text-[var(--color-warning)]", label: "Cancelled" },
  };
  const c = config[status] ?? config.pending;

  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${c.bg} ${c.text}`}>
      {c.pulse && (
        <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
      )}
      {status === "completed" && <CheckCircle2 size={14} />}
      {status === "failed" && <XCircle size={14} />}
      {c.label}
    </span>
  );
}

function formatElapsed(startedAt: number | null): string {
  if (!startedAt) return "";
  const seconds = Math.floor((Date.now() / 1000) - startedAt);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m ago`;
}

export default function ProgressPanel({ status, progress, startedAt }: ProgressPanelProps) {
  const total = progress.total_chapters || 1;
  const translated = progress.translated || 0;
  const pct = total > 0 ? Math.round((translated / total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[var(--text-muted)] text-sm uppercase tracking-wider font-medium">Job Status</span>
          <StatusBadge status={status} />
        </div>
        {startedAt && (
          <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-sm">
            <Clock size={14} />
            <span>Started {formatElapsed(startedAt)}</span>
          </div>
        )}
      </div>

      {/* Overall Progress Bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[var(--text-secondary)] text-sm font-medium">Overall Progress</span>
          <span className="text-[var(--text-primary)] text-sm font-[var(--font-fira-code)]">
            {translated}/{total} ({pct}%)
          </span>
        </div>
        <div
          className="h-3 rounded-full bg-[var(--bg-elevated)] overflow-hidden"
          role="progressbar"
          aria-valuenow={translated}
          aria-valuemin={0}
          aria-valuemax={total}
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[#14B8A6] transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
          <p className="text-[var(--text-muted)] text-xs uppercase tracking-wider mb-1">Crawled</p>
          <p className="text-2xl font-bold font-[var(--font-fira-code)] text-[var(--color-warning)]">
            {progress.crawled}/{total}
          </p>
          <p className="text-[var(--text-muted)] text-xs mt-1">
            {total > 0 ? Math.round((progress.crawled / total) * 100) : 0}%
          </p>
        </div>
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
          <p className="text-[var(--text-muted)] text-xs uppercase tracking-wider mb-1">Translated</p>
          <p className="text-2xl font-bold font-[var(--font-fira-code)] text-[var(--color-success)]">
            {translated}/{total}
          </p>
          <p className="text-[var(--text-muted)] text-xs mt-1">{pct}%</p>
        </div>
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
          <p className="text-[var(--text-muted)] text-xs uppercase tracking-wider mb-1">Errors</p>
          <p className="text-2xl font-bold font-[var(--font-fira-code)] text-[var(--color-error)]">
            {progress.errors}
          </p>
        </div>
      </div>
    </div>
  );
}
