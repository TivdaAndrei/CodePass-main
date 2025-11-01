import argparse
import sys
import requests
import json
import os
import glob
import sqlite3
import re
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
        "model": "qwen2:0.5b",
        "prompt": prompt,
        "stream": True
    }
    
    received_data = False
    try:
        with requests.post(OLLAMA_URL, json=data, stream=True, timeout=180) as response:
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
            yield "3. If not, pull it: `ollama pull qwen2:0.5b`\n"

    except requests.exceptions.Timeout:
        yield "\n[bold red]❌ Error: Ollama request timed out (180s).[/bold red]\n"
        yield "[yellow]The model may still be processing. Try again or check Ollama logs.[/yellow]\n"
    except requests.exceptions.ConnectionError:
        yield "\n[bold red]❌ Error: Cannot connect to Ollama at localhost:11434[/bold red]\n"
        yield "[yellow]💡 Make sure Ollama is running:[/yellow]\n"
        yield "`ollama serve`\n"
    except requests.exceptions.RequestException as e:
        yield f"\n[bold red]❌ Ollama request failed: {e}[/bold red]\n"

def init_db():
    """Creează tabelele bazei de date dacă nu există."""
    conn = sqlite3.connect('reviews.db')
    cursor = conn.cursor()
    
    # Tabelul pentru problemele identificate
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        issue_desc TEXT NOT NULL,
        suggestion TEXT,
        effort TEXT,
        status TEXT NOT NULL DEFAULT 'open'
    )''')
    
    # Tabelul pentru comentarii și răspunsuri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER,
        author TEXT NOT NULL,
        comment_text TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(issue_id) REFERENCES issues(id)
    )''')
    conn.commit()
    conn.close()

def parse_and_save_review(file_path, full_review_text):
    """Parsează textul Markdown și salvează problemele individuale în DB."""
    conn = sqlite3.connect('reviews.db')
    cursor = conn.cursor()
    
    issues_found = []
    
    # Strategie: Extragere bazată pe separatoare Markdown
    # Caută secțiuni care descriu probleme
    # Pattern: "## Description:", "## Bugs?:", "**Bug?**", etc.
    
    # Split pe secțiunile de probleme
    sections = re.split(r'(?:^|\n)#{1,4}\s+(?:Bug|Issue|Problem|Description)', full_review_text, flags=re.MULTILINE | re.IGNORECASE)
    
    for section in sections[1:]:  # Skip first empty section before first match
        lines = section.strip().split('\n')
        if not lines:
            continue
        
        # Extrage descrierea din primele linii
        desc = ""
        explanation = ""
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Extrage descrierea din liniile care nu sunt headers
            if not line_stripped.startswith('#') and not line_stripped.startswith('**'):
                if len(desc) < 100:
                    desc += (" " + line_stripped).strip()
            
            # Extrage explanation
            if 'explanation' in line_stripped.lower() and ':' in line_stripped:
                idx = line_stripped.lower().find(':')
                if idx != -1:
                    explanation = line_stripped[idx+1:].strip()
        
        # Curăță descrierea
        desc = desc.replace('##', '').replace('**', '').strip()
        # Ia doar prima propoziție și max 120 caractere
        if desc:
            if '.' in desc:
                desc = desc.split('.')[0] + '.'
            desc = desc[:120]
        
        if desc and len(desc) > 10:
            suggestion = explanation if explanation else "Review and fix this issue"
            issues_found.append({
                'desc': desc,
                'suggestion': suggestion[:200],
                'effort': 'Medium'
            })
    
    # Fallback: dacă nu s-au găsit probleme, caută * **Description:**
    if not issues_found:
        lines = full_review_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if '**Description:**' in line and line.startswith('*'):
                parts = line.split('**Description:**', 1)
                if len(parts) > 1:
                    desc = parts[1].strip()
                    if len(desc) < 10 and i + 1 < len(lines):
                        desc += " " + lines[i + 1].strip()
                        i += 1
                    
                    if desc and len(desc) > 5:
                        desc = desc[:150]
                        
                        suggestion = "Review this code issue"
                        for j in range(i + 1, min(i + 10, len(lines))):
                            if '**Explanation:**' in lines[j]:
                                parts = lines[j].split('**Explanation:**', 1)
                                if len(parts) > 1:
                                    suggestion = parts[1].strip()[:200]
                                break
                        
                        issues_found.append({
                            'desc': desc,
                            'suggestion': suggestion,
                            'effort': 'Medium'
                        })
            i += 1
    
    # Salvează problemele în DB, evitând duplicate
    for issue in issues_found:
        try:
            cursor.execute(
                "SELECT id FROM issues WHERE file_path = ? AND issue_desc = ? AND status = 'open'",
                (file_path, issue['desc'])
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO issues (file_path, issue_desc, suggestion, effort, status) VALUES (?, ?, ?, ?, 'open')",
                    (file_path, issue['desc'], issue['suggestion'], issue['effort'])
                )
        except Exception as e:
            pass
                
    conn.commit()
    conn.close()

