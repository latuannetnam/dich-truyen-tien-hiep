import argparse
import json
import re
from pathlib import Path


def fix_chapter_names(book_dir: Path, dry_run: bool = True) -> None:
    book_json_path = book_dir / "book.json"
    translating_dir = book_dir / "translating"

    if not book_json_path.exists():
        print(f"Error: {book_json_path} not found")
        return

    if not translating_dir.exists():
        print(f"Error: {translating_dir} not found")
        return

    with open(book_json_path, "r", encoding="utf-8") as f:
        book_data = json.load(f)

    chapters = {c["index"]: c for c in book_data.get("chapters", [])}
    txt_files = sorted(
        list(translating_dir.glob("*.txt")),
        key=lambda p: int(p.stem) if p.stem.isdigit() else 999999,
    )

    mismatches_found = 0
    fixed_count = 0

    print(f"Scanning {translating_dir}... Total txt files: {len(txt_files)}")
    if dry_run:
        print("RUNNING IN DRY-RUN MODE (No files will be modified)")

    for file_path in txt_files:
        if not file_path.stem.isdigit():
            continue
        index = int(file_path.stem)
        chapter_data = chapters.get(index)
        if not chapter_data:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            continue

        first_line = lines[0].strip()
        cn_match = re.search(r"第(\d+)章", chapter_data.get("title_cn", ""))
        if not cn_match:
            continue

        cn_num = cn_match.group(1)
        fl_match = re.search(r"Chương\s+(\d+)", first_line)
        if not fl_match:
            continue

        fl_num = fl_match.group(1)
        if fl_num != cn_num:
            mismatches_found += 1

            # Extract title suffix
            title_part = ""
            if ":" in first_line:
                title_part = first_line.split(":", 1)[1].strip()
            elif " " in first_line:
                parts = first_line.split(" ", 2)
                title_part = parts[2].strip() if len(parts) > 2 else ""

            new_first_line = f"Chương {cn_num}: {title_part}" if title_part else f"Chương {cn_num}"

            # Preserve original newline of the first line
            orig_newline = "\n"
            if lines[0].endswith("\r\n"):
                orig_newline = "\r\n"

            new_first_line_with_newline = new_first_line + orig_newline

            print(f"File {file_path.name}:")
            print(f"  Current: '{first_line}'")
            print(f"  New:     '{new_first_line}'")

            if not dry_run:
                lines[0] = new_first_line_with_newline
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                fixed_count += 1

    print("\nScan completed.")
    print(f"Total mismatches found: {mismatches_found}")
    if dry_run:
        print("Dry-run finished. No files were changed. Run with --execute to commit changes.")
    else:
        print(f"Successfully fixed {fixed_count} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix chapter prefixes in translating folder")
    parser.add_argument("--execute", action="store_true", help="Commit the changes to files")
    parser.add_argument(
        "--book-dir",
        type=str,
        default="books/15112-indexhtml",
        help="Path to book directory",
    )
    args = parser.parse_args()

    fix_chapter_names(Path(args.book_dir), dry_run=not args.execute)
