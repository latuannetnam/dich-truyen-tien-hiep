# Dịch Truyện — Web UI

Giao diện web cho Dịch Truyện, xây dựng với Next.js, TypeScript, và Tailwind CSS.

## Tính năng

- 📊 **Dashboard**: Tổng quan thống kê thư viện sách
- 📚 **Library**: Duyệt sách với card hiển thị tiến độ dịch
- 📖 **Book Detail**: Xem chi tiết sách, trạng thái từng chương
- 📕 **Chapter Reader**: Đọc bản dịch với chế độ song ngữ (side-by-side), điều chỉnh cỡ chữ, điều hướng bàn phím

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
│   ├── page.tsx            # Dashboard
│   ├── library/page.tsx    # Book library
│   ├── books/[id]/
│   │   ├── page.tsx        # Book detail
│   │   └── read/page.tsx   # Chapter reader
│   ├── layout.tsx          # Root layout
│   └── globals.css         # Design system tokens
├── components/
│   ├── layout/             # Sidebar, LayoutWrapper
│   ├── library/            # BookCard, BookCardSkeleton
│   ├── book/               # ChapterTable
│   ├── reader/             # ReaderView
│   └── dashboard/          # StatCard
└── lib/
    ├── api.ts              # API client
    └── types.ts            # TypeScript interfaces
```

## API Proxy

Requests đến `/api/*` được proxy sang `http://127.0.0.1:8000/api/*` qua cấu hình `next.config.ts`.
