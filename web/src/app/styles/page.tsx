"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Search,
  X,
  Palette,
  Check,
  ChevronRight,
  Plus,
  Upload,
  Download,
  Wrench,
  Pencil,
  Trash2,
  RotateCcw,
} from "lucide-react";
import {
  getStyles,
  getStyle,
  createStyle,
  updateStyle,
  deleteStyle,
  duplicateStyle,
  importStyle,
  getStyleExportUrl,
} from "@/lib/api";
import type { StyleSummary, StyleDetail } from "@/lib/types";
import { useToast } from "@/components/ui/ToastProvider";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import ConfirmDialog from "@/components/styles/ConfirmDialog";
import StyleEditorForm from "@/components/styles/StyleEditorForm";

const toneColors: Record<string, string> = {
  formal: "var(--color-info)",
  casual: "var(--color-success)",
  poetic: "var(--color-cta)",
  literary: "var(--color-warning)",
  archaic: "var(--color-primary)",
};

function getToneColor(tone: string): string {
  return toneColors[tone.toLowerCase()] || "var(--color-primary)";
}

const badgeConfig: Record<string, { label: string; className: string }> = {
  builtin: { label: "built-in", className: "bg-blue-500/20 text-blue-300" },
  custom: { label: "custom", className: "bg-green-500/20 text-green-300" },
  shadow: { label: "customized", className: "bg-amber-500/20 text-amber-300" },
};

type PanelMode = "view" | "create" | "edit" | "shadow-edit" | null;

