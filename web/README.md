# Dịch Truyện — Web UI

Giao diện web cho Dịch Truyện, xây dựng với Next.js, TypeScript, và Tailwind CSS.

## Tính năng

### 📊 Dashboard

Tổng quan thống kê thư viện sách, hiển thị active jobs đang chạy và sách gần đây.

<!-- TODO: Add screenshot -->
<!-- ![Dashboard](docs/screenshots/dashboard.png) -->

### 📚 Library

Duyệt sách với card hiển thị tiến độ dịch.

<!-- TODO: Add screenshot -->
<!-- ![Library](docs/screenshots/library.png) -->

### 📖 Book Detail

Xem chi tiết sách, trạng thái từng chương, điều khiển export, liên kết đến glossary editor.

<!-- TODO: Add screenshot -->
<!-- ![Book Detail](docs/screenshots/book-detail.png) -->

### 📕 Chapter Reader

Đọc bản dịch với nhiều tính năng:
- **Chế độ song ngữ**: Hiển thị bản gốc và bản dịch song song, tự động căn chỉnh theo đoạn
- **Cuộn đồng bộ**: Khi cuộn một bên, bên kia tự động cuộn theo tỉ lệ
- **Chọn chương nhanh**: Dropdown chuyển chương trực tiếp
- **Lưu tiến trình đọc**: Tự động lưu chương đang đọc, tiếp tục từ nơi dừng lại
- **Font size**: Điều chỉnh cỡ chữ, tự lưu preference
- **Điều hướng bàn phím**: Nhấn ← → để chuyển chương

<!-- TODO: Add screenshot -->
<!-- ![Reader - Side by Side](docs/screenshots/reader-side-by-side.png) -->

### ⚙️ Settings

Cấu hình ứng dụng trực tiếp trên giao diện web:
- **API Configuration**: API key, base URL, model, max tokens, temperature
- **Crawler Settings**: Delay, timeout, retries
- **Translation Settings**: Chunk size, overlap, polish pass, progressive glossary
- **Pipeline Settings**: Workers, queue size, crawl delay
- **Export Settings**: Parallel workers, volume size, fast mode
- **Test Connection**: Kiểm tra kết nối API ngay trên giao diện

<!-- TODO: Add screenshot -->
<!-- ![Settings](docs/screenshots/settings.png) -->

### 📝 Glossary Editor

Quản lý glossary trực tiếp trên giao diện, mỗi sách có glossary riêng:
- **Inline editing**: Sửa trực tiếp trên bảng, thêm/xóa entry
- **Tìm kiếm & lọc**: Tìm theo tiếng Trung/Việt, lọc theo category
- **Category badges**: Nhân vật, cảnh giới, kỹ thuật, địa điểm, vật phẩm, tổ chức
- **Import/Export CSV**: Import glossary từ file CSV hoặc export ra CSV

<!-- TODO: Add screenshot -->
<!-- ![Glossary Editor](docs/screenshots/glossary-editor.png) -->

### 🎨 Style Manager

Quản lý đầy đủ style templates (CRUD + LLM generation + import/export):
- **Card grid**: Hiển thị tên, mô tả, tone badge, type badge (built-in/custom/customized)
- **Detail panel**: Slide-in panel hiển thị guidelines, vocabulary, examples
- **Create/Edit**: Form tạo mới hoặc chỉnh sửa style với inline validation
- **Customize built-in**: Shadow built-in styles với customizations riêng
- **AI Generation**: Tạo style từ mô tả bằng LLM (✨ Generate with AI)
- **Import/Export YAML**: Import file YAML (validate → review → save), export bất kỳ style
- **Search/filter**: Tìm kiếm theo tên, mô tả, tone
- **Accessibility**: Focus trap, aria-live validation, keyboard shortcuts (Escape, Ctrl+S)

<!-- TODO: Add screenshot -->
<!-- ![Style Manager](docs/screenshots/style-manager.png) -->

### 📦 Export Controls

Điều khiển export trực tiếp từ Book Detail:
- **Format selector**: epub, azw3, mobi, pdf
- **Export button**: Bắt đầu export với loading spinner
- **Download links**: Tải file đã export
- **Toast feedback**: Thông báo thành công/lỗi

### ✨ Animations & Error Handling

- **CSS animations**: fadeIn, slideInRight, slideInUp, pulse, spin với staggered children
- **`prefers-reduced-motion`**: Tự động tắt animation cho người dùng nhạy cảm
- **ErrorBoundary**: Bắt lỗi global với nút retry
- **EmptyState**: Component tái sử dụng cho trạng thái trống (chapters, glossary)

### 🚀 New Translation

Wizard 3 bước để bắt đầu dịch mới (URL → Options → Start).

<!-- TODO: Add screenshot -->
<!-- ![New Translation Wizard](docs/screenshots/new-translation.png) -->

### 📡 Pipeline Monitor

Theo dõi tiến trình dịch real-time qua WebSocket:
- **Progress panel**: Thanh tiến trình tổng thể
- **Worker cards**: Trạng thái từng worker
- **Event log**: Nhật ký sự kiện chi tiết

<!-- TODO: Add screenshot -->
<!-- ![Pipeline Monitor](docs/screenshots/pipeline-monitor.png) -->

### 🔄 Resumable Pipeline

