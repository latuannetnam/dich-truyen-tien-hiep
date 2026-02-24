"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, XCircle, Loader2 } from "lucide-react";
import { getPipelineJob, cancelPipelineJob } from "@/lib/api";
import { usePipelineWebSocket } from "@/hooks/useWebSocket";
import type { PipelineJob } from "@/lib/types";
import ProgressPanel from "@/components/pipeline/ProgressPanel";
import WorkerCards from "@/components/pipeline/WorkerCards";
import EventLog from "@/components/pipeline/EventLog";

export default function PipelineMonitorPage() {
  const params = useParams();
  const jobId = params.jobId as string;

  const [job, setJob] = useState<PipelineJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const { events, connected, latestProgress } = usePipelineWebSocket(jobId);

  // Fetch job info on mount
  useEffect(() => {
    getPipelineJob(jobId)
      .then(setJob)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [jobId]);

  // Update job progress from WebSocket events
  useEffect(() => {
    if (latestProgress && job) {
      setJob((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          progress: {
            total_chapters: (latestProgress.total_chapters as number) ?? prev.progress.total_chapters,
            crawled: (latestProgress.crawled as number) ?? prev.progress.crawled,
            translated: (latestProgress.translated as number) ?? prev.progress.translated,
            errors: (latestProgress.errors as number) ?? prev.progress.errors,
            worker_status: (latestProgress.worker_status as Record<string, string>) ?? prev.progress.worker_status,
            glossary_count: (latestProgress.glossary_count as number) ?? prev.progress.glossary_count,
          },
        };
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestProgress]);

  // Update job status from terminal events
  useEffect(() => {
    const lastEvent = events.at(-1);
    if (!lastEvent) return;

    if (lastEvent.type === "job_completed") {
      setJob((prev) => prev ? { ...prev, status: "completed" } : prev);
    } else if (lastEvent.type === "job_failed") {
      setJob((prev) => prev ? { ...prev, status: "failed", error: String(lastEvent.data.error || "") } : prev);
    } else if (lastEvent.type === "job_cancelled") {
      setJob((prev) => prev ? { ...prev, status: "cancelled" } : prev);
    }
  }, [events]);

  const handleCancel = async () => {
    if (!showCancelConfirm) {
      setShowCancelConfirm(true);
      return;
    }
    setCancelling(true);
    try {
      const updated = await cancelPipelineJob(jobId);
      setJob(updated);
    } catch {
      // Ignore cancel errors
    } finally {
      setCancelling(false);
      setShowCancelConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-48 rounded-lg" />
        <div className="skeleton h-32 rounded-xl" />
        <div className="grid grid-cols-3 gap-4">
          <div className="skeleton h-24 rounded-xl" />
          <div className="skeleton h-24 rounded-xl" />
          <div className="skeleton h-24 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="bg-[var(--bg-surface)] border border-[var(--color-error)]/30 rounded-xl p-8 text-center">
        <XCircle size={36} className="text-[var(--color-error)] mx-auto mb-3" />
        <p className="text-[var(--color-error)] font-medium mb-2">Failed to load job</p>
        <p className="text-[var(--text-muted)] text-sm">{error || "Job not found"}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 mt-4 text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] text-sm font-medium transition-colors duration-150"
        >
          <ChevronLeft size={16} />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const isActive = job.status === "running" || job.status === "pending";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm font-medium transition-colors duration-150 cursor-pointer"
        >
          <ChevronLeft size={16} />
          Dashboard
        </Link>

        {isActive && (
          <div className="flex items-center gap-3">
            {showCancelConfirm && (
              <span className="text-[var(--text-muted)] text-sm">Are you sure?</span>
            )}
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="
                inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                bg-[var(--color-error)]/10 text-[var(--color-error)]
                border border-[var(--color-error)]/30
                hover:bg-[var(--color-error)]/20
                transition-colors duration-150 cursor-pointer
                disabled:opacity-50
              "
            >
              {cancelling ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <XCircle size={14} />
              )}
              {showCancelConfirm ? "Confirm Cancel" : "Cancel Job"}
            </button>
          </div>
        )}
      </div>

      {/* Connection Status */}
      {isActive && (
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-[var(--color-success)]" : "bg-[var(--color-error)]"}`} />
          {connected ? "Live" : "Reconnecting..."}
        </div>
      )}

      {/* Progress */}
      <ProgressPanel
        status={job.status}
        progress={job.progress}
        startedAt={job.started_at}
      />

      {/* Workers */}
      <WorkerCards workerStatus={job.progress.worker_status} />

      {/* Event Log */}
      <EventLog events={events} />
    </div>
  );
}
