# AI Code Reviewer

This is a command-line tool that uses a local AI model (via Ollama) to review your Python code. It can be run manually on files or directories, or be integrated as a `pre-commit` hook to automatically review your changes.

## Features

*   **AI-Powered Code Review**: Get feedback on your code regarding bugs, performance, style, and documentation.
*   **Local First**: Runs with a local Ollama instance, so your code never leaves your machine.
*   **Flexible Input**: Analyze code from files, standard input, or entire directories.
*   **Custom Rules**: Extend the AI's review with your own custom linting rules.
*   **Pre-commit Integration**: Automatically review staged Python files before you commit.

## Prerequisites

*   Python 3.6+
*   [Ollama](https://ollama.ai/) installed and running.
*   A model pulled for Ollama to use (e.g., `ollama pull gemma:2b`).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **(Optional) Set up the pre-commit hook:**
    ```bash
    pre-commit install
    ```

## Usage

### Command-Line

*   **Analyze a specific file:**
    ```bash
    python review.py my_file.py
    ```

*   **Analyze multiple files:**
    ```bash
    python review.py file1.py file2.py
    ```

*   **Analyze a whole directory recursively:**
    ```bash
    python review.py --directory ./my_project
    ```

*   **Use with custom rules:**
    ```bash
    python review.py --rules my_rules.txt my_file.py
    ```

*   **Analyze code from stdin:**
    ```bash
    cat my_file.py | python review.py
    ```

### Pre-commit Hook

Once installed (`pre-commit install`), the tool will automatically run on any staged (`.py`) files when you run `git commit`. The review will be printed to your console.

## How It Works

The `review.py` script sends the content of the specified file(s) to the Ollama API with a detailed prompt asking it to act as a code reviewer. The response from the AI is then streamed to the console and formatted as Markdown.

When used as a pre-commit hook, `pre-commit` passes the names of the staged files to the script.
