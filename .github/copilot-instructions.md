# Git MCP - AI Coding Instructions

## Project Overview
**gitMCP** is a Model Context Protocol (MCP) server that exposes Git repository operations as tools for AI agents. It extracts structured Git metadata (status, diffs, change summaries) and makes them available via FastMCP with built-in safety features (redaction, truncation).

**Key Purpose**: Enable AI agents to understand repository state without direct Git access; useful for code review, understanding changes, and contextual analysis.

## Architecture & Components

### Core Architecture Pattern
The project uses a **modular registration pattern** where each feature area (status, diff, snippet, explainer) is in a separate module that:
1. Implements async Git command runners via [git_runner.py](git_runner.py)
2. Parses raw Git output into structured dicts
3. Exposes one or more MCP tools via a `register(mcp: FastMCP)` function
4. Gets registered in [server.py](server.py) during startup

### Key Modules

**[git_runner.py](git_runner.py)** - Foundation layer
- Single async function `run_git(repo_path, args, timeout_s=8)` that executes all Git commands
- Environment: Disables pagers (`GIT_PAGER=""`, `GIT_TERMINAL_PROMPT="0"`) to ensure clean output
- Validation: Checks Git executable exists via `shutil.which("git")`
- All stderr logged; non-zero exit raises `RuntimeError`

**[git_status.py](git_status.py)** - Repository status parsing
- `parse_porcelain_status()`: Parses `git status --porcelain=2 --branch` into structured dict with:
  - `head`: branch name, OID, is_initial flag
  - `tracking`: upstream ref, ahead/behind counts
  - `working_tree`: lists of untracked, staged, unstaged, conflict files
- Handles porcelain v2 edge cases (rename records `2 XY...`, conflicts `u XY...`)
- Tool: `repo_status(repo_path)` returns complete status JSON

**[git_diff.py](git_diff.py)** - Change analysis
- `parse_numstat()`: Maps `--numstat` output to {path: {additions, deletions, is_binary}}
- `parse_name_status()`: Maps `--name-status` output to {path: {change_type, old_path}}
- Tools: `repo_diff_summary(repo_path, scope)` for staged/unstaged overview; includes top files by impact
- Helper: `_diff_summary_for_scope()` used by other modules

**[git_diff_snippet.py](git_diff_snippet.py)** - Bounded diff delivery
- `get_diff_snippet_raw()`: Runs `git diff --unified=0` with optional path filters
- `apply_redactions()`: Scans for secrets (AWS keys, private keys, password= patterns) → `[REDACTED]`
- `truncate_text()`: Enforces max_lines + max_bytes to prevent huge responses
- Tool: `repo_diff_snippet(repo_path, scope, paths, max_lines=50, max_bytes=10000)` with safety defaults

**[git_change_explainer.py](git_change_explainer.py)** - Orchestrator
- `repo_change_explainer()`: Combines status + diff summaries + evidence snippets into one JSON bundle
- Smart path picking: Uses top changed files from diff summary to populate evidence
- Tool parameters: `include="both"` (staged/unstaged), `max_files=3`, `max_lines=250`, `max_bytes=30000`

### Data Flow
```
MCP Client Request
        ↓
repo_change_explainer (or direct status/diff tools)
        ↓
    [Orchestrator validates repo, fetches status + diffs]
        ↓
    [Redaction → Truncation → JSON serialization]
        ↓
    MCP Tool Response (structured dict)
```

## Critical Patterns & Conventions

### 1. Git Output Handling
- **Porcelain v2 Format**: All status queries use `--porcelain=2 --branch` (stable, parseable format)
- **Raw Tab Separation**: Diff output parsed by splitting on tabs; paths may contain spaces (handled defensively)
- **Always `--no-pager`**: Prevents interactive output that breaks async subprocess communication

### 2. Error Handling
- Missing Git executable → `RuntimeError("Git not found in PATH")`
- Git command failure (non-zero exit) → `RuntimeError(f"git {args} failed: {stderr}")`
- Invalid repo path → `ValueError("repo_path does not exist or is not a directory")`
- Callers should catch and wrap these for MCP response context

### 3. Safety & Redaction
- **[git_diff_snippet.py](git_diff_snippet.py) patterns** (lines ~55-60):
  - AWS keys: `AKIA[0-9A-Z]{16}`
  - Private key blocks: `-----BEGIN.*PRIVATE KEY-----`
  - Secrets: `password|passwd|secret|token|api_key` followed by `:=` assignment
- Truncation is applied **after** redaction to ensure secrets don't leak via size limits
- All applied patterns logged for transparency

### 4. Tool Response Schema
All tools return dicts with consistent structure:
```python
{
    "repo": {"path": repo_path},
    "summary": {...},           # tool-specific data
    "errors": {...}             # if validation fails
}
```
- Avoid exceptions in tool handlers; wrap in response dict when possible

## Development Workflow

### Running the Server
```bash
python server.py
# Starts MCP server on stdio; connect via Claude Desktop or similar client
```

### Testing a Single Module
Each module can be tested independently:
```bash
python -c "
import asyncio
from git_runner import run_git
result = asyncio.run(run_git('.', ['status', '--short']))
print(result)
"
```

### Adding a New Git Tool
1. Create new module (e.g., `git_blame.py`)
2. Implement async functions to fetch/parse Git output
3. Define `register(mcp: FastMCP)` with `@mcp.tool()` decorator
4. Import and call in [server.py](server.py): `register_git_blame(mcp)`

### Dependencies
- **mcp[cli]>=1.25.0**: FastMCP server framework
- **httpx>=0.28.1**: For MCP over HTTP (if needed)
- **Python >=3.10**: Async/await syntax, pattern matching

## Project-Specific Quirks

1. **Logging to stderr**: Server logs go to `sys.stderr` (MCP best practice; stdout is reserved for protocol)
2. **Redaction is conservative**: Only flags known patterns; custom secrets in arbitrary code won't redact
3. **Scope must be explicit**: Diff tools require `scope="staged"` or `scope="unstaged"`; no "all" mode (too large)
4. **Path quoting in porcelain v2**: Filenames with special chars are quoted; parser handles this via tab splitting
5. **Comments in Hebrew**: Some code has Hebrew comments (line ~24 in git_runner.py); don't assume English-only

## Key Files to Know
- [server.py](server.py) - Entry point, tool registration
- [git_runner.py](git_runner.py) - All Git subprocess logic
- [git_status.py](git_status.py) - Porcelain v2 parsing reference
- [git_diff_snippet.py](git_diff_snippet.py) - Redaction/truncation reference (security-sensitive)
- [pyproject.toml](pyproject.toml) - Dependencies and Python version requirement
