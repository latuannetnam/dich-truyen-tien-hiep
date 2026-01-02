"""Encoding detection and handling utilities."""

from typing import Optional

import chardet


def detect_encoding(content: bytes) -> str:
    """Detect the encoding of byte content.

    Args:
        content: Raw bytes content

    Returns:
        Detected encoding name (e.g., 'utf-8', 'gbk', 'gb2312')
    """
    result = chardet.detect(content)
    encoding = result.get("encoding", "utf-8")

    # Normalize common Chinese encodings
    if encoding:
        encoding_lower = encoding.lower()
        if encoding_lower in ("gb2312", "gb18030"):
            return "gbk"  # GBK is a superset, more compatible

    return encoding or "utf-8"


def decode_content(content: bytes, encoding: Optional[str] = None) -> str:
    """Decode byte content to string with encoding detection.

    Args:
        content: Raw bytes content
        encoding: Optional explicit encoding, auto-detect if None

    Returns:
        Decoded string content
    """
    if encoding is None:
        encoding = detect_encoding(content)

    # Try the detected/specified encoding first
    try:
        return content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        pass

    # Fallback chain for Chinese content
    fallback_encodings = ["gbk", "gb18030", "utf-8", "latin-1"]
    for fallback in fallback_encodings:
        if fallback.lower() != encoding.lower():
            try:
                return content.decode(fallback)
            except (UnicodeDecodeError, LookupError):
                continue

    # Last resort: decode with errors ignored
    return content.decode("utf-8", errors="ignore")
