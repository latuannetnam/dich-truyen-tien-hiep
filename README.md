# Dịch Truyện - Công Cụ Dịch Truyện Trung Quốc

> **Ngôn ngữ:** [English](README.en.md) | [Tiếng Việt](README.md)

Công cụ dòng lệnh để crawl, dịch và xuất truyện Trung Quốc sang ebook tiếng Việt.

## Tính Năng

- 🕷️ **Crawler Thông Minh**: Sử dụng LLM để tự động phát hiện cấu trúc chương từ các website truyện Trung Quốc
- 🌐 **Công Cụ Dịch**: Dịch từ tiếng Trung sang tiếng Việt với các style template có thể tùy chỉnh
- 📖 **4 Style Có Sẵn**: Tiên hiệp, Kiếm hiệp, Huyền huyễn, Đô thị
- 📚 **Hệ Thống Glossary**: Duy trì thuật ngữ nhất quán (import/export CSV)
- 📕 **Xuất Ebook**: Chuyển đổi sang EPUB, AZW3, MOBI, PDF qua Calibre
- 🔄 **Hoạt Động Tiếp Tục Được**: Tiếp tục download/dịch khi bị gián đoạn

## Cài Đặt

```bash
# Clone repository
git clone https://github.com/latuannetnam/dich-truyen-tien-hiep.git
cd dich-truyen-tien-hiep

# Cài đặt với uv
uv sync

# Cài đặt Playwright cho các site chạy JavaScript (tùy chọn)
uv run playwright install chromium
```

## Cấu Hình

Sao chép `.env.example` thành `.env` và cấu hình:

```bash
cp .env.example .env
```

Thiết lập bắt buộc:
```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1  # hoặc endpoint tương thích
OPENAI_MODEL=gpt-4.1
```

Tùy chỉnh glossary (tùy chọn):
```env
# Số chương lấy mẫu để tạo glossary
TRANSLATION_GLOSSARY_SAMPLE_CHAPTERS=5
# Số ký tự mỗi chương mẫu
TRANSLATION_GLOSSARY_SAMPLE_SIZE=3000
# Số thuật ngữ tối thiểu/tối đa
TRANSLATION_GLOSSARY_MIN_ENTRIES=20
TRANSLATION_GLOSSARY_MAX_ENTRIES=100
# Chọn chương ngẫu nhiên
TRANSLATION_GLOSSARY_RANDOM_SAMPLE=true
```

## Bắt Đầu Nhanh

### Pipeline Đầy Đủ (Đơn Giản Nhất)

Xử lý toàn bộ truyện trong một lệnh:

```bash
# Mặc định: crawl tất cả chương, dịch, định dạng, xuất EPUB
uv run dich-truyen pipeline --url "https://www.piaotia.com/html/8/8717/index.html"

# Chỉ dịch 10 chương đầu, xuất định dạng Kindle
uv run dich-truyen pipeline \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --chapters 1-10 \
  --format azw3

# Sử dụng style tùy chỉnh và ép làm lại
uv run dich-truyen pipeline \
  --url "https://example.com/novel/index.html" \
  --style kiem_hiep \
  --chapters 1-50 \
  --format pdf \
  --force
```

### Lệnh Riêng Lẻ (Kiểm Soát Chi Tiết Hơn)

#### Trường hợp 1: Chỉ download (chưa dịch)

```bash
# Chỉ crawl chương 1-100 để dịch sau
uv run dich-truyen crawl \
  --url "https://www.piaotia.com/html/8/8717/index.html" \
  --chapters 1-100

# Crawl với encoding cố định cho các site có vấn đề
uv run dich-truyen crawl \
  --url "https://example.com/novel/" \
  --encoding gbk
```

#### Trường hợp 2: Dịch các chương cụ thể

```bash
# Dịch chương 1-10 với style mặc định
uv run dich-truyen translate \
  --book-dir books/8717-indexhtml \
  --chapters 1-10

# Dịch với glossary tùy chỉnh (chế độ chuyên gia)
uv run dich-truyen translate \
  --book-dir books/8717-indexhtml \
  --glossary my-custom-glossary.csv \
  --style huyen_huyen \
  --no-auto-glossary

# Ép dịch lại các chương với style khác
uv run dich-truyen translate \
  --book-dir books/8717-indexhtml \
  --chapters 1-5 \
  --style kiem_hiep \
  --force
```

#### Trường hợp 3: Tùy chỉnh metadata sách

```bash
# Định dạng với tiêu đề và tên dịch giả tùy chỉnh
uv run dich-truyen format \
  --book-dir books/8717-indexhtml \
  --title "Kiếm Lai" \
  --author "Phong Hỏa Hí Chư Hầu" \
  --translator "AI Translator" \
  --cover cover.jpg
```

#### Trường hợp 4: Xuất sang các định dạng khác