export default function StylesPage() {
  const [styles, setStyles] = useState<StyleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Panel state
  const [panelMode, setPanelMode] = useState<PanelMode>(null);
  const [selectedStyle, setSelectedStyle] = useState<StyleDetail | null>(null);
  const [selectedStyleType, setSelectedStyleType] = useState<string>("builtin");
  const [detailLoading, setDetailLoading] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  // Confirm dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    confirmLabel: string;
    onConfirm: () => void;
  }>({ open: false, title: "", message: "", confirmLabel: "", onConfirm: () => {} });

  // Discard changes dialog
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);

  const { showSuccess, showError } = useToast();
  const panelRef = useFocusTrap(panelMode !== null && !isClosing);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load styles
  const loadStyles = useCallback(() => {
    getStyles()
      .then(setStyles)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadStyles();
  }, [loadStyles]);

  const filtered = styles.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase()) ||
      s.tone.toLowerCase().includes(search.toLowerCase())
  );

  // --- Panel operations ---

  const closePanel = useCallback(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      setPanelMode(null);
      setSelectedStyle(null);
      setIsDirty(false);
      return;
    }
    setIsClosing(true);
    setTimeout(() => {
      setPanelMode(null);
      setSelectedStyle(null);
      setIsDirty(false);
      setIsClosing(false);
    }, 200);
  }, []);

  const handleCloseAttempt = useCallback(() => {
    if (isDirty && (panelMode === "edit" || panelMode === "create" || panelMode === "shadow-edit")) {
      setShowDiscardDialog(true);
    } else {
      closePanel();
    }
  }, [isDirty, panelMode, closePanel]);

  // Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && panelMode) {
        handleCloseAttempt();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [panelMode, handleCloseAttempt]);

  const openView = async (name: string) => {
    setDetailLoading(true);
    setPanelMode("view");
    const styleInfo = styles.find((s) => s.name === name);
    setSelectedStyleType(styleInfo?.style_type || "builtin");
    try {
      const detail = await getStyle(name);
      setSelectedStyle(detail);
    } catch {
      setSelectedStyle(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const openCreate = () => {
    setSelectedStyle(null);
    setSelectedStyleType("custom");
    setPanelMode("create");
  };

  const openEdit = () => {
    setPanelMode("edit");
  };

  const handleCustomize = async (name: string) => {
    try {
      const result = await duplicateStyle(name);
      setSelectedStyle(result);
      setSelectedStyleType("shadow");
      setPanelMode("shadow-edit");
      loadStyles();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to customize");
    }
  };

  const handleSave = async (data: StyleDetail) => {
    try {
      if (panelMode === "create") {
        await createStyle(data);
        showSuccess("Style created");
      } else {
        await updateStyle(data.name, data);
        showSuccess("Style saved");
      }
      loadStyles();
      // Switch to view mode after save
      const refreshed = await getStyle(data.name);
      setSelectedStyle(refreshed);
      const refreshedInfo = (await getStyles()).find((s) => s.name === data.name);
      setSelectedStyleType(refreshedInfo?.style_type || "custom");
      setPanelMode("view");
      setIsDirty(false);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to save");
      throw err; // re-throw so form stays in saving state
    }
  };

  const handleDelete = (name: string) => {
    setConfirmDialog({
      open: true,
      title: "Delete Style",
      message: `Delete '${name}'? This cannot be undone.`,
      confirmLabel: "Delete",
      onConfirm: async () => {
        setConfirmDialog((d) => ({ ...d, open: false }));
        try {
          await deleteStyle(name);
          showSuccess("Style deleted");
          loadStyles();
          closePanel();
        } catch (err) {
          showError(err instanceof Error ? err.message : "Failed to delete");
        }
      },
    });
  };

  const handleResetToDefault = (name: string) => {
    setConfirmDialog({
      open: true,
      title: "Reset to Default",
      message: `Reset '${name}' to default? Your customizations will be removed.`,
      confirmLabel: "Reset",
      onConfirm: async () => {
        setConfirmDialog((d) => ({ ...d, open: false }));
        try {
          await deleteStyle(name);
          showSuccess("Style reset to default");
          loadStyles();
          // Reload as built-in
          const refreshed = await getStyle(name);
          setSelectedStyle(refreshed);
          setSelectedStyleType("builtin");
          setPanelMode("view");
        } catch (err) {
          showError(err instanceof Error ? err.message : "Failed to reset");
        }
      },
    });
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const result = await importStyle(text);
      showSuccess("Style imported");
      loadStyles();
      setSelectedStyle(result);
      setSelectedStyleType("custom");
      setPanelMode("view");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to import");
    }
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // --- Panel animation classes ---
  const panelAnimation = isClosing
    ? "animate-[slideOutRight_200ms_ease-in_forwards]"
    : "animate-[slideInRight_300ms_ease-out_both]";

  return (
    <div className="relative animate-fade-in">
      {/* Header with actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2">
        <div>
          <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)]">
            Style Manager
          </h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">
            Create, customize, and manage translation style templates.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openCreate}
            aria-label="Create new style"
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg
                       bg-blue-600 hover:bg-blue-700 text-white
                       transition-colors duration-200 cursor-pointer
                       focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          >
            <Plus size={16} /> New Style
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            aria-label="Import YAML file"
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg
                       bg-white/10 hover:bg-white/20 text-gray-300
                       transition-colors duration-200 cursor-pointer
                       focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          >
            <Upload size={16} /> Import YAML
          </button>
          <input
            type="file"
            accept=".yaml,.yml"
            ref={fileInputRef}
            className="hidden"
            onChange={handleImportFile}
          />
        </div>
      </div>

      {/* Search bar */}
      <div className="relative mb-6 mt-4">
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
          {filtered.map((style) => {
            const badge = badgeConfig[style.style_type] || badgeConfig.custom;
            return (
              <div
                key={style.name}
                role="button"
                tabIndex={0}
                onClick={() => openView(style.name)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    openView(style.name);
                  }
                }}
                className="text-left bg-[var(--bg-surface)] border border-[var(--border-default)]
                  rounded-xl p-5 cursor-pointer hover:border-[var(--border-hover)]
                  hover:shadow-[var(--shadow-md)] transition-all duration-200 group
                  focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
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
                <div className="flex items-center gap-2 flex-wrap">
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
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.className}`}
                    aria-label={`Style type: ${badge.label}`}
                  >
                    {badge.label}
                  </span>
                  {/* Customize button on built-in cards */}
                  {style.style_type === "builtin" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCustomize(style.name);
                      }}
                      aria-label={`Customize ${style.name}`}
                      className="ml-auto text-xs flex items-center gap-1 px-2 py-0.5 rounded-full
                                 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-amber-300
                                 transition-colors cursor-pointer
                                 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    >
                      <Wrench size={12} /> Customize
                    </button>
                  )}
                </div>
              </div>
            );
          })}
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
              : "Click \"New Style\" to create your first template."}
          </p>
        </div>
      )}

      {/* Slide-in panel */}
      {panelMode !== null && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/40 z-30"
            onClick={handleCloseAttempt}
            style={{ animation: "fadeIn 200ms ease-out both" }}
          />

          {/* Panel */}
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="panel-title"
            className={`fixed right-0 top-0 h-screen w-full bg-[var(--bg-surface)]
              border-l border-[var(--border-default)] z-40 overflow-y-auto
              ${panelMode === "view" ? "max-w-lg" : "max-w-xl"}
              ${panelAnimation}`}
          >
            {/* Panel header */}
            <div className="sticky top-0 bg-[var(--bg-surface)] border-b border-[var(--border-default)] px-6 py-4 z-10">
              <div className="flex items-center justify-between">
                <h2
                  id="panel-title"
                  className="font-[var(--font-fira-code)] text-lg font-bold text-[var(--text-primary)]"
                >
                  {panelMode === "create"
                    ? "Create New Style"
                    : panelMode === "edit" || panelMode === "shadow-edit"
                      ? `Edit: ${selectedStyle?.name || ""}`
                      : detailLoading
                        ? "Loading..."
                        : selectedStyle?.name || ""}
                </h2>
                <button
                  onClick={handleCloseAttempt}
                  aria-label="Close panel"
                  className="p-1.5 rounded-lg hover:bg-[var(--bg-elevated)] text-[var(--text-muted)]
                             hover:text-[var(--text-primary)] transition-colors cursor-pointer
                             focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                >
                  <X size={18} />
                </button>
              </div>

              {/* View mode action buttons */}
              {panelMode === "view" && selectedStyle && !detailLoading && (
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {selectedStyleType === "builtin" && (
                    <button
                      onClick={() => handleCustomize(selectedStyle.name)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                                 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300
                                 transition-colors cursor-pointer
                                 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    >
                      <Wrench size={14} /> Customize
                    </button>
                  )}
                  {selectedStyleType === "custom" && (
                    <>
                      <button
                        onClick={openEdit}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                                   bg-blue-500/10 hover:bg-blue-500/20 text-blue-300
                                   transition-colors cursor-pointer
                                   focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                      >
                        <Pencil size={14} /> Edit
                      </button>
                      <button
                        onClick={() => handleDelete(selectedStyle.name)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                                   bg-red-500/10 hover:bg-red-500/20 text-red-300
                                   transition-colors cursor-pointer
                                   focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                    </>
                  )}
                  {selectedStyleType === "shadow" && (
                    <>
                      <button
                        onClick={() => setPanelMode("shadow-edit")}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                                   bg-blue-500/10 hover:bg-blue-500/20 text-blue-300
                                   transition-colors cursor-pointer
                                   focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                      >
                        <Pencil size={14} /> Edit
                      </button>
                      <button
                        onClick={() => handleResetToDefault(selectedStyle.name)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                                   bg-amber-500/10 hover:bg-amber-500/20 text-amber-300
                                   transition-colors cursor-pointer
                                   focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                      >
                        <RotateCcw size={14} /> Reset to Default
                      </button>
                    </>
                  )}
                  {/* Export always visible */}
                  <a
                    href={getStyleExportUrl(selectedStyle.name)}
                    download={`${selectedStyle.name}.yaml`}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                               bg-white/5 hover:bg-white/10 text-gray-300
                               transition-colors cursor-pointer
                               focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                  >
                    <Download size={14} /> Export YAML
                  </a>
                </div>
              )}
            </div>

            {/* Panel body */}
            <div className="p-6">
              {/* Loading */}
              {detailLoading && (
                <div className="space-y-4">
                  <div className="skeleton h-4 w-3/4" />
                  <div className="skeleton h-4 w-1/2" />
                  <div className="skeleton h-24 w-full rounded-lg" />
                  <div className="skeleton h-48 w-full rounded-lg" />
                </div>
              )}

              {/* VIEW mode */}
              {panelMode === "view" && selectedStyle && !detailLoading && (
                <div className="space-y-6">
                  {/* Description */}
                  <div>
                    <p className="text-[var(--text-secondary)] text-sm leading-relaxed">
                      {selectedStyle.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {selectedStyle.tone && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{
                            backgroundColor: `color-mix(in srgb, ${getToneColor(selectedStyle.tone)} 15%, transparent)`,
                            color: getToneColor(selectedStyle.tone),
                          }}
                        >
                          Tone: {selectedStyle.tone}
                        </span>
                      )}
                      {selectedStyleType && (
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${badgeConfig[selectedStyleType]?.className || ""}`}
                        >
                          {badgeConfig[selectedStyleType]?.label || selectedStyleType}
                        </span>
                      )}
                    </div>
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
              )}

              {/* CREATE / EDIT / SHADOW-EDIT modes */}
              {(panelMode === "create" || panelMode === "edit" || panelMode === "shadow-edit") && (
                <StyleEditorForm
                  initialData={panelMode === "create" ? null : selectedStyle}
                  mode={panelMode}
                  onSave={handleSave}
                  onCancel={handleCloseAttempt}
                  onDirtyChange={setIsDirty}
                />
              )}
            </div>
          </div>
        </>
      )}

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.title}
        message={confirmDialog.message}
        confirmLabel={confirmDialog.confirmLabel}
        confirmVariant="danger"
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog((d) => ({ ...d, open: false }))}
      />

      {/* Discard changes dialog */}
      <ConfirmDialog
        open={showDiscardDialog}
        title="Discard Changes"
        message="You have unsaved changes. Discard them?"
        confirmLabel="Discard"
        confirmVariant="danger"
        onConfirm={() => {
          setShowDiscardDialog(false);
          closePanel();
        }}
        onCancel={() => setShowDiscardDialog(false)}
      />
    </div>
  );
}
