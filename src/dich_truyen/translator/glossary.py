"""Glossary management for consistent term translation."""

import csv
import json
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dich_truyen.translator.term_scorer import TermScorer
    from dich_truyen.translator.style import StyleTemplate

from pydantic import BaseModel, Field
import structlog

from dich_truyen.config import get_config

logger = structlog.get_logger()


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

    def to_prompt_format(self, max_entries: Optional[int] = None) -> str:
        """Format glossary for inclusion in LLM prompt.

        Args:
            max_entries: Maximum entries to include (None = all entries).
                        If limited, prioritizes characters and important categories.

        Returns:
            Formatted string for prompt
        """
        if not self.entries:
            return ""

        # If max_entries specified, select most important entries
        entries_to_use = self.entries
        if max_entries and len(self.entries) > max_entries:
            # Priority order: characters first, then other categories
            priority_order = ["character", "realm", "technique", "location", "item", "organization", "general"]
            sorted_entries = sorted(
                self.entries,
                key=lambda e: priority_order.index(e.category) if e.category in priority_order else 99
            )
            entries_to_use = sorted_entries[:max_entries]

        lines = []
        for category in self.CATEGORIES:
            category_entries = [e for e in entries_to_use if e.category == category]
            if category_entries:
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
                for entry in category_entries:
                    lines.append(f"- {entry.chinese} → {entry.vietnamese}")
                lines.append("")

        return "\n".join(lines)

    def get_relevant_entries(
        self,
        chunk: str,
        scorer: Optional["TermScorer"] = None,
        max_entries: int = 100,
    ) -> list[GlossaryEntry]:
        """Get glossary entries relevant to a specific chunk.
        
        If a scorer is provided, uses TF-IDF to rank terms by relevance.
        Otherwise falls back to simple presence check with category priority.
        
        Args:
            chunk: Text chunk to find relevant entries for
            scorer: Optional TermScorer for TF-IDF based ranking
            max_entries: Maximum entries to return
            
        Returns:
            List of relevant GlossaryEntry items, sorted by relevance
        """
        if not self.entries:
            return []
        
        if scorer and scorer.is_fitted():
            # TF-IDF based selection
            scores = scorer.score_for_chunk(chunk)
            
            # Get entries that have scores (present in chunk)
            scored_entries = [
                (entry, scores.get(entry.chinese, 0))
                for entry in self.entries
                if entry.chinese in scores
            ]
            
            # Sort by score descending
            scored_entries.sort(key=lambda x: -x[1])
            
            # Take top entries
            return [entry for entry, _ in scored_entries[:max_entries]]
        else:
            # Fallback: simple presence check with category priority
            priority_order = ["character", "realm", "technique", "location", "item", "organization", "general"]
            
            relevant = [
                entry for entry in self.entries
                if entry.chinese in chunk
            ]
            
            # Sort by category priority
            relevant.sort(
                key=lambda e: priority_order.index(e.category) if e.category in priority_order else 99
            )
            
            return relevant[:max_entries]

    def format_relevant_entries(
        self,
        chunk: str,
        scorer: Optional["TermScorer"] = None,
        max_entries: int = 100,
    ) -> str:
        """Format relevant glossary entries for a specific chunk.
        
        Combines get_relevant_entries with formatting.
        
        Args:
            chunk: Text chunk to find relevant entries for
            scorer: Optional TermScorer for TF-IDF based ranking
            max_entries: Maximum entries to include
            
        Returns:
            Formatted string for LLM prompt
        """
        entries = self.get_relevant_entries(chunk, scorer, max_entries)
        
        if not entries:
            return ""
        
        # Group by category
        lines = []
        for category in self.CATEGORIES:
            category_entries = [e for e in entries if e.category == category]
            if category_entries:
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
                for entry in category_entries:
                    if entry.notes:
                        lines.append(f"- {entry.chinese} → {entry.vietnamese} ({entry.notes})")
                    else:
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
        # Note: console output removed - glossary count shown in Live table instead

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

        logger.info("glossary_imported", entries=len(entries), path=str(path))
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
Trích xuất TỐI THIỂU {min_entries} thuật ngữ theo danh mục:
1. **character** - Tên nhân vật (人物) - ưu tiên nhân vật chính và phụ quan trọng
2. **realm** - Cảnh giới tu luyện (境界)
3. **technique** - Võ công/Pháp thuật (武功/法术)
4. **location** - Địa danh (地点) - thành phố, môn phái, núi sông
5. **item** - Vật phẩm/Pháp bảo (法宝/神器)
6. **organization** - Môn phái/Thế lực (门派/势力)