```bash
# Xuất sang Kindle (AZW3)
uv run dich-truyen export --book-dir books/8717-indexhtml --format azw3

# Xuất sang PDF để in
uv run dich-truyen export --book-dir books/8717-indexhtml --format pdf

# Xuất với đường dẫn Calibre tùy chỉnh
uv run dich-truyen export \
  --book-dir books/8717-indexhtml \
  --format epub \
  --calibre-path "C:/Program Files/Calibre2/ebook-convert.exe"
```

#### Trường hợp 5: Tiếp tục công việc bị gián đoạn

```bash
# Tiếp tục download từ nơi bạn dừng lại
uv run dich-truyen crawl --url "https://..." --resume

# Tiếp tục dịch (hành vi mặc định)
uv run dich-truyen translate --book-dir books/8717-indexhtml
```

## Tham Chiếu Lệnh

### `crawl` - Download chương từ website

```bash
uv run dich-truyen crawl [OPTIONS]

Tùy chọn:
  --url TEXT            URL trang mục lục sách (bắt buộc)
  --book-dir PATH       Thư mục sách
  --chapters TEXT       Phạm vi chương, ví dụ: "1-100" hoặc "1,5,10-20"
  --encoding TEXT       Ép encoding (tự động phát hiện nếu không đặt)
  --resume/--no-resume  Tiếp tục download bị gián đoạn (mặc định: resume)
  --force               Ép download lại ngay cả khi đã download
```

### `translate` - Dịch các chương

```bash
uv run dich-truyen translate [OPTIONS]

Tùy chọn:
  --book-dir PATH       Thư mục sách (bắt buộc)
  --chapters TEXT       Phạm vi chương, ví dụ: "1-100" hoặc "1,5,10-20"
  --style TEXT          Template style dịch (mặc định: tien_hiep)
  --glossary PATH       Import glossary CSV
  --auto-glossary       Tự động tạo glossary (mặc định: bật)
  --chunk-size INT      Số ký tự mỗi chunk dịch
  --resume/--no-resume  Tiếp tục dịch bị gián đoạn
  --force               Ép dịch lại ngay cả khi đã dịch
```

### `format` - Tạo sách HTML

```bash
uv run dich-truyen format [OPTIONS]

Tùy chọn:
  --book-dir PATH     Thư mục sách (bắt buộc)
  --title TEXT        Ghi đè tiêu đề sách
  --author TEXT       Ghi đè tên tác giả
  --translator TEXT   Tên dịch giả
  --cover PATH        Đường dẫn ảnh bìa
```

### `export` - Chuyển đổi sang ebook

```bash
uv run dich-truyen export [OPTIONS]

Tùy chọn:
  --book-dir PATH     Thư mục sách (bắt buộc)
  --format CHOICE     Định dạng: epub, azw3, mobi, pdf (mặc định: azw3)
  --calibre-path PATH Đường dẫn đến ebook-convert
```

### Quản Lý Glossary

```bash
# Xuất glossary
uv run dich-truyen glossary export --book-dir ./books/my-book -o glossary.csv

# Import glossary
uv run dich-truyen glossary import --book-dir ./books/my-book -i edited_glossary.csv
```

### Style Templates

#### Liệt Kê Các Style Có Sẵn

```bash
uv run dich-truyen style list
```

#### Tạo Style Tùy Chỉnh

```bash
# Tạo style mới sử dụng LLM
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

Bạn có thể tạo style tùy chỉnh hoặc **ghi đè style có sẵn** bằng cách đặt file YAML trong thư mục `styles/`.

**Thứ tự ưu tiên:**
1. Style tùy chỉnh trong `styles/` (kiểm tra trước)
2. Style có sẵn (dự phòng)

**Ví dụ:**

```bash
# Sử dụng style có sẵn
uv run dich-truyen translate --book-dir books/my-book --style tien_hiep

# Sử dụng style tùy chỉnh
uv run dich-truyen translate --book-dir books/my-book --style ngon_tinh

# Ghi đè style có sẵn: tạo styles/tien_hiep.yaml
# File styles/tien_hiep.yaml của bạn sẽ được dùng thay vì style có sẵn
uv run dich-truyen style generate \
  --description "Văn phong tiên hiệp cải tiến" \
  -o styles/tien_hiep.yaml
```

**Cấu trúc style tùy chỉnh (YAML):**

```yaml
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
└── 8717-indexhtml/         # Thư mục sách
    ├── book.json           # Metadata & tiến độ
    ├── glossary.csv        # Thuật ngữ dịch
    ├── raw/                # Chương đã download
    │   ├── 0001_chapter.txt
    │   └── ...
    ├── translated/         # Chương đã dịch
    │   └── ...
    ├── formatted/          # HTML đã tạo
    │   └── book.html
    └── output/             # Ebook đã xuất
        └── book.azw3
```

## Yêu Cầu

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Calibre](https://calibre-ebook.com/) (để xuất ebook)
- OpenAI API key (hoặc endpoint tương thích)

## Phát Triển

```bash
# Cài đặt dependencies dev
uv sync --dev

# Chạy tests
uv run pytest tests/ -v

# Chạy với coverage
uv run pytest tests/ --cov=src/dich_truyen --cov-report=html
```

## License

MIT License
