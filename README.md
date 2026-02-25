# Dịch Truyện - Công Cụ Dịch Truyện Trung Quốc

> **Ngôn ngữ:** [English](README.en.md) | [Tiếng Việt](README.md)

Công cụ dòng lệnh và giao diện web để crawl, dịch và xuất truyện Trung Quốc sang ebook tiếng Việt.

## Tính Năng

### Tính Năng Chính

- 🕷️ **Crawler Thông Minh**: Sử dụng LLM để tự động phát hiện cấu trúc chương từ các website truyện Trung Quốc
- 🌐 **Công Cụ Dịch**: Dịch từ tiếng Trung sang tiếng Việt với các style template có thể tùy chỉnh
- 📖 **4 Style Có Sẵn**: Tiên hiệp, Kiếm hiệp, Huyền huyễn, Đô thị
- 📚 **Hệ Thống Glossary**: Duy trì thuật ngữ nhất quán (import/export CSV)
- 📕 **Xuất Ebook**: Chuyển đổi sang EPUB, AZW3, MOBI, PDF qua Calibre
- 🔄 **Hoạt Động Tiếp Tục Được**: Tiếp tục download/dịch khi bị gián đoạn
- ⚡ **Pipeline Streaming**: Crawl và dịch đồng thời với đa worker
- 🖥️ **[Giao Diện Web](web/README.md)**: Duyệt thư viện, đọc song ngữ, quản lý glossary, cấu hình settings, và theo dõi tiến trình real-time

### Kỹ Thuật Nâng Cao

| Kỹ Thuật | Mô Tả |
|----------|-------|
| 🎯 **Smart Dialogue Chunking** | Giữ nguyên các đoạn hội thoại trong cùng một chunk để duy trì ngữ cảnh |
| 📈 **Progressive Glossary Building** | Tự động trích xuất thuật ngữ mới từ mỗi chương đã dịch |
| 🔍 **TF-IDF Glossary Selection** | Chọn thuật ngữ phù hợp nhất cho từng chunk dựa trên điểm TF-IDF |
| ⚡ **Direct EPUB Assembly** | Tạo EPUB trực tiếp với parallel writing, nhanh hơn 10-20x |
| 🚀 **Concurrent Pipeline** | Crawl và dịch song song với nhiều worker |
| 🔌 **WebSocket Real-Time** | Theo dõi tiến trình dịch real-time qua WebSocket |

## Cài Đặt

```bash
# Clone repository
git clone https://github.com/latuannetnam/dich-truyen-tien-hiep.git
cd dich-truyen-tien-hiep

# Cài đặt với uv
uv sync
```

## Cấu Hình

Sao chép `.env.example` thành `.env` và cấu hình:

```bash
cp .env.example .env
```

Thiết lập bắt buộc:
```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1
```

## Bắt Đầu Nhanh

### Pipeline Đầy Đủ (Đơn Giản Nhất)

```bash
# Crawl + dịch + xuất EPUB
uv run dich-truyen pipeline --url "https://www.piaotia.com/html/8/8717/index.html"

# Chỉ dịch 10 chương đầu, xuất định dạng Kindle
uv run dich-truyen pipeline \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --chapters 1-10 \
  --format azw3
```

### Các Chế Độ Pipeline

#### Chỉ Crawl (Review Trước Khi Dịch)

```bash
# Crawl chương để review trước khi dịch
uv run dich-truyen pipeline --url "https://..." --crawl-only

# Xem các chương đã crawl trong books/<book-dir>/raw/
```

#### Chỉ Dịch (Sách Đã Có)

```bash
# Dịch sách đã crawl trước đó
uv run dich-truyen pipeline --book-dir books/my-book --translate-only

# Dịch với glossary tùy chỉnh
uv run dich-truyen pipeline \
  --book-dir books/my-book \
  --translate-only \
  --glossary my-glossary.csv
```

#### Tiếp Tục Công Việc Bị Gián Đoạn

```bash
# Tiếp tục từ nơi dừng lại (tự động detect)
uv run dich-truyen pipeline --book-dir books/my-book

# Ép làm lại từ đầu
uv run dich-truyen pipeline --book-dir books/my-book --force
```

## Tham Chiếu Lệnh

### `pipeline` - Lệnh Chính

