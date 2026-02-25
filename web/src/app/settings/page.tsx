"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Eye,
  EyeOff,
  Save,
  RotateCcw,
  Loader2,
  CheckCircle,
  XCircle,
  Zap,
  Settings as SettingsIcon,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { getSettings, updateSettings, testConnection } from "@/lib/api";
import type { AppSettings, TaskLLMConfig } from "@/lib/types";
import { useToast } from "@/components/ui/ToastProvider";

type Tab = "basic" | "advanced";

export default function SettingsPage() {
  const { showSuccess, showError } = useToast();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("basic");

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getSettings();
      setSettings(data);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      showSuccess("Settings saved successfully");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    loadSettings();
    setTestResult(null);
    showSuccess("Settings reloaded from server");
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testConnection();
      setTestResult(result);
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : "Connection failed",
      });
    } finally {
      setTesting(false);
    }
  };

  const updateField = <S extends keyof AppSettings>(
    section: S,
    key: keyof AppSettings[S],
    value: string | number | boolean
  ) => {
    if (!settings) return;
    setSettings({
      ...settings,
      [section]: { ...settings[section], [key]: value },
    });
  };

  if (loading || !settings) {
    return (
      <div>
        <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)] mb-2">
          Settings
        </h1>
        <p className="text-[var(--text-secondary)] mb-8">
          Configure application settings
        </p>
        <div className="space-y-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6 animate-pulse"
            >
              <div className="h-6 bg-[var(--bg-elevated)] rounded w-48 mb-4" />
              <div className="grid grid-cols-2 gap-4">
                <div className="h-10 bg-[var(--bg-elevated)] rounded" />
                <div className="h-10 bg-[var(--bg-elevated)] rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-2">
        <SettingsIcon
          size={28}
          className="text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <h1 className="font-[var(--font-fira-code)] text-3xl font-bold text-[var(--text-primary)]">
          Settings
        </h1>
      </div>
      <p className="text-[var(--text-secondary)] mb-6">
        Configure application settings
      </p>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab("basic")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "basic"
              ? "bg-[var(--color-primary)] text-white"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          Basic
        </button>
        <button
          onClick={() => setActiveTab("advanced")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "advanced"
              ? "bg-[var(--color-primary)] text-white"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          Advanced
        </button>
      </div>

      <div className="space-y-6 max-w-4xl">
        {activeTab === "basic" ? (
          <BasicSettings
            settings={settings}
            updateField={updateField}
            showApiKey={showApiKey}
            setShowApiKey={setShowApiKey}
            testing={testing}
            testResult={testResult}
            onTestConnection={handleTestConnection}
          />
        ) : (
          <AdvancedSettings settings={settings} updateField={updateField} />
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-2 bg-transparent border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-6 py-2.5 font-medium transition-colors cursor-pointer"
          >
            <RotateCcw size={16} aria-hidden="true" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg px-6 py-2.5 font-medium transition-colors cursor-pointer disabled:opacity-50"
          >
            {saving ? (
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <Save size={16} aria-hidden="true" />
            )}
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Basic Settings ────────────────────────────────────────── */

function BasicSettings({
  settings,
  updateField,
  showApiKey,
  setShowApiKey,
  testing,
  testResult,
  onTestConnection,
}: {
  settings: AppSettings;
  updateField: <S extends keyof AppSettings>(
    s: S,
    k: keyof AppSettings[S],
    v: string | number | boolean
  ) => void;
  showApiKey: boolean;
  setShowApiKey: (v: boolean) => void;
  testing: boolean;
  testResult: { success: boolean; message: string } | null;
  onTestConnection: () => void;
}) {
  return (
    <>
      {/* API Configuration */}
      <Section title="API Configuration">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <Label htmlFor="apiKey">API Key</Label>
            <div className="relative">
              <input
                id="apiKey"
                type={showApiKey ? "text" : "password"}
                value={settings.llm.api_key}
                onChange={(e) => updateField("llm", "api_key", e.target.value)}
                className={inputClass + " pr-12"}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors cursor-pointer"
                aria-label={showApiKey ? "Hide API key" : "Show API key"}
              >
                {showApiKey ? (
                  <EyeOff size={18} aria-hidden="true" />
                ) : (
                  <Eye size={18} aria-hidden="true" />
                )}
              </button>
            </div>
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="baseUrl">Base URL</Label>
            <input
              id="baseUrl"
              type="url"
              value={settings.llm.base_url}
              onChange={(e) => updateField("llm", "base_url", e.target.value)}
              className={inputClass}
            />
          </div>
          <NumberField
            id="model"
            label="Model"
            type="text"
            value={settings.llm.model}
            onChange={(v) => updateField("llm", "model", v)}
          />
          <NumberField
            id="maxTokens"
            label="Max Tokens"
            value={settings.llm.max_tokens}
            onChange={(v) => updateField("llm", "max_tokens", v)}
          />
          <NumberField
            id="temperature"
            label="Temperature"
            value={settings.llm.temperature}
            onChange={(v) => updateField("llm", "temperature", v)}
            step={0.1}
            min={0}
            max={2}
          />
          <div className="flex items-end pb-1">
            <TestConnectionButton
              testing={testing}
              testResult={testResult}
              onClick={onTestConnection}
            />
          </div>
        </div>
      </Section>

      {/* Crawler */}
      <Section title="Crawler Settings">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <NumberField
            id="crawlerDelay"
            label="Delay (ms)"
            value={settings.crawler.delay_ms}
            onChange={(v) => updateField("crawler", "delay_ms", v)}
          />
          <NumberField
            id="crawlerTimeout"
            label="Timeout (s)"
            value={settings.crawler.timeout_seconds}
            onChange={(v) => updateField("crawler", "timeout_seconds", v)}
          />
          <NumberField
            id="crawlerRetries"
            label="Max Retries"
            value={settings.crawler.max_retries}
            onChange={(v) => updateField("crawler", "max_retries", v)}
          />
        </div>
      </Section>

      {/* Translation (basic) */}
      <Section title="Translation Settings">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <NumberField
            id="chunkSize"
            label="Chunk Size"
            value={settings.translation.chunk_size}
            onChange={(v) => updateField("translation", "chunk_size", v)}
          />
          <NumberField
            id="chunkOverlap"
            label="Overlap"
            value={settings.translation.chunk_overlap}
            onChange={(v) => updateField("translation", "chunk_overlap", v)}
          />
          <NumberField
            id="polishTemp"
            label="Polish Temperature"
            value={settings.translation.polish_temperature}
            onChange={(v) => updateField("translation", "polish_temperature", v)}
            step={0.1}
            min={0}
            max={2}
          />
          <div className="flex items-end gap-6 pb-1">
            <CheckboxField
              label="Polish Pass"
              checked={settings.translation.enable_polish_pass}
              onChange={(v) =>
                updateField("translation", "enable_polish_pass", v)
              }
            />
            <CheckboxField
              label="Progressive Glossary"
              checked={settings.translation.progressive_glossary}
              onChange={(v) =>
                updateField("translation", "progressive_glossary", v)
              }
            />
          </div>
        </div>
      </Section>

      {/* Pipeline */}
      <Section title="Pipeline Settings">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <NumberField
            id="pipelineWorkers"
            label="Workers"
            value={settings.pipeline.translator_workers}
            onChange={(v) => updateField("pipeline", "translator_workers", v)}
            min={1}
          />
          <NumberField
            id="queueSize"
            label="Queue Size"
            value={settings.pipeline.queue_size}
            onChange={(v) => updateField("pipeline", "queue_size", v)}
          />
          <NumberField
            id="crawlDelay"
            label="Crawl Delay (ms)"
            value={settings.pipeline.crawl_delay_ms}
            onChange={(v) => updateField("pipeline", "crawl_delay_ms", v)}
          />
        </div>
      </Section>

      {/* Export */}
      <Section title="Export Settings">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <NumberField
            id="exportWorkers"
            label="Parallel Workers"
            value={settings.export.parallel_workers}
            onChange={(v) => updateField("export", "parallel_workers", v)}
            min={1}
          />
          <NumberField
            id="volumeSize"
            label="Volume Size"
            value={settings.export.volume_size}
            onChange={(v) => updateField("export", "volume_size", v)}
            min={0}
          />
          <div className="flex items-end pb-1">
            <CheckboxField
              label="Fast Mode"
              checked={settings.export.fast_mode}
              onChange={(v) => updateField("export", "fast_mode", v)}
            />
          </div>
        </div>
      </Section>
    </>
  );
}

/* ─── Advanced Settings ─────────────────────────────────────── */

function AdvancedSettings({
  settings,
  updateField,
}: {
  settings: AppSettings;
  updateField: <S extends keyof AppSettings>(
    s: S,
    k: keyof AppSettings[S],
    v: string | number | boolean
  ) => void;
}) {
  return (
    <>
      {/* Crawler advanced */}
      <Section title="Crawler — Advanced">
        <div className="grid grid-cols-1 gap-4">
          <div>
            <Label htmlFor="userAgent">User Agent</Label>
            <input
              id="userAgent"
              type="text"
              value={settings.crawler.user_agent}
              onChange={(e) =>
                updateField("crawler", "user_agent", e.target.value)
              }
              className={inputClass}
            />
          </div>
        </div>
      </Section>

      {/* Translation advanced */}
      <Section title="Translation — Advanced">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-end gap-6 pb-1 md:col-span-2">
            <CheckboxField
              label="Glossary Annotation"
              checked={settings.translation.enable_glossary_annotation}
              onChange={(v) =>
                updateField("translation", "enable_glossary_annotation", v)
              }
            />
            <CheckboxField
              label="State Tracking"
              checked={settings.translation.enable_state_tracking}
              onChange={(v) =>
                updateField("translation", "enable_state_tracking", v)
              }
            />
            <CheckboxField
              label="Random Glossary Samples"
              checked={settings.translation.glossary_random_sample}
              onChange={(v) =>
                updateField("translation", "glossary_random_sample", v)
              }
            />
          </div>
          <NumberField
            id="stateMaxRetries"
            label="State Tracking Max Retries"
            value={settings.translation.state_tracking_max_retries}
            onChange={(v) =>
              updateField("translation", "state_tracking_max_retries", v)
            }
          />
          <NumberField
            id="polishMaxRetries"
            label="Polish Max Retries"
            value={settings.translation.polish_max_retries}
            onChange={(v) =>
              updateField("translation", "polish_max_retries", v)
            }
          />
          <NumberField
            id="glossarySampleChapters"
            label="Glossary Sample Chapters"
            value={settings.translation.glossary_sample_chapters}
            onChange={(v) =>
              updateField("translation", "glossary_sample_chapters", v)
            }
          />
          <NumberField
            id="glossarySampleSize"
            label="Glossary Sample Size"
            value={settings.translation.glossary_sample_size}
            onChange={(v) =>
              updateField("translation", "glossary_sample_size", v)
            }
          />
          <NumberField
            id="glossaryMinEntries"
            label="Glossary Min Entries"
            value={settings.translation.glossary_min_entries}
            onChange={(v) =>
              updateField("translation", "glossary_min_entries", v)
            }
          />
          <NumberField
            id="glossaryMaxEntries"
            label="Glossary Max Entries"
            value={settings.translation.glossary_max_entries}
            onChange={(v) =>
              updateField("translation", "glossary_max_entries", v)
            }
          />
        </div>
      </Section>

      {/* Pipeline advanced */}
      <Section title="Pipeline — Advanced">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <NumberField
            id="glossaryWaitTimeout"
            label="Glossary Wait Timeout (s)"
            value={settings.pipeline.glossary_wait_timeout}
            onChange={(v) =>
              updateField("pipeline", "glossary_wait_timeout", v)
            }
          />
          <NumberField
            id="glossaryBatchInterval"
            label="Glossary Batch Interval (s)"
            value={settings.pipeline.glossary_batch_interval}
            onChange={(v) =>
              updateField("pipeline", "glossary_batch_interval", v)
            }
          />
          <NumberField
            id="glossaryScorerRebuild"
            label="Scorer Rebuild Threshold"
            value={settings.pipeline.glossary_scorer_rebuild_threshold}
            onChange={(v) =>
              updateField("pipeline", "glossary_scorer_rebuild_threshold", v)
            }
          />
        </div>
      </Section>

      {/* Calibre */}
      <Section title="Calibre">
        <div className="grid grid-cols-1 gap-4">
          <div>
            <Label htmlFor="calibrePath">ebook-convert Path</Label>
            <input
              id="calibrePath"
              type="text"
              value={settings.calibre.path}
              onChange={(e) =>
                updateField("calibre", "path", e.target.value)
              }
              className={inputClass}
            />
          </div>
        </div>
      </Section>

      {/* Task-specific LLM overrides */}
      <TaskLLMSection
        title="Crawler LLM Override"
        description="Override the default LLM settings for the crawler. Leave empty to use defaults."
        sectionKey="crawler_llm"
        config={settings.crawler_llm}
        updateField={updateField}
      />
      <TaskLLMSection
        title="Glossary LLM Override"
        description="Override the default LLM settings for glossary generation. Leave empty to use defaults."
        sectionKey="glossary_llm"
        config={settings.glossary_llm}
        updateField={updateField}
      />
      <TaskLLMSection
        title="Translator LLM Override"
        description="Override the default LLM settings for translation. Leave empty to use defaults."
        sectionKey="translator_llm"
        config={settings.translator_llm}
        updateField={updateField}
      />
    </>
  );
}

/* ─── Reusable Components ──────────────────────────────────── */

const inputClass =
  "bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150 text-sm";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Label({
  htmlFor,
  children,
}: {
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
    >
      {children}
    </label>
  );
}

function NumberField({
  id,
  label,
  value,
  onChange,
  type = "number",
  step,
  min,
  max,
}: {
  id: string;
  label: string;
  value: number | string;
  onChange: (v: number | string) => void;
  type?: "number" | "text";
  step?: number;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <input
        id={id}
        type={type}
        step={step}
        min={min}
        max={max}
        value={value}
        onChange={(e) => {
          if (type === "text") {
            onChange(e.target.value);
          } else {
            onChange(
              step && step < 1
                ? parseFloat(e.target.value) || 0
                : parseInt(e.target.value) || 0
            );
          }
        }}
        className={inputClass}
      />
    </div>
  );
}

function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <div
        className={`
          w-5 h-5 rounded flex items-center justify-center
          transition-colors duration-150
          ${
            checked
              ? "bg-[var(--color-primary)] border-[var(--color-primary)]"
              : "bg-[var(--bg-surface)] border border-[var(--border-default)] group-hover:border-[var(--border-hover)]"
          }
        `}
      >
        {checked && (
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
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <span className="text-[var(--text-secondary)] text-sm">{label}</span>
    </label>
  );
}

function TestConnectionButton({
  testing,
  testResult,
  onClick,
}: {
  testing: boolean;
  testResult: { success: boolean; message: string } | null;
  onClick: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onClick}
        disabled={testing}
        className="inline-flex items-center gap-2 bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20 rounded-lg px-4 py-2 text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
      >
        {testing ? (
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
        ) : (
          <Zap size={16} aria-hidden="true" />
        )}
        Test Connection
      </button>
      {testResult && (
        <span
          className={`inline-flex items-center gap-1.5 text-sm ${
            testResult.success ? "text-[#10B981]" : "text-[#EF4444]"
          }`}
        >
          {testResult.success ? (
            <CheckCircle size={16} aria-hidden="true" />
          ) : (
            <XCircle size={16} aria-hidden="true" />
          )}
          {testResult.message}
        </span>
      )}
    </div>
  );
}

function TaskLLMSection({
  title,
  description,
  sectionKey,
  config,
  updateField,
}: {
  title: string;
  description: string;
  sectionKey: "crawler_llm" | "glossary_llm" | "translator_llm";
  config: TaskLLMConfig;
  updateField: <S extends keyof AppSettings>(
    s: S,
    k: keyof AppSettings[S],
    v: string | number | boolean
  ) => void;
  }) {
  const [expanded, setExpanded] = useState(false);
  const hasOverrides = !!(config.model || config.base_url || (config.api_key && !config.api_key.includes("••••••••")));

  return (
    <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-6 cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            {title}
          </h2>
          {hasOverrides && (
            <span className="px-2 py-0.5 bg-[var(--color-primary)]/10 text-[var(--color-primary)] text-xs rounded font-medium">
              Custom
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronDown size={18} className="text-[var(--text-muted)]" />
        ) : (
          <ChevronRight size={18} className="text-[var(--text-muted)]" />
        )}
      </button>
      {expanded && (
        <div className="px-6 pb-6 pt-0">
          <p className="text-[var(--text-muted)] text-sm mb-4">{description}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor={`${sectionKey}-apiKey`}>API Key</Label>
              <input
                id={`${sectionKey}-apiKey`}
                type="password"
                value={config.api_key}
                onChange={(e) =>
                  updateField(sectionKey, "api_key" as keyof AppSettings[typeof sectionKey], e.target.value)
                }
                placeholder="(use default)"
                className={inputClass}
              />
            </div>
            <div>
              <Label htmlFor={`${sectionKey}-baseUrl`}>Base URL</Label>
              <input
                id={`${sectionKey}-baseUrl`}
                type="text"
                value={config.base_url}
                onChange={(e) =>
                  updateField(sectionKey, "base_url" as keyof AppSettings[typeof sectionKey], e.target.value)
                }
                placeholder="(use default)"
                className={inputClass}
              />
            </div>
            <div>
              <Label htmlFor={`${sectionKey}-model`}>Model</Label>
              <input
                id={`${sectionKey}-model`}
                type="text"
                value={config.model}
                onChange={(e) =>
                  updateField(sectionKey, "model" as keyof AppSettings[typeof sectionKey], e.target.value)
                }
                placeholder="(use default)"
                className={inputClass}
              />
            </div>
            <NumberField
              id={`${sectionKey}-maxTokens`}
              label="Max Tokens"
              value={config.max_tokens}
              onChange={(v) =>
                updateField(sectionKey, "max_tokens" as keyof AppSettings[typeof sectionKey], v)
              }
            />
            <NumberField
              id={`${sectionKey}-temperature`}
              label="Temperature"
              value={config.temperature}
              onChange={(v) =>
                updateField(sectionKey, "temperature" as keyof AppSettings[typeof sectionKey], v)
              }
              step={0.1}
              min={0}
              max={2}
            />
          </div>
        </div>
      )}
    </section>
  );
}
