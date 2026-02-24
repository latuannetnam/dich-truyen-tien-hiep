"use client";

import { Cpu } from "lucide-react";

interface WorkerStatus {
  [key: string]: string;
}

interface WorkerCardsProps {
  workerStatus?: WorkerStatus;
}

export default function WorkerCards({ workerStatus }: WorkerCardsProps) {
  if (!workerStatus || Object.keys(workerStatus).length === 0) {
    return null;
  }

  return (
    <div>
      <h3 className="font-[var(--font-fira-code)] text-sm font-semibold text-[var(--text-primary)] mb-3 uppercase tracking-wider">
        Workers
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(workerStatus).map(([workerId, status]) => {
          const isActive = status !== "idle" && status !== "waiting";
          return (
            <div
              key={workerId}
              className={`
                bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-4
                transition-all duration-200
                ${isActive ? "border-l-3 border-l-[var(--color-primary)]" : "opacity-50"}
              `}
            >
              <div className="flex items-center gap-2 mb-2">
                <Cpu size={14} className={isActive ? "text-[var(--color-primary)]" : "text-[var(--text-muted)]"} />
                <span className="text-[var(--text-primary)] text-sm font-medium font-[var(--font-fira-code)]">
                  Worker {workerId}
                </span>
              </div>
              <p className={`text-sm truncate ${isActive ? "text-[var(--text-secondary)]" : "text-[var(--text-muted)]"}`}>
                {status || "idle"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
