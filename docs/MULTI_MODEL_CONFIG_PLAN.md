# Multi-Model Configuration Plan

> **Status:** Draft  
> **Created:** 2026-01-17  
> **Goal:** Allow separate LLM models/endpoints for crawl, glossary generation, and translation phases

## Problem Statement

Currently, the application uses a single global `LLMConfig` (with `OPENAI_*` environment variable prefix) for all LLM operations:
- **Crawling:** HTML parsing and pattern discovery
- **Glossary Generation:** Term extraction from sample chapters  
- **Translation:** The main translation task

This is limiting because:
1. Different tasks may benefit from different models (e.g., cheaper models for crawling, best quality for translation)
2. Users may want to use different providers for different tasks
3. Cost optimization requires task-specific model selection

## Solution: Dedicated Configuration Sections

Add three separate LLM configuration objects, each with its own environment variable prefix:

| Task | Config Class | Env Prefix | Example Use Case |
|------|--------------|------------|------------------|
| Crawl | `CrawlerLLMConfig` | `CRAWLER_LLM_` | Use `gpt-4o-mini` for fast HTML parsing |
| Glossary | `GlossaryLLMConfig` | `GLOSSARY_LLM_` | Use `gpt-4o` for term extraction |
| Translation | `TranslatorLLMConfig` | `TRANSLATOR_LLM_` | Use `claude-sonnet` for best quality |

Each config supports: `api_key`, `base_url`, `model`, `max_tokens`, `temperature`

## Environment Variables Example

```env
# Default fallback (used if specific config not set)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Crawler-specific (cheaper/faster model for HTML parsing)
CRAWLER_LLM_API_KEY=sk-xxx
CRAWLER_LLM_BASE_URL=https://api.openai.com/v1
CRAWLER_LLM_MODEL=gpt-4o-mini

# Glossary-specific (good at term extraction)
GLOSSARY_LLM_API_KEY=sk-xxx
GLOSSARY_LLM_BASE_URL=https://api.openai.com/v1
GLOSSARY_LLM_MODEL=gpt-4o

# Translation-specific (best quality model)
TRANSLATOR_LLM_API_KEY=sk-xxx
TRANSLATOR_LLM_BASE_URL=https://api.openai.com/v1
TRANSLATOR_LLM_MODEL=gpt-5
```

## Implementation Steps

### Step 1: Modify `src/dich_truyen/config.py`

**Goal:** Add three new LLM config classes with distinct environment variable prefixes.

**Changes:**

1. **Create `CrawlerLLMConfig` class** (after line ~19)
   ```python
   class CrawlerLLMConfig(BaseSettings):
       """LLM configuration for crawler/pattern discovery."""
       model_config = SettingsConfigDict(env_prefix="CRAWLER_LLM_")
       
       api_key: str = Field(default="", description="API key")
       base_url: str = Field(default="", description="API base URL")
       model: str = Field(default="", description="Model name")
       max_tokens: int = Field(default=0, description="Max tokens per request")
       temperature: float = Field(default=0.0, description="Temperature")
   ```

2. **Create `GlossaryLLMConfig` class**
   ```python
   class GlossaryLLMConfig(BaseSettings):
       """LLM configuration for glossary generation."""
       model_config = SettingsConfigDict(env_prefix="GLOSSARY_LLM_")
       # Same fields as above
   ```

3. **Create `TranslatorLLMConfig` class**
   ```python
   class TranslatorLLMConfig(BaseSettings):
       """LLM configuration for translation."""
       model_config = SettingsConfigDict(env_prefix="TRANSLATOR_LLM_")
       # Same fields as above
   ```

4. **Update `AppConfig` class** (lines ~100-114)
   - Add new fields:
     ```python
     crawler_llm: CrawlerLLMConfig = Field(default_factory=CrawlerLLMConfig)
     glossary_llm: GlossaryLLMConfig = Field(default_factory=GlossaryLLMConfig)
     translator_llm: TranslatorLLMConfig = Field(default_factory=TranslatorLLMConfig)
     ```
   - Keep existing `llm: LLMConfig` as default fallback

5. **Update `AppConfig.load()` method** (lines ~116-132)
   - Instantiate all new config objects

6. **Add fallback helper function**
   ```python
   def get_effective_config(specific: BaseSettings, fallback: LLMConfig) -> LLMConfig:
       """Merge specific config with fallback for unset values."""
       return LLMConfig(
           api_key=specific.api_key or fallback.api_key,
           base_url=specific.base_url or fallback.base_url,
           model=specific.model or fallback.model,
           max_tokens=specific.max_tokens or fallback.max_tokens,
           temperature=specific.temperature if specific.temperature > 0 else fallback.temperature,
       )
   ```

---

### Step 2: Modify `src/dich_truyen/translator/llm.py`

**Goal:** Update `LLMClient` to support task-specific config lookup.

**Changes:**

1. **Add task type** (line ~5)
   ```python
   from typing import Literal, Optional
   TaskType = Literal["crawl", "glossary", "translate", "default"]
   ```

