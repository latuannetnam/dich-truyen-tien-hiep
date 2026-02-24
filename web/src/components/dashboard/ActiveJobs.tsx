"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Activity, ChevronRight } from "lucide-react";
import { getPipelineJobs } from "@/lib/api";
import type { PipelineJob } from "@/lib/types";

export default function ActiveJobs() {
  const [jobs, setJobs] = useState<PipelineJob[]>([]);

  const fetchJobs = useCallback(() => {
    getPipelineJobs()
      .then((allJobs) => {
        const active = allJobs.filter(
          (j) => j.status === "running" || j.status === "pending"
        );
        setJobs(active);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchJobs();

    // Auto-refresh every 5 seconds while there are active jobs
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  // Hide section entirely when no active jobs
  if (jobs.length === 0) return null;

  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-[var(--color-primary)]" />
        <h2 className="font-[var(--font-fira-code)] text-lg font-semibold text-[var(--text-primary)]">
          Active Jobs
        </h2>
      </div>

      <div className="space-y-3">
        {jobs.map((job) => {
          const total = job.progress.total_chapters || 1;
          const translated = job.progress.translated || 0;
          const pct = total > 0 ? Math.round((translated / total) * 100) : 0;

          return (
            <Link
              key={job.id}
              href={`/pipeline/${job.id}`}
              className="
                block bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5
                cursor-pointer hover:border-[var(--border-hover)] transition-all duration-200
              "
            >
              <div className="flex items-center gap-4">
                {/* Status dot */}
                <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse shrink-0" />

                <div className="flex-1 min-w-0">
                  {/* URL/title */}
                  <p className="text-[var(--text-primary)] text-sm font-medium truncate">
                    {job.url || job.book_dir || "Unknown"}
                  </p>

                  {/* Progress text */}
                  <p className="text-[var(--text-muted)] text-xs mt-1">
                    {translated}/{total} chapters ({pct}%)
                  </p>

                  {/* Mini progress bar */}
                  <div className="h-2 rounded-full bg-[var(--bg-elevated)] mt-2 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--color-primary)] transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>

                <ChevronRight
                  size={16}
                  className="text-[var(--text-muted)] shrink-0"
                />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
