"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, ChevronLeft, Play, Loader2 } from "lucide-react";
import { startPipeline } from "@/lib/api";
import WizardSteps from "@/components/wizard/WizardSteps";

const STEPS = ["URL", "Options", "Confirm"];

const STYLES = [
  { value: "tien_hiep", label: "Tiên Hiệp" },
  { value: "kiem_hiep", label: "Kiếm Hiệp" },
  { value: "huyen_huyen", label: "Huyền Huyễn" },
  { value: "do_thi", label: "Đô Thị" },
];

export default function NewTranslationPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [url, setUrl] = useState("");
  const [bookDir, setBookDir] = useState("");
  const [style, setStyle] = useState("tien_hiep");
  const [workers, setWorkers] = useState(3);
  const [chapters, setChapters] = useState("");
  const [autoGlossary, setAutoGlossary] = useState(true);
  const [crawlOnly, setCrawlOnly] = useState(false);
  const [translateOnly, setTranslateOnly] = useState(false);
  const [force, setForce] = useState(false);

  const canGoNext = currentStep === 1 ? (url.trim() || bookDir.trim()) : true;

  const handleNext = () => {
    if (currentStep < 3) setCurrentStep(currentStep + 1);
  };

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  const handleStart = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const job = await startPipeline({
        url: url.trim() || undefined,
        book_dir: bookDir.trim() || undefined,
        style,
        workers,
        chapters: chapters.trim() || undefined,
        crawl_only: crawlOnly,
        translate_only: translateOnly,
        no_glossary: !autoGlossary,
        force,
      });
      router.push(`/pipeline/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start pipeline");
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)] mb-2">
        New Translation
      </h1>
      <p className="text-[var(--text-secondary)] mb-8">
        Start a new book translation pipeline
      </p>

      <WizardSteps steps={STEPS} currentStep={currentStep} />

      <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-8 max-w-2xl">
        {/* Step 1: URL */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              Enter Book URL
            </h2>

            <div>
              <label
                htmlFor="url"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Book URL
              </label>
              <input
                id="url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://truyenfull.vn/tien-nghich/"
                className="
                  bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg
                  px-4 py-3 text-[var(--text-primary)] w-full
                  focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20
                  outline-none transition-all duration-150
                  placeholder:text-[var(--text-muted)]
                "
              />
            </div>

            <div className="flex items-center gap-4">
              <div className="h-px flex-1 bg-[var(--border-default)]" />
              <span className="text-[var(--text-muted)] text-sm">or</span>
              <div className="h-px flex-1 bg-[var(--border-default)]" />
            </div>

            <div>
              <label
                htmlFor="bookDir"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Existing Book Directory
              </label>
              <input
                id="bookDir"
                type="text"
                value={bookDir}
                onChange={(e) => setBookDir(e.target.value)}
                placeholder="books/tien-nghich"
                className="
                  bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg
                  px-4 py-3 text-[var(--text-primary)] w-full
                  focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20
                  outline-none transition-all duration-150
                  placeholder:text-[var(--text-muted)]
                "
              />
            </div>
          </div>
        )}

        {/* Step 2: Options */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              Configure Options
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Style */}
              <div>
                <label
                  htmlFor="style"
                  className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
                >
                  Translation Style
                </label>
                <select
                  id="style"
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="
                    bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg
                    px-4 py-3 text-[var(--text-primary)] w-full
                    focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20
                    outline-none transition-all duration-150 cursor-pointer
                  "
                >
                  {STYLES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Workers */}
              <div>
                <label className="text-[var(--text-secondary)] text-sm font-medium mb-2 block">
                  Workers
                </label>
                <div className="flex gap-2" role="radiogroup" aria-label="Number of workers">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      role="radio"
                      aria-checked={workers === n}
                      onClick={() => setWorkers(n)}
                      className={`
                        w-10 h-10 rounded-lg text-sm font-medium
                        transition-colors duration-150 cursor-pointer
                        ${
                          workers === n
                            ? "bg-[var(--color-primary)] text-white"
                            : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--border-hover)]"
                        }
                      `}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Chapter Range */}
            <div>
              <label
                htmlFor="chapters"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Chapter Range (optional)
              </label>
              <input
                id="chapters"
                type="text"
                value={chapters}
                onChange={(e) => setChapters(e.target.value)}
                placeholder="e.g. 1-100"
                className="
                  bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg
                  px-4 py-3 text-[var(--text-primary)] w-full
                  focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20
                  outline-none transition-all duration-150
                  placeholder:text-[var(--text-muted)]
                "
              />
            </div>

            {/* Checkboxes */}
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Auto-generate glossary", checked: autoGlossary, onChange: setAutoGlossary },
                { label: "Crawl only", checked: crawlOnly, onChange: setCrawlOnly },
                { label: "Translate only", checked: translateOnly, onChange: setTranslateOnly },
                { label: "Force re-process", checked: force, onChange: setForce },
              ].map((opt) => (
                <label
                  key={opt.label}
                  className="flex items-center gap-3 cursor-pointer group"
                >
                  <div
                    className={`
                      w-5 h-5 rounded flex items-center justify-center
                      transition-colors duration-150
                      ${
                        opt.checked
                          ? "bg-[var(--color-primary)] border-[var(--color-primary)]"
                          : "bg-[var(--bg-surface)] border border-[var(--border-default)] group-hover:border-[var(--border-hover)]"
                      }
                    `}
                  >
                    {opt.checked && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path
                          d="M2 6L5 9L10 3"
                          stroke="white"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                  <input
                    type="checkbox"
                    checked={opt.checked}
                    onChange={(e) => opt.onChange(e.target.checked)}
                    className="sr-only"
                  />
                  <span className="text-[var(--text-secondary)] text-sm">
                    {opt.label}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              Confirm & Start
            </h2>

            <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6 space-y-0">
              {[
                { label: "Source", value: url || bookDir || "—" },
                { label: "Style", value: STYLES.find((s) => s.value === style)?.label || style },
                { label: "Workers", value: String(workers) },
                { label: "Chapters", value: chapters || "All" },
                { label: "Auto Glossary", value: autoGlossary ? "Yes" : "No" },
                { label: "Crawl Only", value: crawlOnly ? "Yes" : "No" },
                { label: "Translate Only", value: translateOnly ? "Yes" : "No" },
                { label: "Force", value: force ? "Yes" : "No" },
              ].map((row) => (
                <div
                  key={row.label}
                  className="flex justify-between py-3 border-b border-[var(--border-default)] last:border-0"
                >
                  <span className="text-[var(--text-muted)] text-sm">{row.label}</span>
                  <span className="text-[var(--text-primary)] text-sm font-medium">
                    {row.value}
                  </span>
                </div>
              ))}
            </div>

            {error && (
              <div className="text-[var(--color-error)] text-sm bg-[var(--color-error)]/10 rounded-lg px-4 py-3">
                {error}
              </div>
            )}
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between mt-8">
          <div>
            {currentStep > 1 && (
              <button
                onClick={handleBack}
                className="
                  inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium
                  text-[var(--text-secondary)] hover:text-[var(--text-primary)]
                  hover:bg-[var(--bg-elevated)]
                  transition-colors duration-150 cursor-pointer
                "
              >
                <ChevronLeft size={16} />
                Back
              </button>
            )}
          </div>

          <div>
            {currentStep < 3 ? (
              <button
                onClick={handleNext}
                disabled={!canGoNext}
                className="
                  inline-flex items-center gap-1.5 px-6 py-2.5 rounded-lg text-sm font-medium
                  bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white
                  transition-colors duration-150 cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                Next
                <ChevronRight size={16} />
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={submitting}
                className="
                  inline-flex items-center gap-2 px-8 py-3 rounded-lg font-semibold text-lg
                  bg-[var(--color-cta)] hover:bg-[var(--color-cta-hover)] text-white
                  transition-colors duration-150 cursor-pointer
                  disabled:opacity-50
                "
              >
                {submitting ? (
                  <Loader2 size={20} className="animate-spin" />
                ) : (
                  <Play size={20} />
                )}
                {submitting ? "Starting..." : "Start Translation"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
