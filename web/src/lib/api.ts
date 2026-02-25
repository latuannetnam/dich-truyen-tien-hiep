import type {
  BookSummary,
  BookDetail,
  ChapterContent,
  PipelineJob,
  StartPipelineRequest,
  AppSettings,
  TestConnectionResult,
  GlossaryResponseType,
  GlossaryEntryType,
  StyleSummary,
  StyleDetail,
  ExportStatus,
} from "./types";

const API_BASE = "/api/v1";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getBooks(): Promise<BookSummary[]> {
  return fetchJson<BookSummary[]>(`${API_BASE}/books`);
}

export async function getBook(id: string): Promise<BookDetail> {
  return fetchJson<BookDetail>(`${API_BASE}/books/${id}`);
}

export async function getChapterRaw(
  bookId: string,
  chapterNum: number
): Promise<ChapterContent> {
  return fetchJson<ChapterContent>(
    `${API_BASE}/books/${bookId}/chapters/${chapterNum}/raw`
  );
}

export async function getChapterTranslated(
  bookId: string,
  chapterNum: number
): Promise<ChapterContent> {
  return fetchJson<ChapterContent>(
    `${API_BASE}/books/${bookId}/chapters/${chapterNum}/translated`
  );
}

export async function startPipeline(
  request: StartPipelineRequest
): Promise<PipelineJob> {
  const res = await fetch(`${API_BASE}/pipeline/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function getPipelineJobs(): Promise<PipelineJob[]> {
  return fetchJson<PipelineJob[]>(`${API_BASE}/pipeline/jobs`);
}

export async function getPipelineJob(jobId: string): Promise<PipelineJob> {
  return fetchJson<PipelineJob>(`${API_BASE}/pipeline/jobs/${jobId}`);
}

export async function cancelPipelineJob(jobId: string): Promise<PipelineJob> {
  const res = await fetch(`${API_BASE}/pipeline/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// --- Settings API ---

export async function getSettings(): Promise<AppSettings> {
  return fetchJson<AppSettings>(`${API_BASE}/settings`);
}

export async function updateSettings(
  settings: Partial<AppSettings>
): Promise<AppSettings> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function testConnection(): Promise<TestConnectionResult> {
  const res = await fetch(`${API_BASE}/settings/test-connection`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// --- Glossary API ---

export async function getGlossary(bookId: string): Promise<GlossaryResponseType> {
  return fetchJson<GlossaryResponseType>(`${API_BASE}/books/${bookId}/glossary`);
}

export async function addGlossaryEntry(
  bookId: string,
  entry: Omit<GlossaryEntryType, "notes"> & { notes?: string }
): Promise<void> {
  const res = await fetch(`${API_BASE}/books/${bookId}/glossary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function updateGlossaryEntry(
  bookId: string,
  term: string,
  entry: Omit<GlossaryEntryType, "notes"> & { notes?: string }
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/books/${bookId}/glossary/${encodeURIComponent(term)}`,
    { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(entry) }
  );
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function deleteGlossaryEntry(bookId: string, term: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/books/${bookId}/glossary/${encodeURIComponent(term)}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function importGlossaryCsv(bookId: string, file: File): Promise<{imported: number}> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/books/${bookId}/glossary/import`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// For export, use the raw URL: `${API_BASE}/books/${bookId}/glossary/export`
export function getGlossaryExportUrl(bookId: string): string {
  return `${API_BASE}/books/${bookId}/glossary/export`;
}

// --- Styles API ---

export async function getStyles(): Promise<StyleSummary[]> {
  return fetchJson<StyleSummary[]>(`${API_BASE}/styles`);
}

export async function getStyle(name: string): Promise<StyleDetail> {
  return fetchJson<StyleDetail>(`${API_BASE}/styles/${name}`);
}

// --- Export API ---

export async function getExportStatus(bookId: string): Promise<ExportStatus> {
  return fetchJson<ExportStatus>(`${API_BASE}/books/${bookId}/export`);
}

export async function startExport(
  bookId: string,
  format: string
): Promise<{ success: boolean; output_path?: string; error_message?: string }> {
  const res = await fetch(`${API_BASE}/books/${bookId}/export?format=${format}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function getExportDownloadUrl(bookId: string, filename: string): string {
  return `${API_BASE}/books/${bookId}/export/download/${filename}`;
}
