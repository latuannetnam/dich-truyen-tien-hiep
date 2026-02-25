"use client";

import { useEffect, useState } from "react";
import { Search, X, Palette, Check, ChevronRight } from "lucide-react";
import { getStyles, getStyle } from "@/lib/api";
import type { StyleSummary, StyleDetail } from "@/lib/types";

const toneColors: Record<string, string> = {
  formal: "var(--color-info)",
  casual: "var(--color-success)",
  poetic: "var(--color-cta)",
  literary: "var(--color-warning)",
};

function getToneColor(tone: string): string {
  return toneColors[tone.toLowerCase()] || "var(--color-primary)";
}

export default function StylesPage() {
  const [styles, setStyles] = useState<StyleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedStyle, setSelectedStyle] = useState<StyleDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    getStyles()
      .then(setStyles)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = styles.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase()) ||
      s.tone.toLowerCase().includes(search.toLowerCase())
  );

  const openDetail = async (name: string) => {
    setDetailLoading(true);
    setShowDetail(true);
    try {
      const detail = await getStyle(name);
      setSelectedStyle(detail);
    } catch (err) {
      setSelectedStyle(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setShowDetail(false);
    setTimeout(() => setSelectedStyle(null), 300);
  };

  return (
    <div className="relative">
      <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)] mb-2">
        Style Manager
      </h1>
      <p className="text-[var(--text-secondary)] text-sm mb-6">
        Browse and inspect translation style templates.
      </p>

      {/* Search bar */}
      <div className="relative mb-6">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
        />
        <input
          type="text"
          placeholder="Search styles by name, description, or tone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-[var(--bg-surface)] border border-[var(--border-default)]
            rounded-lg text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)]
            focus:outline-none focus:border-[var(--color-primary)] transition-colors"
        />
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-[rgba(239,68,68,0.1)] border border-[var(--color-error)] rounded-xl p-4 mb-6">
          <p className="text-[var(--color-error)] text-sm">
            Failed to load styles: {error}
          </p>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-36 rounded-xl" />
          ))}
        </div>
      )}

      {/* Style cards */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((style) => (
            <button
              key={style.name}
              onClick={() => openDetail(style.name)}
              className="text-left bg-[var(--bg-surface)] border border-[var(--border-default)]
                rounded-xl p-5 cursor-pointer hover:border-[var(--border-hover)]
                hover:shadow-[var(--shadow-md)] transition-all duration-200 group"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-[var(--font-fira-code)] text-sm font-semibold text-[var(--text-primary)] group-hover:text-[var(--color-primary)] transition-colors">
                  {style.name}
                </h3>
                <ChevronRight
                  size={14}
                  className="text-[var(--text-muted)] group-hover:text-[var(--color-primary)] transition-colors mt-0.5"
                />
              </div>
              <p className="text-[var(--text-secondary)] text-xs leading-relaxed mb-3 line-clamp-2">
                {style.description || "No description available."}
              </p>
              <div className="flex items-center gap-2">
                {style.tone && (
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: `color-mix(in srgb, ${getToneColor(style.tone)} 15%, transparent)`,
                      color: getToneColor(style.tone),
                    }}
                  >
                    {style.tone}
                  </span>
                )}
                {style.is_builtin && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-primary-subtle)] text-[var(--color-primary)] font-medium">
                    built-in
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="p-4 rounded-2xl bg-[var(--bg-elevated)] mb-4">
            <Palette size={32} className="text-[var(--text-muted)]" />
          </div>
          <h3 className="text-lg font-medium text-[var(--text-primary)] mb-1">
            {search ? "No matching styles" : "No styles found"}
          </h3>
          <p className="text-[var(--text-secondary)] text-sm max-w-sm">
            {search
              ? "Try adjusting your search query."
              : "No translation style templates are available."}
          </p>
        </div>
      )}

      {/* Detail slide-in panel */}
      {showDetail && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/40 z-30"
            onClick={closeDetail}
            style={{ animation: "fadeIn 200ms ease-out both" }}
          />

          {/* Panel */}
          <div
            className="fixed right-0 top-0 h-screen w-full max-w-lg bg-[var(--bg-surface)]
              border-l border-[var(--border-default)] z-40 overflow-y-auto"
            style={{ animation: "slideInRight 300ms ease-out both" }}
          >
            {/* Header */}
            <div className="sticky top-0 bg-[var(--bg-surface)] border-b border-[var(--border-default)] px-6 py-4 flex items-center justify-between z-10">
              <h2 className="font-[var(--font-fira-code)] text-lg font-bold text-[var(--text-primary)]">
                {detailLoading ? "Loading..." : selectedStyle?.name}
              </h2>
              <button
                onClick={closeDetail}
                className="p-1.5 rounded-lg hover:bg-[var(--bg-elevated)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {detailLoading ? (
              <div className="p-6 space-y-4">
                <div className="skeleton h-4 w-3/4" />
                <div className="skeleton h-4 w-1/2" />
                <div className="skeleton h-24 w-full rounded-lg" />
                <div className="skeleton h-48 w-full rounded-lg" />
              </div>
            ) : (
              selectedStyle && (
                <div className="p-6 space-y-6">
                  {/* Description */}
                  <div>
                    <p className="text-[var(--text-secondary)] text-sm leading-relaxed">
                      {selectedStyle.description}
                    </p>
                    {selectedStyle.tone && (
                      <span
                        className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          backgroundColor: `color-mix(in srgb, ${getToneColor(selectedStyle.tone)} 15%, transparent)`,
                          color: getToneColor(selectedStyle.tone),
                        }}
                      >
                        Tone: {selectedStyle.tone}
                      </span>
                    )}
                  </div>

                  {/* Guidelines */}
                  {selectedStyle.guidelines.length > 0 && (
                    <div>
                      <h3 className="font-[var(--font-fira-code)] text-sm font-semibold text-[var(--text-primary)] mb-3">
                        Guidelines
                      </h3>
                      <ul className="space-y-2">
                        {selectedStyle.guidelines.map((g, i) => (
                          <li
                            key={i}
                            className="flex items-start gap-2 text-sm text-[var(--text-secondary)]"
                          >
                            <Check
                              size={14}
                              className="text-[var(--color-success)] mt-0.5 shrink-0"
                            />
                            <span>{g}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Vocabulary */}
                  {Object.keys(selectedStyle.vocabulary).length > 0 && (
                    <div>
                      <h3 className="font-[var(--font-fira-code)] text-sm font-semibold text-[var(--text-primary)] mb-3">
                        Vocabulary
                      </h3>
                      <div className="bg-[var(--bg-primary)] rounded-lg border border-[var(--border-default)] overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-[var(--border-default)]">
                              <th className="text-left px-4 py-2 text-[var(--text-muted)] font-medium text-xs uppercase tracking-wider">
                                Chinese
                              </th>
                              <th className="text-left px-4 py-2 text-[var(--text-muted)] font-medium text-xs uppercase tracking-wider">
                                Vietnamese
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(selectedStyle.vocabulary).map(
                              ([cn, vi]) => (
                                <tr
                                  key={cn}
                                  className="border-b border-[var(--border-default)] last:border-b-0"
                                >
                                  <td className="px-4 py-2 text-[var(--text-primary)] font-[var(--font-fira-code)]">
                                    {cn}
                                  </td>
                                  <td className="px-4 py-2 text-[var(--color-primary)]">
                                    {vi}
                                  </td>
                                </tr>
                              )
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Examples */}
                  {selectedStyle.examples.length > 0 && (
                    <div>
                      <h3 className="font-[var(--font-fira-code)] text-sm font-semibold text-[var(--text-primary)] mb-3">
                        Translation Examples
                      </h3>
                      <div className="space-y-3">
                        {selectedStyle.examples.map((ex, i) => (
                          <div
                            key={i}
                            className="bg-[var(--bg-primary)] rounded-lg border border-[var(--border-default)] p-4"
                          >
                            <p className="text-[var(--text-muted)] text-xs uppercase tracking-wider mb-1">
                              Chinese
                            </p>
                            <p className="text-[var(--text-primary)] text-sm mb-3 font-[var(--font-fira-code)]">
                              {ex.chinese}
                            </p>
                            <p className="text-[var(--text-muted)] text-xs uppercase tracking-wider mb-1">
                              Vietnamese
                            </p>
                            <p className="text-[var(--color-primary)] text-sm">
                              {ex.vietnamese}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        </>
      )}
    </div>
  );
}
