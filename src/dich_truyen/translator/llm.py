"""OpenAI-compatible LLM client wrapper."""

import asyncio
from typing import Literal, Optional

import structlog

from dich_truyen.config import LLMConfig, get_config, get_effective_llm_config

logger = structlog.get_logger()

# Task types for LLM client configuration
TaskType = Literal["crawl", "glossary", "translate", "default"]


class LLMClient:
    """OpenAI-compatible LLM client with retry logic."""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        task: Optional[TaskType] = None,
    ):
        """Initialize the LLM client.

        Args:
            config: LLM configuration, uses global config if None
            task: Task type for automatic config selection (crawl, glossary, translate)
                  If both config and task are provided, config takes precedence.
        """
        if config:
            self.config = config
        else:
            self.config = self._get_config_for_task(task or "default")
        self._client = None

    def _get_config_for_task(self, task: TaskType) -> LLMConfig:
        """Get effective LLM config for a specific task.
        
        This method retrieves the task-specific config (e.g., crawler_llm for crawl task)
        and merges it with the default llm config for any unset values.
        
        Args:
            task: The task type (crawl, glossary, translate, default)
            
        Returns:
            LLMConfig with effective values for the task
        """
        app_config = get_config()
        fallback = app_config.llm
        
        if task == "crawl":
            return get_effective_llm_config(app_config.crawler_llm, fallback, "Crawler")
        elif task == "glossary":
            return get_effective_llm_config(app_config.glossary_llm, fallback, "Glossary")
        elif task == "translate":
            return get_effective_llm_config(app_config.translator_llm, fallback, "Translator")
        else:
            # Default task - log direct usage
            logger.debug(
                "llm_config_default",
                model=fallback.model,
                api_key=fallback.api_key[:8] + "..." if len(fallback.api_key) > 8 else "***",
                base_url=fallback.base_url,
                max_tokens=fallback.max_tokens,
                temperature=fallback.temperature,
            )
            return fallback

    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a completion request with retry logic.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            max_retries: Number of retry attempts
            temperature: Override temperature (uses config default if None)
            max_tokens: Override max tokens (uses config default if None)

        Returns:
            Generated text content
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature or self.config.temperature,
                    max_tokens=max_tokens or self.config.max_tokens,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = (2**attempt) * 1  # Exponential backoff: 1, 2, 4 seconds
                    logger.warning("llm_retry", attempt=attempt + 1, error=str(e))
                    await asyncio.sleep(delay)

        raise last_error or RuntimeError("LLM request failed")

    async def translate(
        self,
        text: str,
        style_prompt: str,
        glossary_prompt: str = "",
        context: Optional[str] = None,
        narrative_state: Optional[dict] = None,
    ) -> str:
        """Translate text from Chinese to Vietnamese.

        Args:
            text: Chinese text to translate
            style_prompt: Style guidelines for translation
            glossary_prompt: Glossary terms to use
            context: Previous context for continuity
            narrative_state: Optional narrative state (speaker, pronouns) from previous chunk

        Returns:
            Translated Vietnamese text
        """
        system_prompt = self._build_translation_system_prompt(style_prompt, narrative_state)
        user_prompt = self._build_translation_user_prompt(
            text, glossary_prompt, context
        )

        return await self.complete(system_prompt, user_prompt)

    def _build_translation_system_prompt(self, style_prompt: str, narrative_state: Optional[dict] = None) -> str:
        """Build the system prompt for translation."""
        base_prompt = f"""Bạn là dịch giả chuyên nghiệp chuyên dịch tiểu thuyết Trung Quốc sang tiếng Việt.

## Phong cách dịch thuật
{style_prompt}

## Yêu cầu
- Dịch chính xác, giữ nguyên ý nghĩa và cảm xúc của bản gốc
- Sử dụng ngôn ngữ tiếng Việt tự nhiên, mượt mà
- Giữ nguyên cấu trúc đoạn văn
- KHÔNG thêm giải thích hay chú thích
- Các thuật ngữ có dạng `中文<Tiếng Việt>` PHẢI dịch đúng như trong ngoặc nhọn
- Giữ nguyên bản dịch đã chỉ định, KHÔNG sửa đổi"""

        # Add state tracking instructions if state is provided
        if narrative_state:
            speaker = narrative_state.get("speaker", "")
            pronouns = narrative_state.get("pronouns", {})
            
            state_info = "\n\n## Trạng thái trước đó (giữ nhất quán)"
            if speaker:
                state_info += f"\n- Người đang nói: {speaker}"
            if pronouns:
                pronoun_list = ", ".join([f"{cn}→{vi}" for cn, vi in pronouns.items()])
                state_info += f"\n- Đại từ: {pronoun_list}"
            
            base_prompt += state_info
        
        # Add state output request
        base_prompt += """\n\n## Đầu ra
- Trả về CHÍNH XÁC bản dịch
- Sau đó thêm dòng `---STATE---` và JSON:
  {"speaker": "tên người đang nói", "pronouns": {"Tên_CN": "đại_từ_VN"}}"""
        
        return base_prompt

    def _build_translation_user_prompt(
        self,
        text: str,
        glossary_prompt: str,
        context: Optional[str],
    ) -> str:
        """Build the user prompt for translation."""
        parts = []

        if glossary_prompt:
            parts.append(f"## Bảng thuật ngữ (BẮT BUỘC sử dụng)\n{glossary_prompt}\n")

        if context:
            parts.append(f"## Bản dịch đoạn trước (tham khảo để giữ mạch văn)\n{context}\n")

        parts.append(f"## Văn bản cần dịch\n{text}")

        return "\n".join(parts)

    async def translate_title(self, title: str, title_type: str = "book") -> str:
        """Translate a title from Chinese to Vietnamese.

        Args:
            title: Chinese title to translate
            title_type: Type of title ("book", "chapter", "author")

        Returns:
            Translated Vietnamese title
        """
        if title_type == "author":
            system_prompt = """Bạn là dịch giả chuyên nghiệp. Hãy phiên âm tên tác giả Trung Quốc sang tiếng Việt.
Quy tắc:
- Phiên âm Hán-Việt chuẩn xác
- VD: 烽火戏诸侯 -> Phong Hỏa Hí Chư Hầu
- CHỈ trả về tên đã phiên âm, không giải thích"""
        elif title_type == "chapter":
            system_prompt = """Bạn là dịch giả chuyên nghiệp. Hãy dịch tiêu đề chương tiểu thuyết Trung Quốc sang tiếng Việt.
Quy tắc:
- Dịch ý nghĩa, giữ văn phong tiên hiệp/kiếm hiệp
- VD: 第一章 惊蛰 -> Chương 1: Kinh Trập
- CHỈ trả về tiêu đề đã dịch, không giải thích"""
        else:  # book
            system_prompt = """Bạn là dịch giả chuyên nghiệp. Hãy dịch tên tiểu thuyết Trung Quốc sang tiếng Việt.
Quy tắc:
- Phiên âm Hán-Việt hoặc dịch nghĩa tùy ngữ cảnh
- VD: 剑来 -> Kiếm Lai
- CHỈ trả về tên đã dịch, không giải thích"""

        user_prompt = f"Dịch: {title}"

        return await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=100,
        )

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


async def test_llm_connection(
    config: Optional[LLMConfig] = None,
    task: Optional[TaskType] = None,
) -> bool:
    """Test if the LLM connection is working.

    Args:
        config: LLM configuration (takes precedence if provided)
        task: Task type for automatic config selection

    Returns:
        True if connection successful
    """
    try:
        client = LLMClient(config=config, task=task)
        response = await client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'hello' in Vietnamese.",
            max_retries=1,
            max_tokens=10,
        )
        return len(response) > 0
    except Exception as e:
        logger.error("llm_connection_failed", error=str(e))
        return False
