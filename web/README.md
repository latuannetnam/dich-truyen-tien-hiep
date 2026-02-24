# Dịch Truyện — Web UI

Giao diện web cho Dịch Truyện, xây dựng với Next.js, TypeScript, và Tailwind CSS.

## Tính năng

- 📊 **Dashboard**: Tổng quan thống kê thư viện sách, hiển thị active jobs đang chạy
- 📚 **Library**: Duyệt sách với card hiển thị tiến độ dịch
- 📖 **Book Detail**: Xem chi tiết sách, trạng thái từng chương
- 📕 **Chapter Reader**: Đọc bản dịch với chế độ song ngữ (side-by-side), điều chỉnh cỡ chữ, điều hướng bàn phím
- 🚀 **New Translation**: Wizard 3 bước để bắt đầu dịch mới (URL → Options → Start)
- 📡 **Pipeline Monitor**: Theo dõi tiến trình dịch real-time qua WebSocket (progress, workers, event log)

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
│   │   └── read/page.tsx   # Chapter reader
│   ├── new/page.tsx        # New Translation wizard (3-step)
│   ├── pipeline/
│   │   └── [jobId]/page.tsx # Pipeline monitor (real-time WebSocket)
│   ├── layout.tsx          # Root layout
│   └── globals.css         # Design system tokens
├── components/
│   ├── layout/             # Sidebar, LayoutWrapper
│   ├── library/            # BookCard, BookCardSkeleton
│   ├── book/               # ChapterTable
│   ├── reader/             # ReaderView
│   ├── dashboard/          # StatCard, ActiveJobs
│   ├── pipeline/           # ProgressPanel, WorkerCards, EventLog
│   └── wizard/             # WizardSteps
├── hooks/
│   └── useWebSocket.ts     # Pipeline WebSocket hook
└── lib/
    ├── api.ts              # API client (books + pipeline)
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
| POST | `/api/v1/pipeline/start` | Start pipeline job |
| GET | `/api/v1/pipeline/jobs` | List all jobs |
| GET | `/api/v1/pipeline/jobs/:id` | Get job status |
| POST | `/api/v1/pipeline/jobs/:id/cancel` | Cancel job |

### WebSocket

`ws://localhost:8000/ws/pipeline/{jobId}` — Real-time pipeline events (progress, chapter status, worker updates).

