"""Glossary management for consistent term translation."""

import csv
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console

from dich_truyen.config import get_config

console = Console()


class GlossaryEntry(BaseModel):
    """A single glossary entry."""

    chinese: str = Field(description="Chinese term")
    vietnamese: str = Field(description="Vietnamese translation")
    category: str = Field(
        default="general",
        description="Category: character, realm, technique, location, item, organization",
    )
    notes: Optional[str] = Field(default=None, description="Additional context or notes")


class Glossary:
    """Manage translation glossary for consistent term translation."""

    CATEGORIES = [
        "character",  # 人物 - Character names
        "realm",  # 境界 - Cultivation realms
        "technique",  # 武功/法术 - Martial arts/Techniques
        "location",  # 地点 - Locations
        "item",  # 法宝/神器 - Items/Artifacts
        "organization",  # 门派/势力 - Sects/Organizations
        "general",  # Other terms
    ]

    def __init__(self, entries: Optional[list[GlossaryEntry]] = None):
        """Initialize the glossary.

        Args:
            entries: Initial list of entries
        """
        self.entries: list[GlossaryEntry] = entries or []
        self._index: dict[str, GlossaryEntry] = {}
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the lookup index."""
        self._index = {entry.chinese: entry for entry in self.entries}

    def add(self, entry: GlossaryEntry) -> None:
        """Add an entry to the glossary.

        Args:
            entry: Entry to add (updates existing if same Chinese term)
        """
        if entry.chinese in self._index:
            # Update existing
            idx = next(
                i for i, e in enumerate(self.entries) if e.chinese == entry.chinese
            )
            self.entries[idx] = entry
        else:
            self.entries.append(entry)
        self._index[entry.chinese] = entry

    def remove(self, chinese: str) -> bool:
        """Remove an entry by Chinese term.

        Args:
            chinese: Chinese term to remove

        Returns:
            True if entry was removed
        """
        if chinese in self._index:
            self.entries = [e for e in self.entries if e.chinese != chinese]
            del self._index[chinese]
            return True
        return False

    def lookup(self, chinese: str) -> Optional[GlossaryEntry]:
        """Look up an entry by Chinese term.

        Args:
            chinese: Chinese term to look up

        Returns:
            GlossaryEntry if found, None otherwise
        """
        return self._index.get(chinese)

    def get_by_category(self, category: str) -> list[GlossaryEntry]:
        """Get all entries in a category.

        Args:
            category: Category to filter by

        Returns:
            List of entries in the category
        """
        return [e for e in self.entries if e.category == category]

    def to_prompt_format(self) -> str:
        """Format glossary for inclusion in LLM prompt.

        Returns:
            Formatted string for prompt
        """
        if not self.entries:
            return ""

        lines = []
        for category in self.CATEGORIES:
            entries = self.get_by_category(category)
            if entries:
                category_name = {
                    "character": "Nhân vật",
                    "realm": "Cảnh giới",
                    "technique": "Võ công/Pháp thuật",
                    "location": "Địa danh",
                    "item": "Vật phẩm",
                    "organization": "Môn phái/Thế lực",
                    "general": "Thuật ngữ chung",
                }.get(category, category)

                lines.append(f"### {category_name}")
                for entry in entries:
                    lines.append(f"- {entry.chinese} → {entry.vietnamese}")
                lines.append("")

        return "\n".join(lines)

    def to_csv(self, path: Path) -> None:
        """Export glossary to CSV file.

        Args:
            path: Path to save CSV file
        """
        path = Path(path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["chinese", "vietnamese", "category", "notes"]
            )
            writer.writeheader()
            for entry in self.entries:
                writer.writerow(entry.model_dump())

        console.print(f"[green]Exported {len(self.entries)} entries to {path}[/green]")

    @classmethod
    def from_csv(cls, path: Path) -> "Glossary":
        """Import glossary from CSV file.

        Args:
            path: Path to CSV file

        Returns:
            New Glossary instance
        """
        path = Path(path)
        entries = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(
                    GlossaryEntry(
                        chinese=row["chinese"],
                        vietnamese=row["vietnamese"],
                        category=row.get("category", "general"),
                        notes=row.get("notes") or None,
                    )
                )

        console.print(f"[green]Imported {len(entries)} entries from {path}[/green]")
        return cls(entries)

    def save(self, book_dir: Path) -> None:
        """Save glossary to book directory.

        Args:
            book_dir: Book directory path
        """
        glossary_path = Path(book_dir) / "glossary.csv"
        self.to_csv(glossary_path)

    @classmethod
    def load(cls, book_dir: Path) -> Optional["Glossary"]:
        """Load glossary from book directory if exists.

        Args:
            book_dir: Book directory path

        Returns:
            Glossary if file exists, None otherwise
        """
        glossary_path = Path(book_dir) / "glossary.csv"
        if glossary_path.exists():
            return cls.from_csv(glossary_path)
        return None

    @classmethod
    def load_or_create(cls, book_dir: Path) -> "Glossary":
        """Load existing glossary or create new empty one.

        Args:
            book_dir: Book directory path

        Returns:
            Glossary instance
        """
        glossary = cls.load(book_dir)
        return glossary if glossary else cls()

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, chinese: str) -> bool:
        return chinese in self._index


GLOSSARY_GENERATION_PROMPT = """Phân tích các đoạn văn tiểu thuyết Trung Quốc sau và xác định các thuật ngữ quan trọng cần dịch nhất quán.

