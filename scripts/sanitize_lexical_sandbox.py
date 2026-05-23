#!/usr/bin/env python3
"""Programmatic Lexical Sandbox Sanitizer for Vietnamese Novel Translations.

Scans translated files for leaked English conjunctions/prepositions and replaces
them with their proper Vietnamese equivalents using precise word boundaries.
"""

import re
import sys
from pathlib import Path

# Common leaked English words and their contextual Vietnamese replacements
LEAKED_WORDS_MAP = {
    r"\bbut\b": "nhưng",
    r"\bBut\b": "Nhưng",
    r"\band\b": "và",
    r"\bAnd\b": "Và",
    r"\bor\b": "hoặc",
    r"\bOr\b": "Hoặc",
    r"\bwith\b": "với",
    r"\bWith\b": "Với",
    r"\bof\b": "của",
    r"\bOf\b": "Của",
    r"\bhere\b": "đây",
    r"\bHere\b": "Đây",
    r"\bnow\b": "bây giờ",
    r"\bNow\b": "Bây giờ",
    r"\bokay\b": "được",
    r"\bOkay\b": "Được",
    r"\bwhile\b": "trong khi",
    r"\bWhile\b": "Trong khi",
    r"\bbefore\b": "trước khi",
    r"\bBefore\b": "Trước khi",
    r"\bafter\b": "sau khi",
    r"\bAfter\b": "Sau khi",
}

# English words to flag for manual review (could be false positives if replaced automatically)
FLAG_WORDS = [
    "the", "to", "in", "on", "at", "for"
]

def sanitize_file(file_path: Path, dry_run: bool = False) -> bool:
    """Sanitizes a single translation file.

    Args:
        file_path: Path to the translated text file.
        dry_run: If True, only prints detected words without modifying the file.

    Returns:
        True if the file was modified/flagged, False otherwise.
    """
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist.")
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    modified = False
    new_content = content
    replacements_made = []

    # 1. Perform automatic replacements
    for pattern, replacement in LEAKED_WORDS_MAP.items():
        matches = re.findall(pattern, new_content)
        if matches:
            replacements_made.append(f"{pattern.strip(r'\\b')} -> {replacement} ({len(matches)} occurrences)")
            new_content = re.sub(pattern, replacement, new_content)
            modified = True

    # 2. Flag words for review
    flagged_words = []
    for word in FLAG_WORDS:
        pattern = rf"\b{word}\b"
        matches = re.findall(pattern, new_content, re.IGNORECASE)
        if matches:
            flagged_words.append(f"'{word}' ({len(matches)} occurrences)")

    # Reporting
    if replacements_made or flagged_words:
        print(f"\n[AUDIT] {file_path.name}:")
        if replacements_made:
            print("  Replacements made:")
            for rep in replacements_made:
                print(f"    - {rep}")
        if flagged_words:
            print("  WARNING: Flagged words requiring review:")
            for flag in flagged_words:
                print(f"    - {flag}")
            print("  (Please verify manual translations of prepositions like in, on, at, to, for)")

    if modified and not dry_run:
        try:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"  [SUCCESS] Programmatically sanitized {file_path.name} successfully.")
        except Exception as e:
            print(f"  Error writing back to {file_path}: {e}")
            return False

    return modified or bool(flagged_words)

def sanitize_directory(book_dir: str, dry_run: bool = False) -> None:
    """Sanitizes all translating/translated files inside a book directory."""
    path = Path(book_dir)
    target_dirs = [path / "translating", path / "translated"]
    
    txt_files = []
    for t_dir in target_dirs:
        if t_dir.exists():
            txt_files.extend(list(t_dir.glob("*.txt")))

    if not txt_files:
        print(f"No text translation files found in {book_dir}/translating/ or translated/.")
        return

    print(f"Scanning and sanitizing {len(txt_files)} files in {book_dir}...")
    flagged_count = 0
    for f_path in sorted(txt_files, key=lambda p: int(p.stem) if p.stem.isdigit() else 999999):
        if sanitize_file(f_path, dry_run):
            flagged_count += 1
            
    print(f"\nScan complete. Flagged/modified {flagged_count} out of {len(txt_files)} files.")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if len(sys.argv) < 2:
        print("Usage: python sanitize_lexical_sandbox.py <book_dir_or_file_path> [--dry-run]")
        sys.exit(1)

    target = sys.argv[1]
    is_dry_run = "--dry-run" in sys.argv
    
    target_path = Path(target)
    if target_path.is_file():
        sanitize_file(target_path, is_dry_run)
    elif target_path.is_dir():
        sanitize_directory(target, is_dry_run)
    else:
        print(f"Error: '{target}' is not a valid file or directory.")
        sys.exit(1)
