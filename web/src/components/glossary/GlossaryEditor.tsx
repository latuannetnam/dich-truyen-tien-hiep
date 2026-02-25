"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import {
  Search,
  Plus,
  Upload,
  Download,
  Pencil,
  Trash2,
  Check,
  X,
  Loader2,
} from "lucide-react";
import type { GlossaryEntryType, GlossaryResponseType } from "@/lib/types";
import {
  addGlossaryEntry,
  updateGlossaryEntry,
  deleteGlossaryEntry,
  importGlossaryCsv,
  getGlossaryExportUrl,
} from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";

const CATEGORY_COLORS: Record<string, string> = {
  character: "bg-teal-500/15 text-teal-400",
  realm: "bg-purple-500/15 text-purple-400",
  technique: "bg-blue-500/15 text-blue-400",
  location: "bg-amber-500/15 text-amber-400",
  item: "bg-emerald-500/15 text-emerald-400",
  organization: "bg-rose-500/15 text-rose-400",
  general: "bg-gray-500/15 text-gray-400",
};

interface Props {
  bookId: string;
  data: GlossaryResponseType;
  onRefresh: () => void;
}

export default function GlossaryEditor({ bookId, data, onRefresh }: Props) {
  const { showSuccess, showError } = useToast();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [editingTerm, setEditingTerm] = useState<string | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [deletingTerm, setDeletingTerm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit form state
  const [editForm, setEditForm] = useState({
    chinese: "",
    vietnamese: "",
    category: "general",
    notes: "",
  });

  const filteredEntries = useMemo(() => {
    return data.entries.filter((e) => {
      const matchSearch =
        !search ||
        e.chinese.includes(search) ||
        e.vietnamese.toLowerCase().includes(search.toLowerCase());
      const matchCategory =
        categoryFilter === "all" || e.category === categoryFilter;
      return matchSearch && matchCategory;
    });
  }, [data.entries, search, categoryFilter]);

  const startEdit = useCallback((entry: GlossaryEntryType) => {
    setEditingTerm(entry.chinese);
    setEditForm({
      chinese: entry.chinese,
      vietnamese: entry.vietnamese,
      category: entry.category,
      notes: entry.notes || "",
    });
    setAddingNew(false);
    setDeletingTerm(null);
  }, []);

  const startAdd = useCallback(() => {
    setAddingNew(true);
    setEditForm({ chinese: "", vietnamese: "", category: "general", notes: "" });
    setEditingTerm(null);
    setDeletingTerm(null);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingTerm(null);
    setAddingNew(false);
    setDeletingTerm(null);
  }, []);

  const handleSave = async () => {
    if (!editForm.chinese.trim() || !editForm.vietnamese.trim()) return;
    setSaving(true);
    try {
      if (addingNew) {
        await addGlossaryEntry(bookId, {
          chinese: editForm.chinese,
          vietnamese: editForm.vietnamese,
          category: editForm.category,
          notes: editForm.notes || undefined,
        });
        showSuccess("Entry added");
      } else if (editingTerm) {
        await updateGlossaryEntry(bookId, editingTerm, {
          chinese: editForm.chinese,
          vietnamese: editForm.vietnamese,
          category: editForm.category,
          notes: editForm.notes || undefined,
        });
        showSuccess("Entry updated");
      }
      cancelEdit();
      onRefresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (term: string) => {
    setSaving(true);
    try {
      await deleteGlossaryEntry(bookId, term);
      showSuccess("Entry deleted");
      setDeletingTerm(null);
      onRefresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setSaving(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importGlossaryCsv(bookId, file);
      showSuccess(`Imported ${result.imported} entries`);
      onRefresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Import failed");
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
            aria-hidden="true"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search terms..."
            className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg pl-10 pr-4 py-2.5 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150 text-sm"
          />
        </div>

        {/* Category filter */}
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-2.5 text-[var(--text-primary)] focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150 text-sm cursor-pointer"
        >
          <option value="all">All Categories</option>
          {data.categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>

        {/* Actions */}
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleImport}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer"
          >
            <Upload size={14} aria-hidden="true" />
            Import
          </button>
          <a
            href={getGlossaryExportUrl(bookId)}
            download
            className="inline-flex items-center gap-1.5 border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer"
          >
            <Download size={14} aria-hidden="true" />
            Export
          </a>
          <button
            onClick={startAdd}
            className="inline-flex items-center gap-1.5 bg-[var(--color-primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors cursor-pointer"
          >
            <Plus size={14} aria-hidden="true" />
            Add
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-[var(--bg-elevated)]">
              <th className="text-left text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] px-4 py-3">
                Chinese
              </th>
              <th className="text-left text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] px-4 py-3">
                Vietnamese
              </th>
              <th className="text-left text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] px-4 py-3">
                Category
              </th>
              <th className="text-left text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] px-4 py-3">
                Notes
              </th>
              <th className="text-right text-[var(--text-muted)] text-xs uppercase tracking-wider font-[var(--font-fira-code)] px-4 py-3 w-24">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {/* Add new row */}
            {addingNew && (
              <tr className="bg-[var(--bg-elevated)]/30">
                <td className="px-4 py-2">
                  <input
                    type="text"
                    value={editForm.chinese}
                    onChange={(e) =>
                      setEditForm({ ...editForm, chinese: e.target.value })
                    }
                    placeholder="Chinese"
                    autoFocus
                    className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="text"
                    value={editForm.vietnamese}
                    onChange={(e) =>
                      setEditForm({ ...editForm, vietnamese: e.target.value })
                    }
                    placeholder="Vietnamese"
                    className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none"
                  />
                </td>
                <td className="px-4 py-2">
                  <select
                    value={editForm.category}
                    onChange={(e) =>
                      setEditForm({ ...editForm, category: e.target.value })
                    }
                    className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none cursor-pointer"
                  >
                    {data.categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2">
                  <input
                    type="text"
                    value={editForm.notes}
                    onChange={(e) =>
                      setEditForm({ ...editForm, notes: e.target.value })
                    }
                    placeholder="Notes"
                    className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none"
                  />
                </td>
                <td className="px-4 py-2 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer text-[#10B981]"
                      aria-label="Save"
                    >
                      {saving ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Check size={14} />
                      )}
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer text-[var(--text-muted)]"
                      aria-label="Cancel"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            )}

            {filteredEntries.map((entry) => {
              const isEditing = editingTerm === entry.chinese;
              const isDeleting = deletingTerm === entry.chinese;

              if (isDeleting) {
                return (
                  <tr
                    key={entry.chinese}
                    className="bg-[#EF4444]/5 border-b border-[var(--border-default)]"
                  >
                    <td colSpan={4} className="px-4 py-3">
                      <span className="text-sm text-[#EF4444]">
                        Delete &ldquo;{entry.chinese}&rdquo; ({entry.vietnamese})?
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleDelete(entry.chinese)}
                          disabled={saving}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-[#EF4444] text-white hover:bg-[#DC2626] transition-colors cursor-pointer"
                        >
                          {saving ? "..." : "Confirm"}
                        </button>
                        <button
                          onClick={() => setDeletingTerm(null)}
                          className="px-2.5 py-1 rounded text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              }

              if (isEditing) {
                return (
                  <tr
                    key={entry.chinese}
                    className="bg-[var(--bg-elevated)]/30 border-b border-[var(--border-default)]"
                  >
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editForm.chinese}
                        onChange={(e) =>
                          setEditForm({ ...editForm, chinese: e.target.value })
                        }
                        className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editForm.vietnamese}
                        onChange={(e) =>
                          setEditForm({ ...editForm, vietnamese: e.target.value })
                        }
                        className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={editForm.category}
                        onChange={(e) =>
                          setEditForm({ ...editForm, category: e.target.value })
                        }
                        className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none cursor-pointer"
                      >
                        {data.categories.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editForm.notes}
                        onChange={(e) =>
                          setEditForm({ ...editForm, notes: e.target.value })
                        }
                        className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded px-2 py-1.5 text-[var(--text-primary)] w-full text-sm focus:border-[var(--color-primary)] outline-none"
                      />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={handleSave}
                          disabled={saving}
                          className="p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer text-[#10B981]"
                          aria-label="Save"
                        >
                          {saving ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <Check size={14} />
                          )}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer text-[var(--text-muted)]"
                          aria-label="Cancel"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              }

              return (
                <tr
                  key={entry.chinese}
                  className="border-b border-[var(--border-default)] hover:bg-[var(--bg-elevated)]/50 transition-colors duration-150"
                >
                  <td className="px-4 py-3 text-[var(--text-primary)] text-sm font-medium">
                    {entry.chinese}
                  </td>
                  <td className="px-4 py-3 text-[var(--text-primary)] text-sm">
                    {entry.vietnamese}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.general
                      }`}
                    >
                      {entry.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[var(--text-muted)] text-sm">
                    {entry.notes || "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => startEdit(entry)}
                        className="p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer text-[var(--text-secondary)]"
                        aria-label={`Edit ${entry.chinese}`}
                      >
                        <Pencil size={14} aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => setDeletingTerm(entry.chinese)}
                        className="p-1.5 rounded hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer text-[#EF4444]"
                        aria-label={`Delete ${entry.chinese}`}
                      >
                        <Trash2 size={14} aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}

            {filteredEntries.length === 0 && !addingNew && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-12 text-center text-[var(--text-muted)] text-sm"
                >
                  {search || categoryFilter !== "all"
                    ? "No entries match your filters"
                    : "No glossary entries yet. Click \"+ Add\" to create one."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
