---
description: Translation style templates, YAML schema, priority loading, and how to create new styles
---

# Translation Styles

## Key Files

| File | Purpose |
|------|---------|
| `translator/style.py` | Style loading & priority logic |
| `styles/` | Custom user styles (git-tracked) |
| Built-in styles | Embedded in the package |

## Priority Loading

1. **Custom styles** in `styles/` directory — checked **first**
2. **Built-in styles** — fallback if custom not found

```python
# Style priority (in translator/style.py)
custom_path = Path("styles") / f"{name}.yaml"
if custom_path.exists():
    return load_style(custom_path)
return load_builtin_style(name)
```

## Style YAML Schema

```yaml
name: tien_hiep
description: "Tiên hiệp, tu chân style"

guidelines:
  - "Use archaic pronouns: ta, ngươi, hắn"
  - "Keep cultivation terms untranslated: Kim Đan, Luyện Khí"
  - "Maintain formal, archaic tone"

vocabulary:
  我: ta
  你: ngươi
  他: hắn
  修炼: tu luyện
  灵气: linh khí

tone: archaic

examples:
  - chinese: "你是谁？"
    vietnamese: "Ngươi là ai?"
  - chinese: "我要修炼"
    vietnamese: "Ta cần tu luyện"
```

## How to Create a New Style

```bash
# Generate template
uv run dich-truyen style generate my_style_name

# Edit the generated file
# styles/my_style_name.yaml

# List available styles
uv run dich-truyen style list
```

## Using a Style in Pipeline

```bash
uv run dich-truyen pipeline "https://..." --style tien_hiep
```
