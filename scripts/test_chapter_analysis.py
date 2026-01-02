"""Debug script to test chapter page analysis with detailed logging."""

import asyncio
import os
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

console = Console()

# The prompt we're using
CHAPTER_PATTERN_PROMPT = """Analyze this chapter page from a Chinese novel website.

Page URL: {url}
HTML Content (truncated):
```html
{html}
```

Identify:
1. CSS selector for chapter title
2. CSS selector for chapter content
3. Elements to remove (ads, navigation, scripts)

Return ONLY valid JSON:
{{
    "title_selector": "h1",
    "content_selector": "#content",
    "elements_to_remove": ["script", "style", ".toplink", "table"]
}}
"""


async def test_chapter_analysis():
    """Test chapter page analysis with detailed debugging."""
    
    # Load environment
    load_dotenv()
    
    console.print(Panel("[bold blue]Chapter Page Analysis Debug[/bold blue]"))
    
    # Config
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    console.print(f"[bold]1. Configuration[/bold]")
    console.print(f"  API Key: {'Set' if api_key else 'NOT SET'}")
    console.print(f"  Base URL: {base_url}")
    console.print(f"  Model: {model}")
    
    if not api_key:
        console.print("[red]ERROR: No API key![/red]")
        return
    
    # Step 2: Fetch a real chapter page
    console.print(f"\n[bold]2. Fetching Chapter Page[/bold]")
    
    chapter_url = "https://www.piaotia.com/html/8/8717/5588734.html"  # First chapter
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                chapter_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            raw_content = response.content
            
            # Decode as GBK (we know this site uses GBK)
            html = raw_content.decode("gbk", errors="replace")
            
            console.print(f"  [green]Fetched OK[/green]")
            console.print(f"  Status: {response.status_code}")
            console.print(f"  Raw size: {len(raw_content)} bytes")
            console.print(f"  Decoded size: {len(html)} chars")
            
    except Exception as e:
        console.print(f"  [red]Failed to fetch: {e}[/red]")
        return
    
    # Step 3: Process HTML
    console.print(f"\n[bold]3. Processing HTML[/bold]")
    
    soup = BeautifulSoup(html, "lxml")
    
    # Show page structure
    title = soup.find("title")
    h1 = soup.find("h1")
    content_div = soup.find(id="content")
    
    console.print(f"  <title>: {title.get_text()[:50] if title else 'NOT FOUND'}...")
    console.print(f"  <h1>: {h1.get_text()[:50] if h1 else 'NOT FOUND'}...")
    console.print(f"  #content: {'FOUND' if content_div else 'NOT FOUND'}")
    if content_div:
        console.print(f"    Content preview: {content_div.get_text()[:100]}...")
    
    # Remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()
    
    truncated_html = str(soup)[:15000]
    console.print(f"  Truncated HTML size: {len(truncated_html)} chars")
    
    # Step 4: Build prompt
    console.print(f"\n[bold]4. Building Prompt[/bold]")
    
    prompt = CHAPTER_PATTERN_PROMPT.format(url=chapter_url, html=truncated_html)
    console.print(f"  Prompt size: {len(prompt)} chars")
    console.print(f"  Estimated tokens: ~{len(prompt) // 4}")
    
    # Step 5: Send to LLM
    console.print(f"\n[bold]5. Sending to LLM[/bold]")
    
    import openai
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    try:
        console.print(f"  Sending request...")
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing HTML structure. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        
        console.print(f"\n[bold]6. Response Analysis[/bold]")
        console.print(f"  Response ID: {response.id}")
        console.print(f"  Model: {response.model}")
        console.print(f"  Choices count: {len(response.choices)}")
        
        if response.choices:
            choice = response.choices[0]
            console.print(f"  Finish reason: [bold]{choice.finish_reason}[/bold]")
            console.print(f"  Message role: {choice.message.role}")
            console.print(f"  Content type: {type(choice.message.content)}")
            console.print(f"  Content is None: {choice.message.content is None}")
            
            if choice.message.content:
                content = choice.message.content
                console.print(f"  Content length: {len(content)} chars")
                console.print(f"\n[bold]Full Response:[/bold]")
                console.print(content)
            else:
                console.print(f"\n  [red bold]CONTENT IS NONE![/red bold]")
                console.print(f"  This is the bug - the LLM returned None content")
                
                # Check for refusal
                if hasattr(choice.message, 'refusal') and choice.message.refusal:
                    console.print(f"  Refusal: {choice.message.refusal}")
        
        # Usage
        if response.usage:
            console.print(f"\n[bold]7. Token Usage[/bold]")
            console.print(f"  Prompt tokens: {response.usage.prompt_tokens}")
            console.print(f"  Completion tokens: {response.usage.completion_tokens}")
            console.print(f"  Total tokens: {response.usage.total_tokens}")
            
    except openai.APIError as e:
        console.print(f"  [red]API Error: {e}[/red]")
        if hasattr(e, 'response'):
            console.print(f"  Response: {e.response}")
    except Exception as e:
        console.print(f"  [red]Error: {type(e).__name__}: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
    
    # Step 8: Try alternative approach - simpler prompt
    console.print(f"\n[bold]8. Testing Simpler Prompt[/bold]")
    
    simple_prompt = f"""Look at this HTML from {chapter_url} and tell me:
1. What CSS selector finds the chapter title? (probably h1)
2. What CSS selector finds the chapter content? (probably #content or .content)
3. What elements should be removed? (like script, style, ads)

Return JSON only:
{{"title_selector": "h1", "content_selector": "#content", "elements_to_remove": ["script"]}}
"""
    
    try:
        response2 = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": simple_prompt},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        
        content2 = response2.choices[0].message.content
        console.print(f"  Content is None: {content2 is None}")
        console.print(f"  Finish reason: {response2.choices[0].finish_reason}")
        if content2:
            console.print(f"  Response: {content2[:200]}...")
        
    except Exception as e:
        console.print(f"  [red]Error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(test_chapter_analysis())
