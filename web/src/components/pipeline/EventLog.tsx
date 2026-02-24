"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Download, AlertCircle } from "lucide-react";
import type { PipelineEventMessage } from "@/lib/types";

interface EventLogProps {
  events: PipelineEventMessage[];
}

function getEventIcon(type: string) {
  if (type.includes("translated") || type.includes("completed")) {
    return <CheckCircle2 size={14} className="text-[var(--color-success)] shrink-0" />;
  }
  if (type.includes("crawled") || type.includes("started")) {
    return <Download size={14} className="text-[var(--color-warning)] shrink-0" />;
  }
  if (type.includes("error") || type.includes("failed")) {
    return <AlertCircle size={14} className="text-[var(--color-error)] shrink-0" />;
  }
  return <Download size={14} className="text-[var(--text-muted)] shrink-0" />;
}

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function getEventLabel(event: PipelineEventMessage): string {
  const data = event.data;
  switch (event.type) {
    case "chapter_translated":
      return `Ch.${data.chapter_index} translated`;
    case "chapter_crawled":
      return `Ch.${data.chapter_index} crawled`;
    case "chapter_error":
      return `Ch.${data.chapter_index} error: ${data.error || "unknown"}`;
    case "job_started":
      return "Job started";
    case "job_completed":
      return "Job completed";
    case "job_failed":
      return `Job failed: ${data.error || "unknown"}`;
    case "job_cancelled":
      return "Job cancelled";
    default:
      return event.type;
  }
}

export default function EventLog({ events }: EventLogProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Filter out progress events (those are shown in ProgressPanel)
  const displayEvents = events.filter((e) => e.type !== "progress");

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [displayEvents.length, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // Auto-scroll if user is near bottom (within 50px)
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
  };

  if (displayEvents.length === 0) {
    return (
      <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-8 text-center">
        <p className="text-[var(--text-muted)] text-sm">Waiting for events...</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="font-[var(--font-fira-code)] text-sm font-semibold text-[var(--text-primary)] mb-3 uppercase tracking-wider">
        Event Log
      </h3>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border-default)] max-h-[40vh] overflow-y-auto"
        aria-live="polite"
      >
        {displayEvents.map((event, i) => (
          <div
            key={`${event.timestamp}-${i}`}
            className="px-4 py-2 border-b border-[var(--border-default)] last:border-0 text-sm flex items-center gap-3"
          >
            {getEventIcon(event.type)}
            <span className="text-[var(--text-secondary)] flex-1 truncate">
              {getEventLabel(event)}
            </span>
            <span className="text-[var(--text-muted)] text-xs font-mono shrink-0">
              {formatTime(event.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