def launch_gui():
    """Lanșează interfața grafică Tkinter pentru managementul problemelor."""
    
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, simpledialog, Toplevel, Text, Scrollbar
    except ImportError:
        print("[ERROR] Tkinter is not available. GUI mode cannot run.")
        return

    conn = sqlite3.connect('reviews.db')
    cursor = conn.cursor()

    root = tk.Tk()
    root.title("CodePass - Review Manager")
    root.geometry("1200x700")

    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill="both", expand=True)

    # Title label
    title_label = ttk.Label(main_frame, text="Review history", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    # Configurare Treeview (tabel) pentru a afișa problemele
    cols = ("ID", "Status", "File", "Issue")
    tree = ttk.Treeview(main_frame, columns=cols, show="headings", height=15)
    
    for col in cols:
        tree.heading(col, text=col)
    tree.column("ID", width=50, stretch=False)
    tree.column("Status", width=100, stretch=False)
    tree.column("File", width=200)
    tree.column("Issue", width=600)

    tree.pack(fill="both", expand=True, side="top")

    # Funcție pentru a încărca/reîncărca datele
    def load_issues():
        # Șterge datele vechi
        for i in tree.get_children():
            tree.delete(i)
        
        # Încarcă datele noi din DB
        cursor.execute("SELECT id, status, file_path, issue_desc FROM issues ORDER BY status, file_path")
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)

    # Butoane de acțiuni
    btn_frame = ttk.Frame(main_frame, padding="10 0")
    btn_frame.pack(fill="x", side="bottom")

    def get_selected_issue_id():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an issue from the list.")
            return None
        return tree.item(selected, "values")[0]

    def update_status(status):
        issue_id = get_selected_issue_id()
        if issue_id:
            cursor.execute("UPDATE issues SET status = ? WHERE id = ?", (status, issue_id))
            conn.commit()
            load_issues()

    def view_comments():
        issue_id = get_selected_issue_id()
        if not issue_id:
            return

        # Creează o fereastră Toplevel (fereastră nouă)
        win = Toplevel(root)
        win.title(f"Comments for Issue #{issue_id}")
        win.geometry("600x500")

        # Afișează comentariile existente
        comments_text = Text(win, height=15, wrap="word", state="disabled")
        comments_text.pack(fill="both", expand=True, padx=10, pady=10)

        def load_comments():
            comments_text.config(state="normal")
            comments_text.delete("1.0", "end")
            cursor.execute("SELECT author, timestamp, comment_text FROM comments WHERE issue_id = ? ORDER BY timestamp", (issue_id,))
            for author, ts, text in cursor.fetchall():
                comments_text.insert("end", f"--- {author} ({ts}) ---\n{text}\n\n")
            comments_text.config(state="disabled")

        # Câmp pentru adăugare comentariu nou
        new_comment_entry = ttk.Entry(win, width=80)
        new_comment_entry.pack(fill="x", padx=10, pady="0 5")

        def add_comment():
            author = simpledialog.askstring("Author", "Enter your name:", parent=win)
            comment = new_comment_entry.get()
            if author and comment:
                cursor.execute("INSERT INTO comments (issue_id, author, comment_text) VALUES (?, ?, ?)",
                               (issue_id, author, comment))
                conn.commit()
                new_comment_entry.delete(0, "end")
                load_comments()
            elif not author:
                messagebox.showwarning("Missing Author", "Author name is required.", parent=win)
            
        add_btn = ttk.Button(win, text="Add Comment", command=add_comment)
        add_btn.pack(pady=5)
        
        load_comments()
        win.transient(root)
        win.grab_set()
        root.wait_window(win)

    ttk.Button(btn_frame, text="View/Add Comments", command=view_comments).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Mark Resolved", command=lambda: update_status("resolved")).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Mark Wontfix", command=lambda: update_status("wontfix")).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Reload", command=load_issues).pack(side="right", padx=5)

    # Încarcă datele la pornire
    load_issues()
    
    # Asigură-te că se închide conexiunea DB la ieșire
    def on_closing():
        conn.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

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
    parser.add_argument(
        '--manage',
        action='store_true',
        help="Open the GUI to manage issues and reviews"
    )
    
    args = parser.parse_args()
    
    # Initialize database at startup
    init_db()
    
    # Launch GUI if --manage flag is used
    if args.manage:
        try:
            launch_gui()
        except Exception as e:
            console.print(f"[bold red]Error launching GUI: {e}[/bold red]")
        sys.exit()
    
    # Convert "." or "./" to --directory if passed as a file argument
    if args.files and len(args.files) == 1 and args.files[0] in ('.', './'):
        args.directory = args.files[0]
        args.files = []
    
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
                # Print directly to stdout with error handling for encoding issues
                try:
                    sys.stdout.write(full_text)
                    sys.stdout.flush()
                except UnicodeEncodeError:
                    # Fallback: encode with replacement characters
                    sys.stdout.buffer.write(full_text.encode('utf-8', errors='replace'))
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
            parse_and_save_review(filepath, full_text)
    
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
                            # Print directly to stdout with error handling
                            try:
                                sys.stdout.write(full_text)
                                sys.stdout.flush()
                            except UnicodeEncodeError:
                                # Fallback: encode with replacement characters
                                sys.stdout.buffer.write(full_text.encode('utf-8', errors='replace'))
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
                        parse_and_save_review(file_path, full_text)
                except Exception as e:
                    console.print(f"[red][ERROR] Error processing file {file_path}: {e}[/red]")
            return

        if not sys.stdin.isatty():
            code_to_review = sys.stdin.read()
            if not code_to_review.strip():
                console.print("[yellow][SKIP] No Python code to review in staged diff.[/yellow]")
                sys.exit(0)

            console.print("\n[bold yellow][ANALYZE] Analyzing standard input (stdin)[/bold yellow]")
            console.print("[cyan][STREAMING] Live code review starting...[/cyan]\n")
            
            if no_emoji:
                # For pre-commit: just collect and print without Rich display
                full_text = ""
                for chunk in get_ollama_review(code_to_review, custom_rules):
                    full_text += chunk
                # Print directly to stdout with error handling
                try:
                    sys.stdout.write(full_text)
                    sys.stdout.flush()
                except UnicodeEncodeError:
                    # Fallback: encode with replacement characters
                    sys.stdout.buffer.write(full_text.encode('utf-8', errors='replace'))
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
            parse_and_save_review("stdin", full_text)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
