"""Translation style template management."""

import yaml
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console

from dich_truyen.config import get_config

console = Console()


class StyleTemplate(BaseModel):
    """Translation style template."""

    name: str = Field(description="Style name")
    description: str = Field(description="Style description in Vietnamese")
    guidelines: list[str] = Field(
        default_factory=list, description="Translation guidelines"
    )
    vocabulary: dict[str, str] = Field(
        default_factory=dict, description="Word/phrase mappings"
    )
    tone: str = Field(default="formal", description="Tone: formal, casual, archaic")
    examples: list[dict[str, str]] = Field(
        default_factory=list,
        description="Translation examples with 'chinese' and 'vietnamese' keys",
    )

    def to_prompt_format(self) -> str:
        """Format style for inclusion in translation prompt.

        Returns:
            Formatted string for prompt
        """
        lines = [f"**Phong cách: {self.description}**\n"]

        if self.guidelines:
            lines.append("### Nguyên tắc dịch thuật")
            for guideline in self.guidelines:
                lines.append(f"- {guideline}")
            lines.append("")

        if self.vocabulary:
            lines.append("### Từ vựng chuẩn")
            for chinese, vietnamese in self.vocabulary.items():
                lines.append(f"- {chinese} → {vietnamese}")
            lines.append("")

        if self.examples:
            lines.append("### Ví dụ")
            for example in self.examples[:3]:  # Limit examples
                lines.append(f"- CN: {example.get('chinese', '')}")
                lines.append(f"  VN: {example.get('vietnamese', '')}")
            lines.append("")

        return "\n".join(lines)

    def to_yaml(self, path: Path) -> None:
        """Save style template to YAML file.

        Args:
            path: Path to save YAML file
        """
        path = Path(path)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(),
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        console.print(f"[green]Saved style template to {path}[/green]")

    @classmethod
    def from_yaml(cls, path: Path) -> "StyleTemplate":
        """Load style template from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            StyleTemplate instance
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


# Built-in style templates
TIEN_HIEP_STYLE = StyleTemplate(
    name="tien_hiep",
    description="Văn phong tiên hiệp, tu chân, cổ trang",
    guidelines=[
        "Sử dụng ngôn ngữ trang trọng, cổ kính",
        "Giữ nguyên tên nhân vật theo phiên âm Hán-Việt",
        "Dùng đại từ nhân xưng cổ: 'ta', 'ngươi', 'hắn', 'y', 'nàng'",
        "Cảnh giới tu luyện giữ nguyên: Luyện Khí, Trúc Cơ, Kim Đan, Nguyên Anh...",
        "Xưng hô tôn kính: 'tiền bối', 'đạo hữu', 'sư huynh/đệ'",
        "Từ ngữ võ thuật giữ Hán-Việt: 'kiếm khí', 'linh lực', 'đan dược'",
        "Mô tả cảnh giới thiên nhiên bằng ngôn từ bay bổng, huyền ảo",
    ],
    vocabulary={
        "我": "ta",
        "你": "ngươi",
        "他": "hắn",
        "她": "nàng",
        "是": "ấy là",
        "说": "đạo",
        "想": "thầm nghĩ",
        "看": "nhìn",
        "师父": "sư phụ",
        "师兄": "sư huynh",
        "师弟": "sư đệ",
        "前辈": "tiền bối",
        "晚辈": "vãn bối",
        "道友": "đạo hữu",
        "灵气": "linh khí",
        "修炼": "tu luyện",
        "突破": "đột phá",
        "境界": "cảnh giới",
        "丹田": "đan điền",
        "神识": "thần thức",
    },
    tone="archaic",
    examples=[
        {"chinese": "你是谁？", "vietnamese": "Ngươi là ai?"},
        {"chinese": "我不知道", "vietnamese": "Ta không biết"},
        {"chinese": "他突破了", "vietnamese": "Hắn đã đột phá rồi"},
        {"chinese": "师兄，请指教", "vietnamese": "Sư huynh, xin chỉ giáo"},
    ],
)

KIEM_HIEP_STYLE = StyleTemplate(
    name="kiem_hiep",
    description="Văn phong kiếm hiệp, võ lâm, giang hồ",
    guidelines=[
        "Ngôn ngữ hào sảng, khí phách giang hồ",
        "Tên nhân vật phiên âm Hán-Việt",
        "Đại từ: 'ta', 'ngươi', 'hắn', 'gã', 'thiếu hiệp', 'nữ hiệp'",
        "Chiêu thức võ công giữ Hán-Việt: 'Giáng Long Thập Bát Chưởng'",
        "Xưng hô giang hồ: 'các hạ', 'tại hạ', 'đại hiệp', 'bang chủ'",
        "Miêu tả đánh đấu mãnh liệt, sống động",
    ],
    vocabulary={
        "我": "ta",
        "你": "ngươi",
        "他": "hắn",
        "她": "nàng",
        "大侠": "đại hiệp",
        "少侠": "thiếu hiệp",
        "女侠": "nữ hiệp",
        "在下": "tại hạ",
        "阁下": "các hạ",
        "江湖": "giang hồ",
        "武功": "võ công",
        "内力": "nội lực",
        "轻功": "khinh công",
        "剑法": "kiếm pháp",
        "掌法": "chưởng pháp",
        "拳法": "quyền pháp",
        "帮主": "bang chủ",
        "掌门": "chưởng môn",
    },
    tone="archaic",
    examples=[
        {"chinese": "在下有礼了", "vietnamese": "Tại hạ xin chào"},
        {"chinese": "阁下好武功", "vietnamese": "Các hạ võ công cao cường"},
        {"chinese": "江湖险恶", "vietnamese": "Giang hồ hiểm ác"},
    ],
)

HUYEN_HUYEN_STYLE = StyleTemplate(
    name="huyen_huyen",
    description="Văn phong huyền huyễn, kỳ ảo, ma pháp",
    guidelines=[
        "Kết hợp yếu tố đông tây phương",
        "Thuật ngữ ma pháp có thể linh hoạt Hán-Việt hoặc phiên dịch",
        "Đại từ có thể hiện đại hơn: 'ta', 'ngươi' hoặc 'tôi', 'anh'",
        "Miêu tả phép thuật, nguyên tố mang tính huyền ảo",
        "Cảnh giới có thể sáng tạo theo ngữ cảnh",
    ],
    vocabulary={
        "魔法": "ma pháp",
        "法师": "pháp sư",
        "元素": "nguyên tố",
        "魔兽": "ma thú",
        "魔核": "ma hạch",
        "斗气": "đấu khí",
        "斗者": "đấu giả",
        "斗帝": "đấu đế",
        "药剂": "dược tễ",
        "炼金": "luyện kim",
    },
    tone="formal",
    examples=[
        {"chinese": "魔法阵启动", "vietnamese": "Ma pháp trận khởi động"},
        {"chinese": "斗气化翼", "vietnamese": "Đấu khí hóa dực"},
    ],
)

DO_THI_STYLE = StyleTemplate(
    name="do_thi",
    description="Văn phong đô thị, hiện đại, nhẹ nhàng",
    guidelines=[
        "Ngôn ngữ hiện đại, tự nhiên",
        "Đại từ bình thường: 'tôi', 'bạn', 'anh/chị', 'cậu'",
        "Giọng văn gần gũi, đời thường",
        "Có thể sử dụng tiếng lóng phù hợp",
        "Thuật ngữ công nghệ, kinh doanh dịch thoáng",
    ],
    vocabulary={
        "我": "tôi",
        "你": "bạn/cậu",
        "他": "anh ấy",
        "她": "cô ấy",
        "老板": "sếp",
        "公司": "công ty",
        "手机": "điện thoại",
        "电脑": "máy tính",
        "网络": "mạng",
        "系统": "hệ thống",
    },
    tone="casual",
    examples=[
        {"chinese": "你好", "vietnamese": "Xin chào"},
        {"chinese": "谢谢", "vietnamese": "Cảm ơn"},
    ],
)

# Registry of built-in styles
BUILT_IN_STYLES: dict[str, StyleTemplate] = {
    "tien_hiep": TIEN_HIEP_STYLE,
    "kiem_hiep": KIEM_HIEP_STYLE,
    "huyen_huyen": HUYEN_HUYEN_STYLE,
    "do_thi": DO_THI_STYLE,
}


class StyleManager:
    """Manage translation style templates."""

    def __init__(self, styles_dir: Optional[Path] = None):
        """Initialize the style manager.

        Args:
            styles_dir: Directory for custom style templates
        """
        self.styles_dir = Path(styles_dir) if styles_dir else None
        self._cache: dict[str, StyleTemplate] = {}

    def list_available(self) -> list[str]:
        """List all available style names.

        Returns:
            List of style names
        """
        styles = list(BUILT_IN_STYLES.keys())

        if self.styles_dir and self.styles_dir.exists():
            for yaml_file in self.styles_dir.glob("*.yaml"):
                style_name = yaml_file.stem
                if style_name not in styles:
                    styles.append(style_name)

        return sorted(styles)

    def load(self, name: str) -> StyleTemplate:
        """Load a style template by name.

        Args:
            name: Style name (built-in or custom file)

        Returns:
            StyleTemplate instance

        Raises:
            ValueError: If style not found
        """
        # Check cache
        if name in self._cache:
            return self._cache[name]

        # Check built-in
        if name in BUILT_IN_STYLES:
            self._cache[name] = BUILT_IN_STYLES[name]
            return BUILT_IN_STYLES[name]

        # Check custom styles directory
        if self.styles_dir:
            yaml_path = self.styles_dir / f"{name}.yaml"
            if yaml_path.exists():
                style = StyleTemplate.from_yaml(yaml_path)
                self._cache[name] = style
                return style

        raise ValueError(f"Style template not found: {name}")

    def get_built_in_names(self) -> list[str]:
        """Get list of built-in style names.

        Returns:
            List of built-in style names
        """
        return list(BUILT_IN_STYLES.keys())


STYLE_GENERATION_PROMPT = """Tạo một style template dịch thuật tiểu thuyết dựa trên mô tả sau:

## Mô tả
{description}

## Yêu cầu
Tạo một style template với:
1. name: tên ngắn gọn (snake_case, tiếng Anh)
2. description: mô tả phong cách bằng tiếng Việt
3. guidelines: 5-7 nguyên tắc dịch thuật cụ thể
4. vocabulary: 10-15 cặp từ vựng quan trọng (Trung → Việt)
5. tone: formal/casual/archaic
6. examples: 3-4 ví dụ dịch mẫu

## Định dạng trả về
Trả về CHÍNH XÁC JSON object:
{{
    "name": "style_name",
    "description": "Mô tả phong cách",
    "guidelines": ["Nguyên tắc 1", "Nguyên tắc 2"],
    "vocabulary": {{"中文": "tiếng Việt"}},
    "tone": "formal",
    "examples": [{{"chinese": "中文", "vietnamese": "tiếng Việt"}}]
}}"""


async def generate_style_from_description(description: str) -> StyleTemplate:
    """Generate a style template from description using LLM.

    Args:
        description: Style description in Vietnamese

    Returns:
        Generated StyleTemplate
    """
    import json
    import re

    from dich_truyen.translator.llm import LLMClient

    llm = LLMClient()

    prompt = STYLE_GENERATION_PROMPT.format(description=description)

    response = await llm.complete(
        system_prompt="Bạn là chuyên gia dịch thuật tiểu thuyết. Trả về JSON chính xác.",
        user_prompt=prompt,
        temperature=0.5,
    )

    # Parse JSON from response
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return StyleTemplate.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            console.print(f"[red]Failed to parse style response: {e}[/red]")

    # Return a basic template if parsing fails
    return StyleTemplate(
        name="custom",
        description=description,
        guidelines=[description],
    )