{character_naming_rule}

Với mỗi thuật ngữ, cung cấp:
- Tiếng Trung gốc
- Bản dịch tiếng Việt
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
    style: Optional["StyleTemplate"] = None,
    existing_glossary: Optional[Glossary] = None,
    min_entries: int = 20,
    max_entries: int = 100,
) -> Glossary:
    """Use LLM to generate glossary from sample texts.

    Processes samples in batches to avoid token limits.

    Args:
        sample_texts: List of sample text excerpts
        style: Optional style template for naming conventions
        existing_glossary: Existing glossary to merge with
        min_entries: Minimum number of entries to request per batch
        max_entries: Maximum entries to keep in final glossary

    Returns:
        Generated glossary
    """
    from dich_truyen.translator.llm import LLMClient
    import re

    llm = LLMClient(task="glossary")
    
    # Determine character naming rule based on style
    character_naming_rule = _get_character_naming_rule(style)
    
    # Process samples in batches of 5 to avoid token limits
    BATCH_SIZE = 5
    all_entries: list[GlossaryEntry] = []
    
    # Calculate entries per batch
    num_batches = (len(sample_texts) + BATCH_SIZE - 1) // BATCH_SIZE
    entries_per_batch = max(10, min_entries // max(1, num_batches))
    
    logger.info("glossary_batch_start", samples=len(sample_texts), batches=num_batches)
    
    for batch_idx in range(0, len(sample_texts), BATCH_SIZE):
        batch = sample_texts[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        
        logger.debug("glossary_batch", batch=batch_num, total=num_batches, samples=len(batch))
        
        # Combine batch texts
        combined = "\n\n---\n\n".join(batch)

        prompt = GLOSSARY_GENERATION_PROMPT.format(
            sample_texts=combined,
            min_entries=entries_per_batch,
            character_naming_rule=character_naming_rule,
        )

        try:
            response = await llm.complete(
                system_prompt="Bạn là chuyên gia phân tích tiểu thuyết Trung Quốc. Trả về JSON chính xác với nhiều thuật ngữ nhất có thể.",
                user_prompt=prompt,
                temperature=0.3,
            )

            # Parse JSON from response
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                try:
                    entries_data = json.loads(json_match.group())
                    batch_entries = [GlossaryEntry.model_validate(e) for e in entries_data]
                    all_entries.extend(batch_entries)
                    logger.debug("glossary_batch_terms", batch=batch_num, terms=len(batch_entries))
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning("glossary_batch_parse_error", batch=batch_num, error=str(e))
            else:
                logger.warning("glossary_batch_no_json", batch=batch_num)
        except Exception as e:
            logger.error("glossary_batch_failed", batch=batch_num, error=str(e))
            continue

    # Deduplicate entries (keep first occurrence)
    seen = set()
    unique_entries = []
    for entry in all_entries:
        if entry.chinese not in seen:
            seen.add(entry.chinese)
            unique_entries.append(entry)
    
    logger.info("glossary_generated", unique_entries=len(unique_entries))

    # Limit to max_entries
    if len(unique_entries) > max_entries:
        unique_entries = unique_entries[:max_entries]
        logger.debug("glossary_limited", max_entries=max_entries)

    # Create or merge with existing
    if existing_glossary:
        for entry in unique_entries:
            existing_glossary.add(entry)
        return existing_glossary
    else:
        return Glossary(unique_entries)


PROGRESSIVE_GLOSSARY_PROMPT = """Phân tích đoạn văn tiểu thuyết sau và tìm các thuật ngữ MỚI chưa có trong glossary hiện tại.

## Glossary hiện tại (KHÔNG trùng lặp)
{existing_terms}

## Văn bản cần phân tích
{text}

## Yêu cầu
Chỉ trích xuất các thuật ngữ QUAN TRỌNG và MỚI (không có trong glossary hiện tại):
- Tên nhân vật mới xuất hiện (character)
- Địa danh mới (location)
- Môn phái, tổ chức mới (organization)
- Cảnh giới, pháp bảo quan trọng (realm, item, technique)

{character_naming_rule}

Chỉ trả về 3-5 thuật ngữ quan trọng nhất. Nếu không có thuật ngữ mới quan trọng, trả về [].

## Định dạng trả về
JSON array:
[
    {{"chinese": "...", "vietnamese": "...", "category": "...", "notes": "..."}}
]"""


async def extract_new_terms_from_chapter(
    chinese_text: str,
    existing_glossary: Glossary,
    style: Optional["StyleTemplate"] = None,
    max_new_terms: int = 5,
) -> list[GlossaryEntry]:
    """Extract new important terms from a chapter that aren't in the glossary.

    This is used for progressive glossary building during translation.

    Args:
        chinese_text: Chinese text to analyze (typically first 2000 chars of chapter)
        existing_glossary: Current glossary to avoid duplicates
        style: Optional style template for naming conventions
        max_new_terms: Maximum new terms to extract per chapter

    Returns:
        List of new GlossaryEntry items (empty if none found)
    """
    from dich_truyen.translator.llm import LLMClient
    import re

    # Only analyze first portion to save tokens
    text_sample = chinese_text[:2000] if len(chinese_text) > 2000 else chinese_text
    
    # Get existing terms for deduplication
    existing_terms = ", ".join([e.chinese for e in existing_glossary.entries[:200]])
    if not existing_terms:
        existing_terms = "(chưa có)"

    llm = LLMClient(task="glossary")
    
    # Get character naming rule based on style
    character_naming_rule = _get_character_naming_rule(style)

    prompt = PROGRESSIVE_GLOSSARY_PROMPT.format(
        existing_terms=existing_terms,
        text=text_sample,
        character_naming_rule=character_naming_rule,
    )

    try:
        response = await llm.complete(
            system_prompt="Bạn là chuyên gia phân tích tiểu thuyết Trung Quốc. Trả về JSON chính xác, ngắn gọn.",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=500,  # Keep response short
        )

        # Parse JSON from response
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            try:
                entries_data = json.loads(json_match.group())
                entries = [GlossaryEntry.model_validate(e) for e in entries_data[:max_new_terms]]
                # Filter out any that already exist
                new_entries = [e for e in entries if e.chinese not in existing_glossary]
                return new_entries
            except (json.JSONDecodeError, Exception):
                pass
    except Exception:
        pass  # Silently fail - progressive glossary is optional enhancement

    return []


def _get_character_naming_rule(style: Optional["StyleTemplate"]) -> str:
    """Extract character naming rule from style template.
    
    Args:
        style: Style template with guidelines
        
    Returns:
        Formatted character naming rule for LLM prompt
    """
    if not style or not style.guidelines:
        # Default: use Sino-Vietnamese for xianxia/wuxia genres
        return "**Quy tắc dịch tên**: Dịch tên nhân vật và địa danh theo phiên âm Hán-Việt (ví dụ: 陈平安 → Trần Bình An)."
    
    # Extract naming-related guidelines from style
    naming_rules = []
    keywords = ["tên", "nhân vật", "địa danh", "chức danh", "vật phẩm", "name", "character"]
    
    for guideline in style.guidelines:
        guideline_lower = guideline.lower()
        if any(kw in guideline_lower for kw in keywords):
            naming_rules.append(guideline)
    
    if naming_rules:
        # Use actual guidelines from style
        rules_text = "\n".join(f"- {rule}" for rule in naming_rules[:5])  # Limit to 5 rules
        return f"**Quy tắc dịch tên từ style '{style.name}':**\n{rules_text}"
    
    # Fallback to default Sino-Vietnamese
    return "**Quy tắc dịch tên**: Dịch tên nhân vật và địa danh theo phiên âm Hán-Việt (ví dụ: 陈平安 → Trần Bình An)."