```bash
uv run dich-truyen pipeline [OPTIONS]

Tùy chọn:
  --url TEXT            URL trang mục lục sách (cho sách mới)
  --book-dir PATH       Thư mục sách đã có
  --chapters TEXT       Phạm vi chương, ví dụ: "1-100"
  --style TEXT          Style dịch (mặc định: tien_hiep)
  --format CHOICE       Định dạng: epub, azw3, mobi, pdf
  --workers INT         Số worker dịch (mặc định: 3)
  --crawl-only          Chỉ crawl, không dịch
  --translate-only      Chỉ dịch, không crawl
  --skip-export         Bỏ qua xuất ebook
  --no-glossary         Tắt auto-glossary
  --glossary PATH       Import glossary từ CSV
  --force               Ép làm lại tất cả
```

### `ui` - Giao Diện Web

```bash
# Mở giao diện web (tự mở trình duyệt)
uv run dich-truyen ui

# Cấu hình cổng và host
uv run dich-truyen ui --port 9000 --host 0.0.0.0

# Không tự mở trình duyệt
uv run dich-truyen ui --no-browser
```

> Xem [hướng dẫn Web UI chi tiết](web/README.md) để biết thêm về các trang và tính năng giao diện.

### `export` - Xuất Ebook

```bash
uv run dich-truyen export --book-dir books/my-book --format azw3
```

### `glossary` - Quản Lý Glossary

```bash
# Xem glossary
uv run dich-truyen glossary show --book-dir books/my-book

# Xuất glossary
uv run dich-truyen glossary export --book-dir books/my-book -o glossary.csv

# Import glossary (gộp với existing)
uv run dich-truyen glossary import --book-dir books/my-book -i edited.csv --merge

# Import glossary (thay thế)
uv run dich-truyen glossary import --book-dir books/my-book -i new.csv --replace
```

### `style` - Quản Lý Style

```bash
# Liệt kê styles
uv run dich-truyen style list

# Tạo style mới bằng LLM
uv run dich-truyen style generate \
  --description "Văn phong ngôn tình, lãng mạn hiện đại" \
  -o styles/ngon_tinh.yaml
```

## Translation Styles

### Style Có Sẵn (Mặc định: `tien_hiep`)

| Style | Mô Tả | Dùng Cho |
|-------|-------|----------|
| `tien_hiep` | Tiên hiệp, tu chân, cổ trang | Truyện 仙侠, 修真 |
| `kiem_hiep` | Kiếm hiệp, võ lâm, giang hồ | Truyện 武侠 |
| `huyen_huyen` | Huyền huyễn, kỳ ảo, ma pháp | Truyện 玄幻 |
| `do_thi` | Đô thị, hiện đại, nhẹ nhàng | Truyện 都市 |

### Style Tùy Chỉnh

```yaml
# styles/ngon_tinh.yaml
name: ngon_tinh
description: Văn phong ngôn tình, lãng mạn hiện đại
guidelines:
  - Ngôn ngữ mềm mại, lãng mạn
  - Đại từ: 'anh', 'em', 'cô ấy'
vocabulary:
  我: em
  你: anh
  爱: yêu
tone: casual
examples:
  - chinese: "我爱你"
    vietnamese: "Em yêu anh"
```

## Cấu Trúc Thư Mục Sách

```
books/
└── 8717-indexhtml/
    ├── book.json           # Metadata & tiến độ
    ├── glossary.csv        # Thuật ngữ dịch
    ├── raw/                # Chương đã download
    ├── translated/         # Chương đã dịch
    ├── epub_build/         # Thư mục build EPUB
    └── output/             # Ebook đã xuất
        ├── book.epub
        └── book.azw3
```

## Yêu Cầu

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Node.js](https://nodejs.org/) 18+ (cho giao diện web)
- [Calibre](https://calibre-ebook.com/) (để xuất ebook)
- OpenAI API key (hoặc endpoint tương thích)

## Phát Triển

```bash
# Cài đặt dependencies Python
uv sync --dev

# Cài đặt dependencies frontend
cd web && npm install

# Chạy tests Python
uv run pytest tests/ -v

# Chạy lint frontend
cd web && npm run lint

# Chạy với coverage
uv run pytest tests/ --cov=src/dich_truyen --cov-report=html
```

## License

MIT License
