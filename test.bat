uv run dich-truyen crawl --url "https://www.piaotia.com/html/8/8717/index.html" --chapters 1-3
uv run dich-truyen translate --book-dir "books\8717-indexhtml" --chapters 1-3 --force
uv run dich-truyen format --book-dir "books\8717-indexhtml"
uv run dich-truyen export --book-dir "books\8717-indexhtml" --format azw3
@REM uv run dich-truyen pipeline --url "https://www.piaotia.com/html/8/8717/index.html" --chapters 1-3 --format pdf