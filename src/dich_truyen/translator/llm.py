"""OpenAI-compatible LLM client wrapper."""

import asyncio
from typing import Optional

from rich.console import Console

from dich_truyen.config import LLMConfig, get_config

console = Console()


class LLMClient:
    """OpenAI-compatible LLM client with retry logic."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM client.

        Args:
            config: LLM configuration, uses global config if None
        """
        self.config = config or get_config().llm
        self._client = None

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
                    console.print(f"[yellow]LLM attempt {attempt + 1} failed: {e}[/yellow]")
                    await asyncio.sleep(delay)

        raise last_error or RuntimeError("LLM request failed")

    async def translate(
        self,
        text: str,
        style_prompt: str,
        glossary_prompt: str = "",
        context: Optional[str] = None,
    ) -> str:
        """Translate text from Chinese to Vietnamese.

        Args:
            text: Chinese text to translate
            style_prompt: Style guidelines for translation
            glossary_prompt: Glossary terms to use
            context: Previous context for continuity

        Returns:
            Translated Vietnamese text
        """
        system_prompt = self._build_translation_system_prompt(style_prompt)
        user_prompt = self._build_translation_user_prompt(
            text, glossary_prompt, context
        )

        return await self.complete(system_prompt, user_prompt)

    def _build_translation_system_prompt(self, style_prompt: str) -> str:
        """Build the system prompt for translation."""
        return f"""Bạn là dịch giả chuyên nghiệp chuyên dịch tiểu thuyết Trung Quốc sang tiếng Việt.

## Phong cách dịch thuật
{style_prompt}

## Yêu cầu
- Dịch chính xác, giữ nguyên ý nghĩa và cảm xúc của bản gốc
- Sử dụng ngôn ngữ tiếng Việt tự nhiên, mượt mà
- Giữ nguyên cấu trúc đoạn văn
- KHÔNG thêm giải thích hay chú thích
- CHỈ trả về bản dịch, không có gì khác"""

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


async def test_llm_connection(config: Optional[LLMConfig] = None) -> bool:
    """Test if the LLM connection is working.

    Args:
        config: LLM configuration

    Returns:
        True if connection successful
    """
    try:
        client = LLMClient(config)
        response = await client.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'hello' in Vietnamese.",
            max_retries=1,
            max_tokens=10,
        )
        return len(response) > 0
    except Exception as e:
        console.print(f"[red]LLM connection failed: {e}[/red]")
        return False
