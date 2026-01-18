# Solution 2: "Editor-in-Chief" - Two-Pass Translation

## Overview

Add a second "polishing" pass after the initial translation. The LLM acts as a senior editor, comparing the draft against the source to improve fluency without changing meaning.

This leverages GPT-4.1's large context window to hold both the original Chinese and the draft Vietnamese simultaneously, enabling high-quality editorial improvements.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     translate_chapter()                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │   Source    │ ───▶ │  Pass 1:    │ ───▶ │  Pass 2:    │     │
│  │  Chinese    │      │  Translate  │      │   Polish    │     │
│  │   (raw)     │      │   (Draft)   │      │  (Final)    │     │
│  └─────────────┘      └─────────────┘      └─────────────┘     │
│        │                    │                    │              │
│        │                    ▼                    ▼              │
│        │              (in memory)         translated/N.txt     │
│        │                    │                    │              │
│        └────────────────────┼────────────────────┘              │
│                             │                                   │
│                      ┌──────▼──────┐                            │
│                      │  Glossary   │                            │
│                      │  + Style    │                            │
│                      └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Save Draft? | No | Cleaner output, less disk usage |
| Fallback on Failure | Retry once, then use draft | Never lose work |
| Default Enabled | Yes | Quality improvement is the goal |

## Token Cost Estimate

| Phase | Input Tokens | Output Tokens | Total |
|-------|--------------|---------------|-------|
| Pass 1 (Translate) | ~7,000 | ~7,000 | ~14,000 |
| Pass 2 (Polish) | ~15,000 | ~7,000 | ~22,000 |
| **Combined** | ~22,000 | ~14,000 | **~36,000** |

**Cost multiplier: ~2.5x** compared to single-pass translation.

## File Changes

### 1. `src/dich_truyen/config.py`

Add new settings to `TranslationConfig` class (after line 86):

```python
# Two-pass translation (Editor-in-Chief)
enable_polish_pass: bool = Field(
    default=True, 
    description="Enable second pass for polishing translation"
)
polish_temperature: float = Field(
    default=0.4, 
    description="Temperature for polish pass (lower = more conservative edits)"
)
polish_max_retries: int = Field(
    default=1,
    description="Max retries for polish pass before falling back to draft"
)
```

### 2. `src/dich_truyen/translator/llm.py`

Add three new methods after `translate()` method (~line 150):

#### `_build_polish_system_prompt()`

```python
def _build_polish_system_prompt(self, style_prompt: str) -> str:
    """Build the system prompt for polishing pass."""
    return f"""Bạn là biên tập viên cao cấp chuyên về tiểu thuyết tiên hiệp/kiếm hiệp.

## Vai trò
Bạn nhận được bản dịch thô (draft) và nguyên tác tiếng Trung. Nhiệm vụ của bạn là CHỈNH SỬA bản dịch để:

1. **Tự nhiên hơn**: Câu văn mượt mà như người Việt viết, không "dịch máy"
2. **Nhất quán phong cách**: Đảm bảo giọng văn {style_prompt} xuyên suốt
3. **Chính xác thuật ngữ**: Kiểm tra glossary được sử dụng đúng
4. **Giữ nguyên ý nghĩa**: KHÔNG thêm, bớt, hoặc thay đổi nội dung

## Quy tắc tuyệt đối
- Nếu câu dịch đã tốt, GIỮ NGUYÊN - đừng sửa vì sửa sẽ làm hỏng bản dịch
- KHÔNG thêm giải thích, chú thích, hoặc bình luận
- KHÔNG dịch lại từ đầu - chỉ chỉnh sửa những chỗ cần thiết
- Giữ nguyên cấu trúc đoạn văn (số lượng đoạn, xuống dòng)
- Chỉ trả về văn bản đã chỉnh sửa, không có gì khác"""
```

#### `_build_polish_user_prompt()`

```python
def _build_polish_user_prompt(
    self,
    source_chinese: str,
    draft_vietnamese: str,
    glossary_prompt: str,
) -> str:
    """Build the user prompt for polishing pass."""
    parts = []
    
    if glossary_prompt:
        parts.append(f"## Bảng thuật ngữ (kiểm tra sử dụng đúng)\n{glossary_prompt}\n")
    
    parts.append(f"## Nguyên tác tiếng Trung\n{source_chinese}\n")
    parts.append(f"## Bản dịch thô cần chỉnh sửa\n{draft_vietnamese}")
    
    return "\n".join(parts)
```

#### `polish()`

```python
async def polish(
    self,
    source_chinese: str,
    draft_vietnamese: str,
    style_prompt: str,
    glossary_prompt: str = "",
    temperature: Optional[float] = None,
) -> str:
    """Polish a draft translation by comparing against source.
    
    Args:
        source_chinese: Original Chinese text
        draft_vietnamese: Draft Vietnamese translation
        style_prompt: Style guidelines for consistency
        glossary_prompt: Glossary terms to verify
        temperature: Override temperature (lower = more conservative)
    
    Returns:
        Polished Vietnamese text
    """
    system_prompt = self._build_polish_system_prompt(style_prompt)
    user_prompt = self._build_polish_user_prompt(
        source_chinese, draft_vietnamese, glossary_prompt
    )
    
    return await self.complete(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature or 0.4,
    )
```

### 3. `src/dich_truyen/translator/engine.py`

#### Add `_polish_translation()` helper method

Add after `translate_chunk_with_context_marker()` method:

```python
async def _polish_translation(
    self,
    source_chinese: str,
    draft_vietnamese: str,
    progress_callback=None,
) -> str:
    """Polish a draft translation using Editor-in-Chief approach.
    
    Args:
        source_chinese: Original Chinese text
        draft_vietnamese: Draft Vietnamese translation
        progress_callback: Optional callback for progress updates
        
    Returns:
        Polished Vietnamese text, or draft if polish fails
    """
    if not self.style:
        raise ValueError("Style template not set")
    
    style_prompt = self.style.to_prompt_format()
    
    # Get relevant glossary for verification
    max_glossary = self.config.glossary_max_entries
    if self.glossary:
        glossary_prompt = self.glossary.format_relevant_entries(
            source_chinese, scorer=self.term_scorer, max_entries=max_glossary
        )
    else:
        glossary_prompt = ""
    
    max_retries = self.config.polish_max_retries
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if progress_callback:
                progress_callback(f"polishing (attempt {attempt + 1})")
            
            polished = await self.llm.polish(
                source_chinese=source_chinese,
                draft_vietnamese=draft_vietnamese,
                style_prompt=style_prompt,
                glossary_prompt=glossary_prompt,
                temperature=self.config.polish_temperature,
            )
            return polished
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                console.print(f"[yellow]Polish attempt {attempt + 1} failed: {e}[/yellow]")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # All retries failed - fallback to draft
    console.print(f"[yellow]Polish failed after {max_retries + 1} attempts, using draft: {last_error}[/yellow]")
    return draft_vietnamese
```

#### Modify `translate_chapter()` method

After the line where `translated_chunks` is joined (~line 465), replace:

```python
# OLD CODE:
# Combine translated chunks
result = "\n\n".join(translated_chunks)
```

With:

```python
# NEW CODE:
# Combine translated chunks
draft_result = "\n\n".join(translated_chunks)

# Polish pass (Editor-in-Chief)
if self.config.enable_polish_pass:
    if progress_callback:
        progress_callback(total_chunks, total_chunks, "polishing...")
    
    result = await self._polish_translation(
        source_chinese=content,
        draft_vietnamese=draft_result,
        progress_callback=lambda status: progress_callback(total_chunks, total_chunks, status) if progress_callback else None,
    )
else:
    result = draft_result

if progress_callback:
    progress_callback(total_chunks, total_chunks, "[done]")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSLATION_ENABLE_POLISH_PASS` | `true` | Enable/disable polish pass |
| `TRANSLATION_POLISH_TEMPERATURE` | `0.4` | Temperature for polish (lower = conservative) |
| `TRANSLATION_POLISH_MAX_RETRIES` | `1` | Retries before fallback to draft |

## Prompt Design Rationale

### Why "Edit" not "Re-translate"?

LLMs are significantly better at *editing* text than *generating* from scratch because:

1. **Constrained task**: The model only needs to improve phrasing, not decode meaning
2. **Reference comparison**: Model can compare against source to catch errors
3. **Conservative changes**: Lower temperature means minimal unnecessary rewrites

### Key Instructions in Polish Prompt

| Instruction | Purpose |
|-------------|---------|
| "Nếu câu dịch đã tốt, GIỮ NGUYÊN" | Prevents over-editing good translations |
| "KHÔNG dịch lại từ đầu" | Forces editing mode, not translation mode |
| "Giữ nguyên cấu trúc đoạn văn" | Preserves paragraph structure for file integrity |
| "Chỉ trả về văn bản đã chỉnh sửa" | Clean output, no meta-commentary |

## Error Handling

```
┌─────────────────────────────────────────────────┐
│              Polish Pass Flow                    │
├─────────────────────────────────────────────────┤
│                                                  │
│  Attempt 1 ───▶ Success? ───▶ Return polished   │
│       │              │                           │
│       │              ▼ No                        │
│       │         Wait 1s                          │
│       ▼                                          │
│  Attempt 2 ───▶ Success? ───▶ Return polished   │
│       │              │                           │
│       │              ▼ No                        │
│       │         Log warning                      │
│       ▼                                          │
│  Return draft (fallback)                         │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Key principle**: Never lose work. Draft is always preserved as fallback.

## Testing Plan

| Test | Description | Expected Result |
|------|-------------|-----------------|
| Unit: `polish()` method | Call with sample text | Returns polished text |
| Integration: Full chapter | Translate with polish enabled | Final output is polished |
| Fallback: API failure | Mock API error | Draft is used, warning logged |
| Quality: Manual review | Compare draft vs polished | Polished has better flow |

## Usage

### Enable (default)

```bash
# Already enabled by default
uv run dich-truyen translate --book books/my-novel
```

### Disable

```bash
# Via environment variable
TRANSLATION_ENABLE_POLISH_PASS=false uv run dich-truyen translate --book books/my-novel
```

### Adjust temperature

```bash
# More conservative (fewer changes)
TRANSLATION_POLISH_TEMPERATURE=0.2 uv run dich-truyen translate --book books/my-novel

# More aggressive (more rewrites)
TRANSLATION_POLISH_TEMPERATURE=0.6 uv run dich-truyen translate --book books/my-novel
```

## Estimated Implementation Time

| Task | Time |
|------|------|
| Config changes | 5 min |
| LLM polish methods | 15 min |
| Engine integration | 20 min |
| Testing | 10 min |
| **Total** | **~50 min** |