Phát hiện sách dịch dang dở và tiếp tục dịch sau khi khởi động lại:
- **Resumable Books section**: Hiển thị trên trang Pipeline với progress bar và status badges
- **Resume banner**: Banner cảnh báo trên Book Detail khi sách chưa dịch xong
- **Options form**: Mở rộng inline form để tuỳ chỉnh style, workers, chapters trước khi resume
- **Auto-detect**: Quét `books/` khi khởi động, tự tạo settings mặc định cho sách từ CLI
- **Pre-fill settings**: Tự điền settings từ lần chạy trước (`last_pipeline_settings.json`)

<!-- TODO: Add screenshot -->
<!-- ![Resumable Pipeline](docs/screenshots/resumable-pipeline.png) -->

## Bắt đầu

### Yêu cầu

- Node.js 18+
- API server đang chạy (`uv run dich-truyen ui --no-browser`)

### Cài đặt

```bash
npm install
```

### Chạy dev server

```bash
# Chạy API server trước (terminal riêng)
cd .. && uv run dich-truyen ui --no-browser --port 8000

# Chạy frontend
npm run dev
```

Mở [http://localhost:3000](http://localhost:3000).

### Build production

```bash
npm run build
npm start
```

### Lint

```bash
npm run lint
```

## Cấu trúc

```
src/
├── app/                    # App Router pages
│   ├── page.tsx            # Dashboard (stats + active jobs + recent books)
│   ├── library/page.tsx    # Book library
│   ├── books/[id]/
│   │   ├── page.tsx        # Book detail
│   │   ├── read/page.tsx   # Chapter reader
│   │   └── glossary/page.tsx # Glossary editor
│   ├── new/page.tsx        # New Translation wizard (3-step)
│   ├── settings/page.tsx   # Application settings
│   ├── pipeline/
│   │   ├── page.tsx       # Pipeline job list
│   │   └── [jobId]/page.tsx # Pipeline monitor (real-time WebSocket)
│   ├── styles/page.tsx    # Style Manager
│   ├── layout.tsx          # Root layout
│   └── globals.css         # Design system tokens + animations
├── components/
│   ├── layout/             # Sidebar, LayoutWrapper
│   ├── library/            # BookCard, BookCardSkeleton
│   ├── book/               # ChapterTable, ResumeBanner
│   ├── reader/             # ReaderView (paragraph-aligned side-by-side)
│   ├── glossary/           # GlossaryEditor (inline CRUD, search, CSV import/export)
│   ├── dashboard/          # StatCard, ActiveJobs
│   ├── pipeline/           # ProgressPanel, WorkerCards, EventLog, ResumableSection
│   ├── wizard/             # WizardSteps
│   ├── styles/            # StyleEditorForm, ConfirmDialog
│   └── ui/                 # ToastProvider, ErrorBoundary, EmptyState
├── hooks/
│   ├── useWebSocket.ts     # Pipeline WebSocket hook
│   └── useFocusTrap.ts     # Focus trap for modal panels
└── lib/
    ├── api.ts              # API client (books, pipeline, settings, glossary, styles, export)
    └── types.ts            # TypeScript interfaces
```

## API

### REST Endpoints (via proxy)

Requests đến `/api/*` được proxy sang `http://127.0.0.1:8000/api/*` qua cấu hình `next.config.ts`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/books` | List books |
| GET | `/api/v1/books/:id` | Book detail |
| GET | `/api/v1/books/:id/chapters/:num/raw` | Raw chapter |
| GET | `/api/v1/books/:id/chapters/:num/translated` | Translated chapter |
| GET | `/api/v1/books/:id/glossary` | Get glossary entries |
| POST | `/api/v1/books/:id/glossary` | Add glossary entry |
| PUT | `/api/v1/books/:id/glossary/:term` | Update glossary entry |
| DELETE | `/api/v1/books/:id/glossary/:term` | Delete glossary entry |
| GET | `/api/v1/books/:id/glossary/export` | Export glossary CSV |
| POST | `/api/v1/books/:id/glossary/import` | Import glossary CSV |
| POST | `/api/v1/pipeline/start` | Start pipeline job |
| GET | `/api/v1/pipeline/resumable` | List incomplete books for resume |
| GET | `/api/v1/pipeline/jobs` | List all jobs |
| GET | `/api/v1/pipeline/jobs/:id` | Get job status |
| POST | `/api/v1/pipeline/jobs/:id/cancel` | Cancel job |
| GET | `/api/v1/settings` | Get app settings |
| PUT | `/api/v1/settings` | Update app settings |
| POST | `/api/v1/settings/test-connection` | Test API connection |
| GET | `/api/v1/styles` | List styles |
| GET | `/api/v1/styles/:name` | Get style detail |
| POST | `/api/v1/styles` | Create new custom style |
| PUT | `/api/v1/styles/:name` | Update custom style |
| DELETE | `/api/v1/styles/:name` | Delete custom style |
| POST | `/api/v1/styles/:name/duplicate` | Duplicate/shadow style |
| POST | `/api/v1/styles/generate` | LLM-generate style (not saved) |
| POST | `/api/v1/styles/import` | Validate YAML import (not saved) |
| GET | `/api/v1/styles/:name/export` | Export as YAML download |
| GET | `/api/v1/export/formats` | Supported export formats |
| GET | `/api/v1/books/:id/export` | Export status |
| POST | `/api/v1/books/:id/export` | Start export |
| GET | `/api/v1/books/:id/export/download/:file` | Download export |

### WebSocket

`ws://localhost:8000/ws/pipeline/{jobId}` — Real-time pipeline events (progress, chapter status, worker updates).
