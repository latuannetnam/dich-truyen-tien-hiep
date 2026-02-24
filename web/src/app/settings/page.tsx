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
} from "lucide-react";
import { getSettings, updateSettings, testConnection } from "@/lib/api";
import type { AppSettings } from "@/lib/types";
import { useToast } from "@/components/ui/ToastProvider";

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
      <p className="text-[var(--text-secondary)] mb-8">
        Configure application settings
      </p>

      <div className="space-y-6 max-w-4xl">
        {/* API Configuration */}
        <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            API Configuration
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* API Key */}
            <div className="md:col-span-2">
              <label
                htmlFor="apiKey"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                API Key
              </label>
              <div className="relative">
                <input
                  id="apiKey"
                  type={showApiKey ? "text" : "password"}
                  value={settings.llm.api_key}
                  onChange={(e) => updateField("llm", "api_key", e.target.value)}
                  className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150 pr-12"
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

            {/* Base URL */}
            <div className="md:col-span-2">
              <label
                htmlFor="baseUrl"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Base URL
              </label>
              <input
                id="baseUrl"
                type="url"
                value={settings.llm.base_url}
                onChange={(e) => updateField("llm", "base_url", e.target.value)}
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>

            {/* Model */}
            <div>
              <label
                htmlFor="model"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Model
              </label>
              <input
                id="model"
                type="text"
                value={settings.llm.model}
                onChange={(e) => updateField("llm", "model", e.target.value)}
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>

            {/* Max Tokens */}
            <div>
              <label
                htmlFor="maxTokens"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Max Tokens
              </label>
              <input
                id="maxTokens"
                type="number"
                value={settings.llm.max_tokens}
                onChange={(e) =>
                  updateField("llm", "max_tokens", parseInt(e.target.value) || 0)
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>

            {/* Temperature */}
            <div>
              <label
                htmlFor="temperature"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Temperature
              </label>
              <input
                id="temperature"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={settings.llm.temperature}
                onChange={(e) =>
                  updateField(
                    "llm",
                    "temperature",
                    parseFloat(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>

            {/* Test Connection */}
            <div className="md:col-span-2 flex items-center gap-3">
              <button
                onClick={handleTestConnection}
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
                    testResult.success
                      ? "text-[#10B981]"
                      : "text-[#EF4444]"
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
          </div>
        </section>

        {/* Crawler Settings */}
        <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            Crawler Settings
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label
                htmlFor="crawlerDelay"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Delay (ms)
              </label>
              <input
                id="crawlerDelay"
                type="number"
                value={settings.crawler.delay_ms}
                onChange={(e) =>
                  updateField("crawler", "delay_ms", parseInt(e.target.value) || 0)
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="crawlerTimeout"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Timeout (s)
              </label>
              <input
                id="crawlerTimeout"
                type="number"
                value={settings.crawler.timeout_seconds}
                onChange={(e) =>
                  updateField(
                    "crawler",
                    "timeout_seconds",
                    parseInt(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="crawlerRetries"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Max Retries
              </label>
              <input
                id="crawlerRetries"
                type="number"
                value={settings.crawler.max_retries}
                onChange={(e) =>
                  updateField(
                    "crawler",
                    "max_retries",
                    parseInt(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
          </div>
        </section>

        {/* Translation Settings */}
        <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            Translation Settings
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="chunkSize"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Chunk Size
              </label>
              <input
                id="chunkSize"
                type="number"
                value={settings.translation.chunk_size}
                onChange={(e) =>
                  updateField(
                    "translation",
                    "chunk_size",
                    parseInt(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="chunkOverlap"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Overlap
              </label>
              <input
                id="chunkOverlap"
                type="number"
                value={settings.translation.chunk_overlap}
                onChange={(e) =>
                  updateField(
                    "translation",
                    "chunk_overlap",
                    parseInt(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="polishTemp"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Polish Temperature
              </label>
              <input
                id="polishTemp"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={settings.translation.polish_temperature}
                onChange={(e) =>
                  updateField(
                    "translation",
                    "polish_temperature",
                    parseFloat(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
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
        </section>

        {/* Pipeline Settings */}
        <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            Pipeline Settings
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label
                htmlFor="pipelineWorkers"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Workers
              </label>
              <input
                id="pipelineWorkers"
                type="number"
                value={settings.pipeline.translator_workers}
                onChange={(e) =>
                  updateField(
                    "pipeline",
                    "translator_workers",
                    parseInt(e.target.value) || 1
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="queueSize"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Queue Size
              </label>
              <input
                id="queueSize"
                type="number"
                value={settings.pipeline.queue_size}
                onChange={(e) =>
                  updateField(
                    "pipeline",
                    "queue_size",
                    parseInt(e.target.value) || 1
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="crawlDelay"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Crawl Delay (ms)
              </label>
              <input
                id="crawlDelay"
                type="number"
                value={settings.pipeline.crawl_delay_ms}
                onChange={(e) =>
                  updateField(
                    "pipeline",
                    "crawl_delay_ms",
                    parseInt(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
          </div>
        </section>

        {/* Export Settings */}
        <section className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            Export Settings
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label
                htmlFor="exportWorkers"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Parallel Workers
              </label>
              <input
                id="exportWorkers"
                type="number"
                value={settings.export.parallel_workers}
                onChange={(e) =>
                  updateField(
                    "export",
                    "parallel_workers",
                    parseInt(e.target.value) || 1
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div>
              <label
                htmlFor="volumeSize"
                className="text-[var(--text-secondary)] text-sm font-medium mb-2 block"
              >
                Volume Size
              </label>
              <input
                id="volumeSize"
                type="number"
                min="0"
                value={settings.export.volume_size}
                onChange={(e) =>
                  updateField(
                    "export",
                    "volume_size",
                    parseInt(e.target.value) || 0
                  )
                }
                className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-[var(--text-primary)] w-full focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]/20 outline-none transition-all duration-150"
              />
            </div>
            <div className="flex items-end pb-1">
              <CheckboxField
                label="Fast Mode"
                checked={settings.export.fast_mode}
                onChange={(v) => updateField("export", "fast_mode", v)}
              />
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-2 bg-transparent border border-[var(--border-default)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] rounded-lg px-6 py-2.5 font-medium transition-colors cursor-pointer"
          >
            <RotateCcw size={16} aria-hidden="true" />
            Reset to Defaults
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
