"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Activity, ChevronRight, PlusCircle, Clock, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { getPipelineJobs } from "@/lib/api";
import type { PipelineJob } from "@/lib/types";

function statusBadge(status: PipelineJob["status"]) {
  const map: Record<string, { icon: typeof Activity; color: string; label: string }> = {
    running: { icon: Activity, color: "var(--color-primary)", label: "Running" },
    pending: { icon: Clock, color: "var(--color-warning)", label: "Pending" },
    completed: { icon: CheckCircle2, color: "var(--color-success)", label: "Completed" },
    failed: { icon: XCircle, color: "var(--color-error)", label: "Failed" },
    cancelled: { icon: AlertTriangle, color: "var(--text-muted)", label: "Cancelled" },
  };
  const s = map[status] || map.cancelled;
  const Icon = s.icon;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: s.color }}>
      <Icon size={12} />
      {s.label}
    </span>
  );
}

function timeAgo(ts: number): string {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function PipelineListPage() {
  const [jobs, setJobs] = useState<PipelineJob[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = useCallback(() => {
    getPipelineJobs()
      .then(setJobs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const activeJobs = jobs.filter((j) => j.status === "running" || j.status === "pending");
  const pastJobs = jobs.filter((j) => j.status !== "running" && j.status !== "pending");

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)] mb-1">
            Pipelines
          </h1>
          <p className="text-[var(--text-secondary)] text-sm">
            Monitor and manage translation jobs
          </p>
        </div>
        <Link
          href="/new"
          className="
            inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium
            bg-[var(--color-primary-subtle)] border border-[var(--color-primary)]/30
            text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20
            transition-all duration-150 cursor-pointer
          "
        >
          <PlusCircle size={16} />
          New Translation
        </Link>
      </div>

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-xl" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-12 text-center">
          <Activity size={36} className="text-[var(--text-muted)] mx-auto mb-3" />
          <p className="text-[var(--text-secondary)] text-sm mb-4">
            No pipeline jobs yet
          </p>
          <Link
            href="/new"
            className="
              inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium
              bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)]
              transition-colors duration-150 cursor-pointer
            "
          >
            <PlusCircle size={16} />
            Start Translation
          </Link>
        </div>
      ) : (
        <>
          {/* Active Jobs */}
          {activeJobs.length > 0 && (
            <div className="mb-8">
              <h2 className="flex items-center gap-2 font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)] mb-4">
                <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse" />
                Active ({activeJobs.length})
              </h2>
              <div className="space-y-3">
                {activeJobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            </div>
          )}

          {/* Past Jobs */}
          {pastJobs.length > 0 && (
            <div>
              <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)] mb-4">
                History ({pastJobs.length})
              </h2>
              <div className="space-y-3">
                {pastJobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function JobCard({ job }: { job: PipelineJob }) {
  const total = job.progress.total_chapters || 1;
  const translated = job.progress.translated || 0;
  const pct = total > 0 ? Math.round((translated / total) * 100) : 0;
  const isActive = job.status === "running" || job.status === "pending";

  return (
    <Link
      href={`/pipeline/${job.id}`}
      className="
        block bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5
        cursor-pointer hover:border-[var(--border-hover)] transition-all duration-200
      "
    >
      <div className="flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            {statusBadge(job.status)}
            <span className="text-[var(--text-muted)] text-xs">
              {timeAgo(job.created_at)}
            </span>
          </div>

          <p className="text-[var(--text-primary)] text-sm font-medium truncate">
            {job.url || job.book_dir || "Unknown source"}
          </p>

          {isActive && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
                <span>{translated}/{total} chapters</span>
                <span>{pct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-[var(--bg-elevated)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-primary)] transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )}

          {!isActive && (
            <p className="text-[var(--text-muted)] text-xs mt-1">
              {translated}/{total} chapters translated
              {job.error && <span className="text-[var(--color-error)]"> · {job.error}</span>}
            </p>
          )}
        </div>

        <ChevronRight size={16} className="text-[var(--text-muted)] shrink-0" />
      </div>
    </Link>
  );
}
