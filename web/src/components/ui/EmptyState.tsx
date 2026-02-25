import { type LucideIcon } from "lucide-react";

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; href: string };
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      <div className="p-4 rounded-2xl bg-[var(--bg-elevated)] mb-4">
        <Icon size={32} className="text-[var(--text-muted)]" />
      </div>
      <h3 className="text-lg font-medium text-[var(--text-primary)] mb-1">
        {title}
      </h3>
      <p className="text-[var(--text-secondary)] text-sm max-w-sm">
        {description}
      </p>
      {action && (
        <a
          href={action.href}
          className="mt-4 px-4 py-2 rounded-lg bg-[var(--color-primary)]
            text-white text-sm cursor-pointer hover:bg-[var(--color-primary-hover)]
            transition-colors"
        >
          {action.label}
        </a>
      )}
    </div>
  );
}
