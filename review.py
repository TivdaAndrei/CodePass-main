import argparse
import sys
import requests
import json
import os
import glob
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.syntax import Syntax

def get_ollama_review(code_snippet: str, custom_rules: str = ""):
    """
    Sends a code snippet to Ollama for review and streams the response in real-time.
    """
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    custom_rules_section = ""
    if custom_rules:
        custom_rules_section = f"""
---
ADDITIONAL CUSTOM RULES:
The following rules are critical for our team. 
Please enforce them with high priority:
{custom_rules}
---
"""

    prompt = f"""You are 'CodeGuardian', an elite software engineering assistant.
Return the response ONLY in Markdown format.
Analyze the code on the following dimensions:

* **Bugs & Security**
* **Performance & Architecture**
* **Standards & Clean Code**
* **Documentation Suggestions**

For EACH issue found, provide:

* **[Issue]:** Description.
* **[Explanation]:** Why it's a problem.
* **[Remediation Effort]:** Low / Medium / High.
* **[Suggested Fix (diff)]:** (if possible)
{custom_rules_section}
Begin analysis on the following code snippet:
---
```python
{code_snippet}
```
---
"""

    data = {
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": True
    }
    
    received_data = False
    try:
        with requests.post(OLLAMA_URL, json=data, stream=True, timeout=60) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    received_data = True
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        content_chunk = chunk.get("response", "")
                        if content_chunk:
                            yield content_chunk
                    except json.JSONDecodeError:
                        pass
        
        if not received_data:
            yield "\n[bold red]❌ Error: No response received from Ollama.[/bold red]\n"
            yield "[yellow]💡 Troubleshooting tips:[/yellow]\n"
            yield "1. Is Ollama running? Try: `ollama serve` in another terminal\n"
            yield "2. Is the model available? Try: `ollama list`\n"
            yield "3. If not, pull it: `ollama pull gemma:2b`\n"

    except requests.exceptions.Timeout:
        yield "\n[bold red]❌ Error: Ollama request timed out (60s).[/bold red]\n"
        yield "[yellow]The model may still be processing. Try again.[/yellow]\n"
    except requests.exceptions.ConnectionError:
        yield "\n[bold red]❌ Error: Cannot connect to Ollama at localhost:11434[/bold red]\n"
        yield "[yellow]💡 Make sure Ollama is running:[/yellow]\n"
        yield "`ollama serve`\n"
    except requests.exceptions.RequestException as e:
        yield f"\n[bold red]❌ Ollama request failed: {e}[/bold red]\n"

