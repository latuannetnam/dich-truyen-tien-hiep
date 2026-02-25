"use client";

import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Download,
  Clock,
  AlertCircle,
  BookOpen,
} from "lucide-react";
import type { ChapterDetail } from "@/lib/types";
import EmptyState from "@/components/ui/EmptyState";

interface ChapterTableProps {
  bookId: string;
  chapters: ChapterDetail[];
}

const statusConfig: Record<
  string,
  { icon: typeof CheckCircle2; color: string; label: string }
> = {
  translated: {
    icon: CheckCircle2,
    color: "var(--color-success)",
    label: "Translated",
  },
  crawled: {
    icon: Download,
    color: "var(--color-warning)",
    label: "Crawled",
  },
  pending: {
    icon: Clock,
    color: "var(--color-info)",
    label: "Pending",
  },
  error: {
    icon: AlertCircle,
    color: "var(--color-error)",
    label: "Error",
  },
  formatted: {
    icon: CheckCircle2,
    color: "var(--color-success)",
    label: "Formatted",
  },
  exported: {
    icon: CheckCircle2,
    color: "var(--color-success)",
    label: "Exported",
  },
};

export default function ChapterTable({ bookId, chapters }: ChapterTableProps) {
  const router = useRouter();

  if (chapters.length === 0) {
    return (
      <EmptyState
        icon={BookOpen}
        title="No chapters yet"
        description="Start a pipeline to crawl and translate chapters for this book."
        action={{ label: "Start Translation", href: "/new" }}
      />
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl overflow-hidden">
      {/* Table header */}
      <div className="grid grid-cols-[60px_1fr_120px_100px] px-6 py-3 border-b border-[var(--border-default)]">
        <span className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
          #
        </span>
        <span className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
          Title
        </span>
        <span className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
          Status
        </span>
        <span className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] text-right">
          Actions
        </span>
      </div>

      {/* Table body */}
      <div className="max-h-[60vh] overflow-y-auto">
        {chapters.map((ch) => {
          const config = statusConfig[ch.status] || statusConfig.pending;
          const Icon = config.icon;
          const isClickable = ch.has_translated;

          return (
            <div
              key={ch.index}
              onClick={() => {
                if (isClickable) {
                  router.push(`/books/${bookId}/read?chapter=${ch.index}`);
                }
              }}
              className={`
                grid grid-cols-[60px_1fr_120px_100px] px-6 py-3 
                border-b border-[var(--border-default)] last:border-b-0
                transition-colors duration-150
                ${isClickable ? "cursor-pointer hover:bg-[var(--bg-elevated)]" : ""}
              `}
            >
              <span className="text-[var(--text-muted)] text-sm font-[var(--font-fira-code)]">
                {ch.index}
              </span>
              <span className="text-[var(--text-primary)] text-sm truncate">
                {ch.title_vi || ch.title_cn}
              </span>
              <span className="flex items-center gap-2">
                <Icon size={14} style={{ color: config.color }} />
                <span
                  className="text-xs"
                  style={{ color: config.color }}
                >
                  {config.label}
                </span>
              </span>
              <span className="text-right">
                {isClickable && (
                  <span className="text-[var(--color-primary)] text-xs font-medium">
                    Read →
                  </span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