## Văn bản mẫu
{sample_texts}

## Yêu cầu
Trích xuất các thuật ngữ theo danh mục:
1. **character** - Tên nhân vật (人物)
2. **realm** - Cảnh giới tu luyện (境界)
3. **technique** - Võ công/Pháp thuật (武功/法术)
4. **location** - Địa danh (地点)
5. **item** - Vật phẩm/Pháp bảo (法宝/神器)
6. **organization** - Môn phái/Thế lực (门派/势力)

Với mỗi thuật ngữ, cung cấp:
- Tiếng Trung gốc
- Bản dịch tiếng Việt (ưu tiên Hán-Việt cho tên riêng)
- Danh mục
- Ghi chú (nếu cần)

## Định dạng trả về
Trả về CHÍNH XÁC JSON array, không có markdown:
[
    {{"chinese": "陈平安", "vietnamese": "Trần Bình An", "category": "character", "notes": "Nhân vật chính"}},
    {{"chinese": "练气境", "vietnamese": "Luyện Khí cảnh", "category": "realm", "notes": "Cảnh giới tu luyện đầu tiên"}}
]"""


async def generate_glossary_from_samples(
    sample_texts: list[str],
    existing_glossary: Optional[Glossary] = None,
) -> Glossary:
    """Use LLM to generate glossary from sample texts.

    Args:
        sample_texts: List of sample text excerpts
        existing_glossary: Existing glossary to merge with

    Returns:
        Generated glossary
    """
    from dich_truyen.translator.llm import LLMClient

    llm = LLMClient()

    # Combine sample texts
    combined = "\n\n---\n\n".join(sample_texts[:5])  # Limit to 5 samples

    prompt = GLOSSARY_GENERATION_PROMPT.format(sample_texts=combined)

    response = await llm.complete(
        system_prompt="Bạn là chuyên gia phân tích tiểu thuyết Trung Quốc. Trả về JSON chính xác.",
        user_prompt=prompt,
        temperature=0.3,
    )

    # Parse JSON from response
    import re

    # Try to extract JSON array
    json_match = re.search(r"\[.*\]", response, re.DOTALL)
    if json_match:
        try:
            entries_data = json.loads(json_match.group())
            entries = [GlossaryEntry.model_validate(e) for e in entries_data]
        except (json.JSONDecodeError, Exception) as e:
            console.print(f"[yellow]Failed to parse glossary response: {e}[/yellow]")
            entries = []
    else:
        entries = []

    # Create or merge with existing
    if existing_glossary:
        for entry in entries:
            existing_glossary.add(entry)
        return existing_glossary
    else:
        return Glossary(entries)
