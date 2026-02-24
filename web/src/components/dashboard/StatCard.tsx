import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color?: string;
}

export default function StatCard({
  label,
  value,
  icon: Icon,
  color = "var(--text-primary)",
}: StatCardProps) {
  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} style={{ color }} />
        <span className="text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)]">
          {label}
        </span>
      </div>
      <span
        className="text-3xl font-bold font-[var(--font-fira-code)]"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  );
}
