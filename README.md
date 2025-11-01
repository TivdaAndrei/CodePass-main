# CodePass - AI-Powered Code Review System

A powerful command-line tool that uses local AI (via Ollama) to provide intelligent, real-time code reviews. Designed for developers who want AI-assisted code quality without cloud dependencies.

## ✨ Features

- **🚀 Live Streaming Reviews**: Watch code analysis appear in real-time as the AI generates it
- **🔍 Incremental Analysis**: Reviews only code diffs in pre-commit mode for fast feedback
- **🏠 Local-First Privacy**: Your code never leaves your machine - powered by local Ollama
- **📁 Flexible Input Modes**: 
  - Single files or multiple files
  - Entire directories (recursive)
  - Standard input (pipes/streams)
  - Git diffs (automatic via pre-commit)
- **⚙️ Customizable Rules**: Add team-specific linting rules for personalized reviews
- **🔗 Git Integration**: Automatic pre-commit hook for seamless code review workflow
- **💻 Cross-Platform**: Windows, macOS, and Linux support
- **🎨 Rich Terminal Output**: Beautiful formatted reviews with Markdown support
- **🗄️ Issue Database**: SQLite database automatically tracks all issues from reviews
- **🖥️ Issue Management GUI**: Tkinter interface to view, comment, and manage issues

## 📊 Analysis Dimensions

Each review analyzes code across four key areas:

1. **Bugs & Security** - Identifies vulnerabilities, logic errors, and unsafe patterns
2. **Performance & Architecture** - Detects inefficiencies and architectural issues
3. **Standards & Clean Code** - Checks PEP 8 compliance, readability, and best practices
4. **Documentation** - Suggests missing docstrings and comment improvements

## 🔧 Prerequisites