2. **Update `LLMClient.__init__`** (lines 16-23)
   ```python
   def __init__(self, config: Optional[LLMConfig] = None, task: Optional[TaskType] = None):
       if config:
           self.config = config
       else:
           self.config = self._get_config_for_task(task or "default")
       self._client = None
   
   def _get_config_for_task(self, task: TaskType) -> LLMConfig:
       """Get effective LLM config for a specific task."""
       from dich_truyen.config import get_config, get_effective_config
       
       app_config = get_config()
       fallback = app_config.llm
       
       if task == "crawl":
           return get_effective_config(app_config.crawler_llm, fallback)
       elif task == "glossary":
           return get_effective_config(app_config.glossary_llm, fallback)
       elif task == "translate":
           return get_effective_config(app_config.translator_llm, fallback)
       else:
           return fallback
   ```

3. **Update `test_llm_connection`** (lines 203-223)
   - Add optional `task` parameter

---

### Step 3: Modify `src/dich_truyen/crawler/pattern.py`

**Goal:** Use crawler-specific LLM config.

**Changes:**

1. **Update imports** (line 12)
   ```python
   from dich_truyen.translator.llm import LLMClient
   ```

2. **Update `PatternDiscovery.__init__`** (lines 89-96)
   - Option A (minimal change):
     ```python
     self.config = llm_config or get_config().crawler_llm
     # Apply fallback
     if not self.config.api_key:
         self.config = get_config().llm
     ```
   - Option B (cleaner, use LLMClient):
     ```python
     def __init__(self, llm_config: Optional[LLMConfig] = None):
         self._llm = LLMClient(config=llm_config, task="crawl")
         self.config = self._llm.config
     ```

---

### Step 4: Modify `src/dich_truyen/translator/glossary.py`

**Goal:** Use glossary-specific LLM config.

**Changes:**

1. **Update `generate_glossary_from_samples()`** (line 401)
   ```python
   # Before:
   llm = LLMClient()
   
   # After:
   llm = LLMClient(task="glossary")
   ```

2. **Update `extract_new_terms_from_chapter()`** (line 534)
   ```python
   # Before:
   llm = LLMClient()
   
   # After:
   llm = LLMClient(task="glossary")
   ```

---

### Step 5: Modify `src/dich_truyen/translator/engine.py`

**Goal:** Use translator-specific LLM config.

**Changes:**

1. **Update `TranslationEngine.__init__`** (line 55)
   ```python
   # Before:
   self.llm = llm or LLMClient()
   
   # After:
   self.llm = llm or LLMClient(task="translate")
   ```

2. **Update `setup_translation()`** (line 723)
   ```python
   # Before:
   llm = LLMClient()
   
   # After:
   llm = LLMClient(task="translate")
   ```

3. **Update `translate_chapter_titles()`** (line 802)
   ```python
   # Before:
   llm = LLMClient()
   
   # After:
   llm = LLMClient(task="translate")
   ```

---

### Step 6: Verify `src/dich_truyen/pipeline/streaming.py`

**Goal:** Ensure pipeline uses correct configs (mostly inherited from updated modules).

**Verification Points:**

1. `_crawl_producer()` (line 501): `PatternDiscovery()` - will now use `crawler_llm`
2. `_generate_glossary_if_needed()`: calls `generate_glossary_from_samples()` - will use `glossary_llm`
3. Translation workers: use `setup_translation()` - will use `translator_llm`

**No code changes needed** - inherits from updated modules.

---

## Files Summary

| File | Action | Description |
|------|--------|-------------|
| `src/dich_truyen/config.py` | **Modify** | Add 3 new config classes, update AppConfig, add fallback helper |
| `src/dich_truyen/translator/llm.py` | **Modify** | Add task parameter and config lookup logic |
| `src/dich_truyen/crawler/pattern.py` | **Modify** | Use crawler_llm config |
| `src/dich_truyen/translator/glossary.py` | **Modify** | Use `task="glossary"` in LLMClient calls |
| `src/dich_truyen/translator/engine.py` | **Modify** | Use `task="translate"` in LLMClient calls |
| `src/dich_truyen/pipeline/streaming.py` | **Verify** | No changes needed |

---

## Testing Plan

1. **Unit Tests:**
   - Verify each config class loads correct env vars
   - Verify fallback logic works when specific config not set
   - Verify `LLMClient(task=...)` returns correct config

2. **Integration Tests:**
   - Run pipeline with different models per phase
   - Verify crawl uses crawler model
   - Verify glossary uses glossary model
   - Verify translation uses translator model

3. **Fallback Tests:**
   - Set only `OPENAI_*` vars, verify all phases use default
   - Set only `TRANSLATOR_LLM_*`, verify translation uses it while others use default

---

## Backward Compatibility

- **Fully backward compatible**: If no new env vars are set, behavior is identical to current
- Existing `.env` files continue to work without changes
- New env vars are opt-in

---

## Implementation Order

1. `config.py` - Foundation
2. `translator/llm.py` - Core client changes
3. `crawler/pattern.py` - Crawler integration
4. `translator/glossary.py` - Glossary integration
5. `translator/engine.py` - Translation integration
6. Verify `pipeline/streaming.py` - No changes expected
7. Testing
