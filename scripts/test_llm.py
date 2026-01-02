"""Debug script to test LLM connection and response."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

console = Console()


async def test_llm():
    """Test LLM connection with detailed debugging."""
    
    # Load environment
    load_dotenv()
    
    console.print(Panel("[bold blue]LLM Debug Test[/bold blue]"))
    
    # 1. Check environment variables
    console.print("\n[bold]1. Environment Variables[/bold]")
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    console.print(f"  OPENAI_API_KEY: {'[green]Set[/green]' if api_key else '[red]Not set[/red]'}")
    if api_key:
        console.print(f"    Length: {len(api_key)} chars")
        console.print(f"    Prefix: {api_key[:10]}...")
    console.print(f"  OPENAI_BASE_URL: {base_url}")
    console.print(f"  OPENAI_MODEL: {model}")
    
    if not api_key:
        console.print("\n[red]ERROR: OPENAI_API_KEY is not set![/red]")
        console.print("Please set it in .env file")
        return
    
    # 2. Test OpenAI client
    console.print("\n[bold]2. OpenAI Client Test[/bold]")
    
    try:
        import openai
        console.print(f"  OpenAI SDK version: {openai.__version__}")
        
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        console.print(f"  Client created: [green]OK[/green]")
        console.print(f"  Base URL: {client.base_url}")
        
    except Exception as e:
        console.print(f"  [red]Failed to create client: {e}[/red]")
        return
    
    # 3. Test simple completion
    console.print("\n[bold]3. Simple Completion Test[/bold]")
    
    try:
        console.print(f"  Sending request to model: {model}")
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, World!' in Vietnamese."},
            ],
            max_tokens=50,
            temperature=0.7,
        )
        
        console.print(f"  Response object: {type(response)}")
        console.print(f"  Response ID: {response.id}")
        console.print(f"  Model used: {response.model}")
        console.print(f"  Choices count: {len(response.choices)}")
        
        if response.choices:
            choice = response.choices[0]
            console.print(f"  Choice 0 finish_reason: {choice.finish_reason}")
            console.print(f"  Message role: {choice.message.role}")
            console.print(f"  Message content: {choice.message.content}")
            console.print(f"  Content type: {type(choice.message.content)}")
            
            if choice.message.content:
                console.print(f"\n  [green]SUCCESS![/green] Response: {choice.message.content}")
            else:
                console.print(f"\n  [red]WARNING: Content is None or empty![/red]")
        else:
            console.print("  [red]No choices in response![/red]")
            
        # Print usage
        if response.usage:
            console.print(f"\n  Usage:")
            console.print(f"    Prompt tokens: {response.usage.prompt_tokens}")
            console.print(f"    Completion tokens: {response.usage.completion_tokens}")
            console.print(f"    Total tokens: {response.usage.total_tokens}")
        
    except openai.AuthenticationError as e:
        console.print(f"  [red]Authentication Error: {e}[/red]")
        console.print("  Check your API key is correct")
    except openai.RateLimitError as e:
        console.print(f"  [red]Rate Limit Error: {e}[/red]")
    except openai.APIConnectionError as e:
        console.print(f"  [red]Connection Error: {e}[/red]")
        console.print(f"  Check the base URL: {base_url}")
    except openai.APIError as e:
        console.print(f"  [red]API Error: {e}[/red]")
        console.print(f"  Status code: {e.status_code if hasattr(e, 'status_code') else 'N/A'}")
        console.print(f"  Response: {e.response if hasattr(e, 'response') else 'N/A'}")
    except Exception as e:
        console.print(f"  [red]Unexpected Error: {type(e).__name__}: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
    
    # 4. Test pattern discovery prompt (the one that failed)
    console.print("\n[bold]4. Pattern Discovery Prompt Test[/bold]")
    
    try:
        test_html = """
        <div class="centent">
            <ul>
                <li><a href="001.html">第一章</a></li>
                <li><a href="002.html">第二章</a></li>
            </ul>
        </div>
        """
        
        prompt = """Analyze this HTML and return ONLY valid JSON:
{
    "title_selector": "h1",
    "content_selector": "#content",
    "elements_to_remove": ["script", "style"]
}

HTML:
""" + test_html
        
        console.print("  Sending pattern analysis request...")
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an HTML analyzer. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        
        content = response.choices[0].message.content
        console.print(f"  Content type: {type(content)}")
        console.print(f"  Content is None: {content is None}")
        console.print(f"  Content value: {repr(content)}")
        
        if content:
            console.print(f"\n  [green]Pattern response received![/green]")
            console.print(f"  {content[:200]}...")
        else:
            console.print(f"\n  [red]Content is None - this is the bug![/red]")
            console.print("  The model returned an empty response")
            console.print("  This might be due to content filtering or model issues")
            
    except Exception as e:
        console.print(f"  [red]Error: {type(e).__name__}: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(test_llm())
