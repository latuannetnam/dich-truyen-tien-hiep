"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Plus,
  Trash2,
  Loader2,
  Sparkles,
  PenLine,
  Save,
  X,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { generateStyle } from "@/lib/api";
import type { StyleDetail } from "@/lib/types";

interface StyleEditorFormProps {
  initialData: StyleDetail | null;
  mode: "create" | "edit" | "shadow-edit";
  onSave: (data: StyleDetail) => Promise<void>;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
}

const TONE_OPTIONS = ["formal", "casual", "archaic", "poetic", "literary"];

function emptyStyle(): StyleDetail {
  return {
    name: "",
    description: "",
    guidelines: [""],
    vocabulary: {},
    tone: "formal",
    examples: [],
  };
}

export default function StyleEditorForm({
  initialData,
  mode,
  onSave,
  onCancel,
  onDirtyChange,
}: StyleEditorFormProps) {
  const [form, setForm] = useState<StyleDetail>(initialData ?? emptyStyle());
  const [vocabEntries, setVocabEntries] = useState<{ key: string; value: string }[]>(() => {
    const vocab = initialData?.vocabulary ?? {};
    const entries = Object.entries(vocab).map(([key, value]) => ({ key, value }));
    return entries.length > 0 ? entries : [];
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // AI Generate state
  const [showAI, setShowAI] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");

  const firstErrorRef = useRef<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null>(null);

  // Track dirty state
  useEffect(() => {
    const dirty = JSON.stringify(form) !== JSON.stringify(initialData ?? emptyStyle())
      || JSON.stringify(vocabEntries) !== JSON.stringify(
        Object.entries(initialData?.vocabulary ?? {}).map(([key, value]) => ({ key, value }))
      );
    setIsDirty(dirty);
    onDirtyChange(dirty);
  }, [form, vocabEntries, initialData, onDirtyChange]);

  // Ctrl+S shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        if (isDirty && !hasErrors() && !isSaving) handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isDirty, isSaving, form, vocabEntries]);

  const hasErrors = useCallback(() => {
    return Object.keys(errors).length > 0;
  }, [errors]);

  const validate = useCallback((): Record<string, string> => {
    const errs: Record<string, string> = {};
    if (mode === "create" && !form.name.trim()) {
      errs.name = "Name is required";
    }
    if (mode === "create" && form.name && !/^[a-z][a-z0-9_]*$/.test(form.name)) {
      errs.name = "Use snake_case (lowercase letters, numbers, underscores)";
    }
    if (!form.description.trim()) {
      errs.description = "Description is required";
    }
    if (form.description.length > 200) {
      errs.description = "Description must be 200 characters or less";
    }
    if (!form.guidelines.some((g) => g.trim())) {
      errs.guidelines = "At least one guideline is required";
    }
    return errs;
  }, [form, mode]);

  const handleSave = async () => {
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) {
      // Focus first invalid field
      setTimeout(() => firstErrorRef.current?.focus(), 50);
      return;
    }

    setIsSaving(true);
    try {
      const vocab: Record<string, string> = {};
      vocabEntries.forEach(({ key, value }) => {
        if (key.trim()) vocab[key.trim()] = value.trim();
      });
      await onSave({ ...form, vocabulary: vocab });
    } finally {
      setIsSaving(false);
    }
  };

  const handleAIGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setAiLoading(true);
    setAiError("");
    try {
      const result = await generateStyle(aiPrompt);
      setForm(result);
      const entries = Object.entries(result.vocabulary ?? {}).map(([key, value]) => ({ key, value }));
      setVocabEntries(entries);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Generation failed. Please try again.");
    } finally {
      setAiLoading(false);
    }
  };

  // --- Dynamic list helpers ---
  const addGuideline = () => setForm((f) => ({ ...f, guidelines: [...f.guidelines, ""] }));
  const removeGuideline = (idx: number) =>
    setForm((f) => ({ ...f, guidelines: f.guidelines.filter((_, i) => i !== idx) }));
  const updateGuideline = (idx: number, val: string) =>
    setForm((f) => ({ ...f, guidelines: f.guidelines.map((g, i) => (i === idx ? val : g)) }));

  const addVocabEntry = () => setVocabEntries((v) => [...v, { key: "", value: "" }]);
  const removeVocabEntry = (idx: number) =>
    setVocabEntries((v) => v.filter((_, i) => i !== idx));
  const updateVocabEntry = (idx: number, field: "key" | "value", val: string) =>
    setVocabEntries((v) => v.map((e, i) => (i === idx ? { ...e, [field]: val } : e)));

  const addExample = () =>
    setForm((f) => ({ ...f, examples: [...f.examples, { chinese: "", vietnamese: "" }] }));
  const removeExample = (idx: number) =>
    setForm((f) => ({ ...f, examples: f.examples.filter((_, i) => i !== idx) }));
  const updateExample = (idx: number, field: "chinese" | "vietnamese", val: string) =>
    setForm((f) => ({
      ...f,
      examples: f.examples.map((ex, i) => (i === idx ? { ...ex, [field]: val } : ex)),
    }));

  const inputClass =
    "w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white " +
    "placeholder-gray-500 transition-colors " +
    "focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none";

  return (
    <div className="space-y-5">
      {/* Shadow-edit banner */}
      {mode === "shadow-edit" && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm">
          <PenLine size={16} className="shrink-0" />
          <span>Customizing built-in style — your changes override the default</span>
        </div>
      )}

      {/* Name field */}
      <div>
        <label htmlFor="style-name" className="block text-sm font-medium text-gray-300 mb-1">
          Name
        </label>
        <input
          ref={errors.name ? (el) => { firstErrorRef.current = el; } : undefined}
          id="style-name"
          type="text"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          disabled={mode !== "create"}
          placeholder="my_custom_style"
          aria-describedby={errors.name ? "name-error" : undefined}
          className={`${inputClass} ${mode !== "create" ? "opacity-50 cursor-not-allowed" : ""}`}
        />
        {errors.name && (
          <span id="name-error" className="text-red-400 text-xs mt-1 block" role="alert">
            {errors.name}
          </span>
        )}
      </div>

      {/* Description field */}
      <div>
        <label htmlFor="style-desc" className="block text-sm font-medium text-gray-300 mb-1">
          Description
        </label>
        <textarea
          ref={errors.description && !errors.name ? (el) => { firstErrorRef.current = el; } : undefined}
          id="style-desc"
          rows={2}
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          placeholder="Describe the translation style..."
          aria-describedby={errors.description ? "desc-error" : undefined}
          className={inputClass}
        />
        {errors.description && (
          <span id="desc-error" className="text-red-400 text-xs mt-1 block" role="alert">
            {errors.description}
          </span>
        )}
      </div>

      {/* Tone dropdown */}
      <div>
        <label htmlFor="style-tone" className="block text-sm font-medium text-gray-300 mb-1">
          Tone
        </label>
        <select
          id="style-tone"
          value={form.tone}
          onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
          className={`${inputClass} cursor-pointer`}
        >
          {TONE_OPTIONS.map((t) => (
            <option key={t} value={t} className="bg-[#1E293B]">
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Guidelines */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Guidelines
        </label>
        {errors.guidelines && (
          <span className="text-red-400 text-xs mb-1 block" role="alert">
            {errors.guidelines}
          </span>
        )}
        <div className="space-y-2">
          {form.guidelines.map((guideline, idx) => (
            <div key={idx} className="flex gap-2 items-start animate-fade-in">
              <input
                type="text"
                value={guideline}
                onChange={(e) => updateGuideline(idx, e.target.value)}
                placeholder={`Guideline ${idx + 1}`}
                aria-label={`Guideline ${idx + 1}`}
                className={`${inputClass} flex-1`}
              />
              <button
                type="button"
                onClick={() => removeGuideline(idx)}
                disabled={form.guidelines.length <= 1}
                aria-label={`Remove guideline ${idx + 1}`}
                title={form.guidelines.length <= 1 ? "At least one guideline required" : undefined}
                className="p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10
                           transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed
                           focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addGuideline}
          className="mt-2 flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300
                     transition-colors cursor-pointer
                     focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
        >
          <Plus size={14} /> Add guideline
        </button>
      </div>

      {/* Vocabulary */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Vocabulary Mappings
        </label>
        <div className="space-y-2">
          {vocabEntries.map((entry, idx) => (
            <div key={idx} className="flex flex-col sm:flex-row gap-2 items-start animate-fade-in">
              <input
                type="text"
                value={entry.key}
                onChange={(e) => updateVocabEntry(idx, "key", e.target.value)}
                placeholder="Chinese term"
                aria-label={`Vocabulary Chinese term ${idx + 1}`}
                className={`${inputClass} flex-1`}
              />
              <input
                type="text"
                value={entry.value}
                onChange={(e) => updateVocabEntry(idx, "value", e.target.value)}
                placeholder="Vietnamese translation"
                aria-label={`Vocabulary Vietnamese translation ${idx + 1}`}
                className={`${inputClass} flex-1`}
              />
              <button
                type="button"
                onClick={() => removeVocabEntry(idx)}
                aria-label={`Remove vocabulary entry ${idx + 1}`}
                className="p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10
                           transition-colors cursor-pointer shrink-0
                           focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addVocabEntry}
          className="mt-2 flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300
                     transition-colors cursor-pointer
                     focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
        >
          <Plus size={14} /> Add vocabulary entry
        </button>
      </div>

      {/* Examples */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Translation Examples
        </label>
        <div className="space-y-3">
          {form.examples.map((ex, idx) => (
            <div key={idx} className="space-y-1 p-3 rounded-lg bg-white/5 border border-white/5 animate-fade-in">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-gray-500">Example {idx + 1}</span>
                <button
                  type="button"
                  onClick={() => removeExample(idx)}
                  aria-label={`Remove example ${idx + 1}`}
                  className="p-1 rounded text-gray-400 hover:text-red-400 hover:bg-red-500/10
                             transition-colors cursor-pointer
                             focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <textarea
                rows={1}
                value={ex.chinese}
                onChange={(e) => updateExample(idx, "chinese", e.target.value)}
                placeholder="Chinese text"
                aria-label={`Example ${idx + 1} Chinese text`}
                className={inputClass}
              />
              <textarea
                rows={1}
                value={ex.vietnamese}
                onChange={(e) => updateExample(idx, "vietnamese", e.target.value)}
                placeholder="Vietnamese translation"
                aria-label={`Example ${idx + 1} Vietnamese translation`}
                className={inputClass}
              />
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addExample}
          className="mt-2 flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300
                     transition-colors cursor-pointer
                     focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
        >
          <Plus size={14} /> Add example
        </button>
      </div>

      {/* AI Generate section (CREATE mode only) */}
      {mode === "create" && (
        <div className="border border-white/10 rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => setShowAI(!showAI)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm
                       bg-gradient-to-r from-purple-500/10 to-blue-500/10
                       hover:from-purple-500/15 hover:to-blue-500/15
                       text-purple-300 transition-all cursor-pointer
                       focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          >
            <span className="flex items-center gap-2">
              <Sparkles size={16} />
              Generate with AI
            </span>
            {showAI ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {showAI && (
            <div className="p-4 space-y-3 border-t border-white/10 animate-fade-in">
              <label htmlFor="ai-desc" className="block text-sm font-medium text-gray-300">
                Describe the style you want
              </label>
              <textarea
                id="ai-desc"
                rows={3}
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="E.g.: Phong cách tiên hiệp cổ điển, ngôn ngữ trang trọng..."
                className={inputClass}
              />
              {aiError && (
                <p className="text-red-400 text-xs" role="alert">
                  {aiError}
                </p>
              )}
              <button
                type="button"
                onClick={handleAIGenerate}
                disabled={aiLoading || !aiPrompt.trim()}
                className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg
                           bg-purple-600 hover:bg-purple-700 text-white
                           transition-colors cursor-pointer
                           disabled:opacity-50 disabled:cursor-not-allowed
                           focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
              >
                {aiLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Generating...
                  </>
                ) : (
                  <>
                    <Sparkles size={16} /> Generate
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 justify-end pt-2 border-t border-white/10">
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg
                     bg-white/10 hover:bg-white/20 text-gray-300
                     transition-colors cursor-pointer
                     focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
        >
          <X size={16} /> Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!isDirty || isSaving}
          className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg
                      transition-colors cursor-pointer
                      focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none
                      bg-blue-600 hover:bg-blue-700 text-white
                      ${(!isDirty) ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {isSaving ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Saving...
            </>
          ) : (
            <>
              <Save size={16} />
              {mode === "shadow-edit" ? "Save Customization" : "Save"}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