- **Python** 3.8 or higher
- **Ollama** ([install here](https://ollama.ai/)) - Local AI runtime
- **Git** (for pre-commit integration)
- **Model**: Pull a model with `ollama pull gemma:2b` (or another supported model)

## 📦 Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd CodePass-main
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Ollama

In a separate terminal, start the Ollama server:

```bash
ollama serve
```

### 4. (Optional) Install Pre-Commit Hook

Enable automatic code review on every commit:

```bash
pre-commit install
```

## 🚀 Usage

### Command-Line Usage

**Review a single file:**
```bash
python review.py myfile.py
```

**Review multiple files:**
```bash
python review.py file1.py file2.py file3.py
```

**Review current directory (shortcut):**
```bash
python review.py .
```

**Review an entire directory:**
```bash
python review.py --directory ./src
```

**Review from stdin (pipe):**
```bash
cat myfile.py | python review.py
```

**Use custom linting rules:**
```bash
python review.py myfile.py --rules team_rules.txt
```

**Enable debug mode:**
```bash
python review.py myfile.py --verbose
```

**Disable emoji output (pre-commit mode):**
```bash
python review.py myfile.py --no-emoji
```

**Launch issue management GUI:**
```bash
python review.py --manage
```

### GUI Features

The issue management interface provides:

- **Issue Viewer**: Table showing all detected issues with file, status, and description
- **Comments**: Add and view comments on each issue with author tracking
- **Status Management**: Mark issues as `Open`, `Resolved`, or `Wontfix`
- **Real-Time Updates**: Auto-loads new issues from the database
- **Easy Navigation**: Click issues to view details and manage comments

**Workflow:**
1. Run code review: `python review.py myfile.py`
2. Issues automatically saved to database
3. Open GUI: `python review.py --manage`
4. Review issues, add comments, and track progress

Once installed, the hook automatically runs on every commit:

```bash
git add myfile.py
git commit -m "Add new feature"
# → Pre-commit hook runs automatically
# → Reviews only the staged Python diffs
# → Passes or blocks commit based on analysis
```

**Key Benefits:**
- ✅ Reviews only changed lines (incremental)
- ✅ Runs before commit to catch issues early
- ✅ No configuration needed after `pre-commit install`
- ✅ Skips non-Python files automatically

## 📋 Examples

### Example 1: Review a New Function

```bash
$ python review.py utils.py
📄 Analyzing 1 file(s)...

🔍 Analyzing: utils.py
⏳ Streaming live code review...

## Code Analysis

**Bugs & Security:**
* **[Issue]:** Missing input validation
* **[Explanation]:** Function accepts user input without validation
* **[Remediation Effort]:** Low
* **[Suggested Fix]:** Add type hints and validate inputs

...
✓ Review complete
```

### Example 2: Pre-Commit Review

```bash
$ git add feature.py
$ git commit -m "Add new feature"

AI Code Review (Local)...................Passed
[main a1b2c3d] Add new feature
 1 file changed, 45 insertions(+)
```

### Example 3: Directory Analysis

```bash
$ python review.py --directory ./src
[DIR] Analyzing directory: ./src
Found 5 Python file(s) to review

[ANALYZE] src/models.py
[STREAMING] Live code review starting...
...

[OK] Review complete
```

## 🔧 Configuration

### Pre-Commit Configuration (`.pre-commit-config.yaml`)

The hook is configured in `.pre-commit-config.yaml`:

```yaml
repos:
-   repo: local
    hooks:
    -   id: ai-code-review
        name: AI Code Review (Local)
        entry: python review.py --no-emoji
        language: system
        types: [python]
        pass_filenames: false
```

**Key settings:**
- `pass_filenames: false` - Enables incremental review (diffs only)
- `types: [python]` - Only reviews Python files
- `--no-emoji` - Disables emojis in pre-commit output for compatibility

### Custom Rules

Create a `rules.txt` file with your team's rules:

```
1. Always use type hints for function parameters
2. Maximum line length: 100 characters
3. All functions must have docstrings
4. No bare except clauses
```

Then use it:

```bash
python review.py myfile.py --rules rules.txt
```

## 🏗️ Project Structure

```
CodePass-main/
├── review.py                 # Main review script with CLI & GUI
├── .pre-commit-config.yaml   # Pre-commit hook configuration
├── reviews.db               # SQLite database (auto-created)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── test_mic.py              # Example/test file
```

## 🔌 How It Works

1. **Input Processing**: Reads code from files, directories, or stdin
2. **AI Analysis**: Sends code to local Ollama model with detailed prompt
3. **Live Streaming**: Displays results in real-time as they're generated
4. **Formatted Output**: Presents analysis as readable Markdown
5. **Database Storage**: Automatically extracts and saves issues to SQLite
6. **GUI Management**: View and manage all issues through the GUI
7. **Pre-Commit Integration**: Automatically runs on staged commits

## 🐛 Troubleshooting

### Issue: "Error: Could not connect to the Ollama server"

**Solution**: Make sure Ollama is running:
```bash
ollama serve
```

### Issue: "Model not found"

**Solution**: Pull the required model:
```bash
ollama list                    # See available models
ollama pull gemma:2b          # Install a model
```

### Issue: "Ollama request timed out"

**Solution**: The default timeout is 180 seconds. If you're still getting timeouts:
1. Check if Ollama is running: `ollama serve`
2. Check if the model is loaded: `ollama list`
3. Consider waiting longer - first runs may take time to load the model
4. If recurring, your system might be resource-constrained

### Issue: Unicode encoding errors on Windows

**Solution**: The `--no-emoji` flag handles this:
```bash
python review.py myfile.py --no-emoji
```

## 📈 Performance

- **Single file review**: ~5-15 seconds (depends on file size and model)
- **Pre-commit review**: <10 seconds for typical diffs (only reviews changed lines)
- **Directory review**: ~30 seconds for 10-20 files (reviews each file sequentially)
- **Request timeout**: 180 seconds (allows for slower model initialization)

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Support for more programming languages
- Additional AI models (beyond Ollama)
- Enhanced diff visualization
- Performance optimizations
- Additional analysis dimensions

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Powered by [Ollama](https://ollama.ai/) for local AI inference
- Uses [pre-commit](https://pre-commit.com/) for Git integration

---

**Made with ❤️ for code quality**
