@REM uv run dich-truyen crawl --url "https://www.piaotia.com/html/8/8717/index.html" --chapters 1-3
@REM uv run dich-truyen translate --book-dir "books\8717-indexhtml" --chapters 1-3 --force
@REM uv run dich-truyen format --book-dir "books\8717-indexhtml"
@REM uv run dich-truyen export --book-dir "books\8717-indexhtml" --format azw3
@REM  Kiem Lai
@REM uv run dich-truyen pipeline --url "https://www.piaotia.com/html/8/8717/index.html" --chapters 1-5 --format pdf
@REM Ao Thuat Than Toa
@REM uv run dich-truyen pipeline --url https://www.piaotia.com/html/3/3759/index.html --chapters 1-5 --style tay_phuong --format pdf
@REM uv run dich-truyen pipeline --book-dir .\books\3759-indexhtml\ --chapters 1-2 --style tay_phuong --format pdf --translate-only --force

@REM Dai Dao Tranh Phong
uv run dich-truyen pipeline --url https://www.piaotia.com/html/2/2408/index.html --chapters 1-5 --format pdf --translate-only --force
uv run dich-truyen pipeline --url https://www.piaotia.com/html/2/2408/index.html --translate-only --force