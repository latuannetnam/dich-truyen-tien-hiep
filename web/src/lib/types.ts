/** Book summary for list view. */
export interface BookSummary {
  id: string;
  title: string;
  title_vi: string;
  author: string;
  author_vi: string;
  url: string;
  total_chapters: number;
  pending_chapters: number;
  crawled_chapters: number;
  translated_chapters: number;
  formatted_chapters: number;
  exported_chapters: number;
  error_chapters: number;
  created_at: string | null;
  updated_at: string | null;
}

/** Chapter info for book detail view. */
export interface ChapterDetail {
  index: number;
  id: string;
  title_cn: string;
  title_vi: string | null;
  status: string;
  has_raw: boolean;
  has_translated: boolean;
}

/** Full book detail. */
export interface BookDetail {
  id: string;
  title: string;
  title_vi: string;
  author: string;
  author_vi: string;
  url: string;
  encoding: string;
  chapters: ChapterDetail[];
  created_at: string | null;
  updated_at: string | null;
}

/** Chapter text content. */
export interface ChapterContent {
  chapter_index: number;
  content: string;
}

/** Pipeline job. */
export interface PipelineJob {
  id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  url: string | null;
  book_dir: string | null;
  style: string;
  workers: number;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  progress: PipelineProgress;
  error: string | null;
}

/** Pipeline progress stats. */
export interface PipelineProgress {
  total_chapters: number;
  crawled: number;
  translated: number;
  errors: number;
  worker_status?: Record<string, string>;
  glossary_count?: number;
}

/** WebSocket pipeline event. */
export interface PipelineEventMessage {
  type: string;
  data: Record<string, unknown>;
  job_id: string;
  timestamp: number;
}

/** Start pipeline request. */
export interface StartPipelineRequest {
  url?: string;
  book_dir?: string;
  style?: string;
  workers?: number;
  chapters?: string;
  crawl_only?: boolean;
  translate_only?: boolean;
  no_glossary?: boolean;
  force?: boolean;
}

/** Book with incomplete translation, available for resume. */
export interface ResumableBook {
  book_dir: string;
  book_id: string;
  title: string;
  title_vi: string;
  total_chapters: number;
  translated: number;
  crawled: number;
  pending: number;
  errors: number;
  last_settings: Partial<StartPipelineRequest> | null;
  last_run_at: string | null;
}

/** Application settings. */
export interface AppSettings {
  llm: {
    api_key: string;
    base_url: string;
    model: string;
    max_tokens: number;
    temperature: number;
  };
  crawler: {
    delay_ms: number;
    max_retries: number;
    timeout_seconds: number;
    user_agent: string;
  };
  translation: {
    chunk_size: number;
    chunk_overlap: number;
    progressive_glossary: boolean;
    enable_glossary_annotation: boolean;
    enable_state_tracking: boolean;
    state_tracking_max_retries: number;
    glossary_sample_chapters: number;
    glossary_sample_size: number;
    glossary_min_entries: number;
    glossary_max_entries: number;
    glossary_random_sample: boolean;
    enable_polish_pass: boolean;
    polish_temperature: number;
    polish_max_retries: number;
  };
  pipeline: {
    translator_workers: number;
    queue_size: number;
    crawl_delay_ms: number;
    glossary_wait_timeout: number;
    glossary_batch_interval: number;
    glossary_scorer_rebuild_threshold: number;
  };
  export: {
    parallel_workers: number;
    volume_size: number;
    fast_mode: boolean;
  };
  calibre: {
    path: string;
  };
  crawler_llm: TaskLLMConfig;
  glossary_llm: TaskLLMConfig;
  translator_llm: TaskLLMConfig;
  _descriptions: FieldDescriptions;
}

/** Nested map of section → field → description string. */
export type FieldDescriptions = Record<string, Record<string, string>>;

/** Task-specific LLM override config. */
export interface TaskLLMConfig {
  api_key: string;
  base_url: string;
  model: string;
  max_tokens: number;
  temperature: number;
}

/** Test connection result. */
export interface TestConnectionResult {
  success: boolean;
  message: string;
}

/** Glossary entry. */
export interface GlossaryEntryType {
  chinese: string;
  vietnamese: string;
  category: string;
  notes: string | null;
}

/** Glossary response. */
export interface GlossaryResponseType {
  entries: GlossaryEntryType[];
  total: number;
  categories: string[];
}

/** Style template summary. */
export interface StyleSummary {
  name: string;
  description: string;
  tone: string;
  is_builtin: boolean;
  style_type: "builtin" | "custom" | "shadow";
}

/** Full style template. */
export interface StyleDetail {
  name: string;
  description: string;
  guidelines: string[];
  vocabulary: Record<string, string>;
  tone: string;
  examples: { chinese: string; vietnamese: string }[];
}

/** Export status for a book. */
export interface ExportStatus {
  formats: Record<string, string>;
}