def main():
    """
    Reads code from a file, stdin, or a directory and sends it to Ollama for review.
    """
    # Parse just the --no-emoji flag first to decide console settings
    import sys as _sys_temp
    no_emoji = '--no-emoji' in _sys_temp.argv
    console = Console(no_color=no_emoji, force_terminal=not no_emoji)
    parser = argparse.ArgumentParser(description="AI Code Review CLI Tool")
    parser.add_argument('files', nargs='*', help="One or more files to analyze. If omitted, reads from stdin.")
    parser.add_argument('--directory', type=str, help='The directory to be recursively analyzed for .py files')
    parser.add_argument(
        '--rules', 
        type=argparse.FileType('r'), 
        help="A .txt file with custom linting rules."
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Show debug information"
    )
    parser.add_argument(
        '--no-emoji',
        action='store_true',
        help="Disable emoji output (useful for pre-commit hooks)"
    )
    
    args = parser.parse_args()
    
    custom_rules = ""
    if args.rules:
        with args.rules as f:
            custom_rules = f.read()
    
    if args.verbose:
        console.print("[cyan]DEBUG: Debug Mode ON[/cyan]")
        console.print(f"[cyan]Connecting to: http://localhost:11434/api/generate[/cyan]")

    # LOGICA IF (Noul caz pentru Pipeline)
    if args.directory:
        console.print(f"[bold cyan][DIR] Analyzing directory: {args.directory}[/bold cyan]")
        
        python_files = glob.glob(os.path.join(args.directory, '**/*.py'), recursive=True)

        if not python_files:
            console.print("[yellow][WARN] No .py files found in the specified directory.[/yellow]")
            return

        console.print(f"[cyan]Found {len(python_files)} Python file(s) to review[/cyan]\n")

        for filepath in python_files:
            console.print(f"\n[bold yellow][ANALYZE] {filepath}[/bold yellow]")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    code_to_review = f.read()
            except Exception as e:
                console.print(f"[red][ERROR] Error reading file {filepath}: {e}[/red]")
                continue

            if not code_to_review.strip():
                console.print("[italic][SKIP] Empty file, skipping...[/italic]")
                continue

            # Live reviewing with real-time streaming
            console.print("[cyan][STREAMING] Live code review starting...[/cyan]")
            if no_emoji:
                # For pre-commit: just collect and print without Rich formatting
                full_text = ""
                for chunk in get_ollama_review(code_to_review, custom_rules):
                    full_text += chunk
                # Print directly to stdout to avoid Rich encoding issues
                sys.stdout.write(full_text)
                sys.stdout.flush()
            else:
                # Normal mode: Live streaming display
                with Live("", console=console, refresh_per_second=8) as live:
                    full_text = ""
                    chunk_count = 0
                    for chunk in get_ollama_review(code_to_review, custom_rules):
                        chunk_count += 1
                        full_text += chunk
                        # Update display in real-time
                        live.update(full_text)
            
            if args.verbose:
                console.print(f"\n[cyan]DEBUG: Received {chunk_count} chunks[/cyan]")
            
            console.print("[green][OK] Review complete[/green]")
    
    # ELSE LOGIC (Existing functionality)
    else:
        if args.files:
            console.print(f"[bold cyan][FILES] Analyzing {len(args.files)} file(s)...[/bold cyan]\n")
            
            for file_path in args.files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        filepath_str = file_path
                        console.print(f"\n[bold yellow][ANALYZE] {filepath_str}[/bold yellow]")
                        code_to_review = f.read()

                        if not code_to_review.strip():
                            console.print("[italic][SKIP] Empty file or input, skipping...[/italic]")
                            continue
                        
                        console.print("[cyan][STREAMING] Live code review starting...[/cyan]")
                        # Live reviewing with real-time updates
                        if no_emoji:
                            # For pre-commit: just collect and print without Rich display
                            full_text = ""
                            for chunk in get_ollama_review(code_to_review, custom_rules):
                                full_text += chunk
                            # Print directly to stdout to avoid Rich encoding issues
                            sys.stdout.write(full_text)
                            sys.stdout.flush()
                        else:
                            # Normal mode: Live streaming display
                            with Live("", console=console, refresh_per_second=8) as live:
                                full_text = ""
                                chunk_count = 0
                                for chunk in get_ollama_review(code_to_review, custom_rules):
                                    chunk_count += 1
                                    full_text += chunk
                                    # Update display in real-time
                                    live.update(full_text)
                                
                                if args.verbose:
                                    console.print(f"\n[cyan]DEBUG: Received {chunk_count} chunks[/cyan]")
                        
                        console.print("[green][OK] Review complete[/green]")
                except Exception as e:
                    console.print(f"[red][ERROR] Error processing file {file_path}: {e}[/red]")
            return

        if not sys.stdin.isatty():
            code_to_review = sys.stdin.read()
            if not code_to_review.strip():
                console.print("[red]Error: No code provided to analyze from stdin.[/red]")
                sys.exit(1)

            console.print("\n[bold yellow][ANALYZE] Analyzing standard input (stdin)[/bold yellow]")
            console.print("[cyan][STREAMING] Live code review starting...[/cyan]\n")
            
            if no_emoji:
                # For pre-commit: just collect and print without Rich display
                full_text = ""
                for chunk in get_ollama_review(code_to_review, custom_rules):
                    full_text += chunk
                # Print directly to stdout to avoid Rich encoding issues
                sys.stdout.write(full_text)
                sys.stdout.flush()
            else:
                # Normal mode: Live streaming display
                with Live("", console=console, refresh_per_second=8) as live:
                    full_text = ""
                    chunk_count = 0
                    for chunk in get_ollama_review(code_to_review, custom_rules):
                        chunk_count += 1
                        full_text += chunk
                        # Update display in real-time
                        live.update(full_text)
                
                if args.verbose:
                    console.print(f"\n[cyan]DEBUG: Received {chunk_count} chunks[/cyan]")
            
            console.print("\n[green][OK] Review complete[/green]")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
