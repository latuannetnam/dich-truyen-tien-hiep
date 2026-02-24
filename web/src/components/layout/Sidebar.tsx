"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, BookOpen, PlusCircle, Activity, Settings } from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/library", label: "Library", icon: BookOpen },
  { href: "/new", label: "New Translation", icon: PlusCircle },
  { href: "/pipeline", label: "Pipeline", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-[var(--bg-surface)] border-r border-[var(--border-default)] flex flex-col z-20">
      {/* Logo area */}
      <div className="h-16 flex items-center px-6 border-b border-[var(--border-default)]">
        <h1 className="font-[var(--font-fira-code)] text-lg font-bold text-[var(--text-primary)] tracking-tight">
          Dịch Truyện
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                    transition-colors duration-150 cursor-pointer
                    ${
                      isActive
                        ? "bg-[var(--color-primary-subtle)] text-[var(--color-primary)] border-l-3 border-[var(--color-primary)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]"
                    }
                  `}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-[var(--border-default)]">
        <p className="text-xs text-[var(--text-muted)]">v0.1.0</p>
      </div>
    </aside>
  );
}
