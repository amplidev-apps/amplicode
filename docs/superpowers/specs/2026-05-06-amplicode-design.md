# AmpliCode Design Spec — 2026-05-06

## Status
Approved (with addendums)

## Overview
AmpliCode is a single-file Python CLI tool that clones the visual identity and feature set of Open-Claude-Code, adapted for NVIDIA API and optimized for Core 2 Duo hardware. It uses direct ANSI stdout for streaming output and bundles a frozen snapshot of obra/superpowers for Git-aware development workflows.

## Architecture

```
ia_terminal.py (~1800-2200 lines, single file)
│
├── CONFIG MANAGER
│   ├── ~/.amplicode_config.json (models, current_model, settings)
│   ├── ~/.amplicode/sessions/ (session JSON files)
│   ├── load_config() / save_config()
│   ├── first_run_check() → auto-launch /setup wizard
│   └── dependency_check() → verify rich, openai installed
│
├── TERMINAL UI (ANSI direct + minimal Rich)
│   ├── Header bar: [█ AmpliCode │ model │ ctx% │ time │ $cost]
│   ├── User messages: blue-bordered (ANSI color 34)
│   ├── AI messages: green-bordered (ANSI color 32)
│   ├── Streaming: sys.stdout.write(token) + flush()
│   ├── Spinners: ANSI escape sequence animation
│   └── Setup/Help panels: Rich (used sparingly)
│
├── NVIDIA API CLIENT
│   ├── OpenAI SDK with base_url="https://integrate.api.nvidia.com/v1"
│   ├── stream=True for token-by-token output
│   ├── Model config: {name, api_key, model_id}
│   ├── Error handling: auth, not_found, rate_limit, timeout
│   └── Token estimation + cost tracking
│
├── COMMAND HANDLER (39 commands)
│   ├── Core: /setup, /addmodel, /models, /readfile, /clear
│   ├── Info: /tokens, /cost, /compact, /help, /quit, /status
│   ├── Sessions: /sessions, /save, /resume, /history
│   ├── Git/Superpowers: /commit, /diff, /branch, /pr, /review
│   └── Full v2 parity: remaining 25 commands
│
├── CONTEXT MANAGER
│   ├── File context: {path: content} dict
│   ├── Conversation history: [{role, content}] list
│   ├── Auto-compaction at 80% token threshold
│   └── /readfile, /compact commands
│
└── SUPERPOWERS ENGINE (frozen snapshot)
    ├── Bundled skills/ directory (brainstorming, tdd, debugging, etc.)
    ├── Git operations via subprocess (commit, diff, branch, pr)
    ├── Auto-commit with AI-generated messages
    └── Diff analysis and review workflows
```

## Terminal UI Specification

### Header Bar (fixed at top via ANSI scrolling region)
```
█ AmpliCode │ nvidia/llama-3.1-8b-instruct │ ● 12% ctx │ ⏱ 1m30s │ $0.0023
```
- Cyan bold for "█ AmpliCode"
- Dim white for metadata
- Context percentage: green <50%, yellow 50-80%, red >80%
- Implemented with ANSI escape sequences, not Rich Live

### Message Panels
- User messages: ANSI color 34 (blue) border, title "You" in bold blue
- AI messages: ANSI color 32 (green) border, title "AmpliCode" in bold green
- Separator line: ANSI color 90 (dim) across terminal width
- Streaming output: direct stdout.write() with no buffering

### Streaming Implementation
```python
def stream_response(client, model_id, messages):
    sys.stdout.write("\033[32mAmpliCode\033[0m ")
    sys.stdout.flush()
    full_response = []
    try:
        stream = client.chat.completions.create(
            model=model_id, messages=messages, stream=True,
            max_tokens=2048, temperature=0.7
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                sys.stdout.write(token)
                sys.stdout.flush()
                full_response.append(token)
        sys.stdout.write("\n")
        return "".join(full_response), None
    except Exception as e:
        return None, str(e)
```

## NVIDIA API Integration

### Configuration Structure
```json
{
  "models": [
    {
      "name": "Llama 3.1 8B",
      "api_key": "nvapi-...",
      "model_id": "nvidia/llama-3.1-8b-instruct"
    }
  ],
  "current_model": "Llama 3.1 8B",
  "settings": {
    "max_tokens": 2048,
    "temperature": 0.7,
    "auto_compact": true
  }
}
```

### Model ID Validation on /addmodel
- Test API key + model_id with a minimal request (max_tokens=1)
- Show available models from NVIDIA docs
- Accept custom model IDs with format validation

### Error Handling
| Error Type | Behavior |
|------------|----------|
| AuthenticationError | Clear message: "Invalid API key. Check your NVIDIA API key." |
| NotFoundError | "Model ID not found. Verify the model ID format (e.g., nvidia/llama-3.1-8b-instruct)" |
| RateLimitError | "Rate limited. Waiting 5s and retrying..." then retry once |
| Timeout | "Request timed out. Check your connection." |
| General Exception | "API error: {str(e)}" |

## 39 Commands (Full v2 Parity)

### Session & Config
| Command | Description |
|---------|-------------|
| `/setup` | Run setup wizard (first-run or reconfigure) |
| `/addmodel` | Add new NVIDIA model interactively |
| `/models` | List and switch between saved models |
| `/status` | Show current config, model, token usage |

### File & Context
| Command | Description |
|---------|-------------|
| `/readfile <path>` | Add file to context |
| `/compact` | Compact context window (keep last 10 messages) |
| `/clear` | Clear history and context |
| `/tokens` | Show estimated token usage |
| `/cost` | Show estimated session cost |

### Sessions (NEW)
| Command | Description |
|---------|-------------|
| `/sessions` | List all saved sessions with timestamps |
| `/save [name]` | Save current session to ~/.amplicode/sessions/ |
| `/resume <name/id>` | Resume a saved session (restore context + history) |
| `/history` | Show current session message history |

### Git & Superpowers (NEW)
| Command | Description |
|---------|-------------|
| `/commit` | Auto-generate commit message and commit changes |
| `/diff [file]` | Show git diff with AI analysis |
| `/branch <name>` | Create and switch to new branch |
| `/pr [title]` | Create pull request with AI-generated description |
| `/review` | Request code review of current changes |

### Full v2 Parity Commands
| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/quit` or `/exit` | Exit AmpliCode |
| `/undo` | Undo last file edit |
| `/redo` | Redo undone edit |
| `/bash <cmd>` | Run bash command |
| `/search <query>` | Web search integration |
| `/fetch <url>` | Fetch URL content |
| `/todo` | Show/manage todo list |
| `/agents` | List/manage custom agents |
| `/skills` | List available superpowers skills |
| `/hook` | Manage hook events |
| `/permissions` | Manage permission modes |
| `/sandbox` | Toggle sandbox mode |
| `/mcp` | Manage MCP servers |
| `/telemetry` | Toggle telemetry |
| `/theme` | Change color theme |
| `/export` | Export conversation |
| `/import` | Import conversation |
| `/reset` | Factory reset config |
| `/version` | Show version info |
| `/update` | Check for updates |

## Sessions Persistence

### Storage
- Directory: `~/.amplicode/sessions/`
- Format: JSON files named `{timestamp}-{name}.json`
- Each file contains:
  ```json
  {
    "id": "2026-05-06-14-30-00-myproject",
    "name": "myproject",
    "created": "2026-05-06T14:30:00",
    "model": "Llama 3.1 8B",
    "conversation_history": [...],
    "context_files": {...},
    "total_tokens": 1234,
    "session_cost": 0.0023
  }
  ```

### /sessions Command
- List all sessions sorted by date (newest first)
- Show: name, date, model used, token count
- Allow deletion with /sessions delete <name>

### /save Command
- Usage: `/save [name]`
- If no name: auto-generate from timestamp
- Save current conversation_history + context_files + metadata
- Confirm: "Session 'myproject' saved to ~/.amplicode/sessions/"

### /resume Command
- Usage: `/resume <name>` or `/resume <id>`
- Restore conversation_history and context_files
- Show: "Resumed session 'myproject' (12 messages, 3 files)"

## Superpowers Integration

### Bundled Skills (Frozen Snapshot)
The following skills from obra/superpowers are bundled directly in the AmpliCode file as a frozen dictionary:

```python
SUPERPOWERS_SKILLS = {
    "brainstorming": {"prompt": "...", "files": [...]},
    "test-driven-development": {"prompt": "...", "files": [...]},
    "systematic-debugging": {"prompt": "...", "files": [...]},
    "writing-plans": {"prompt": "...", "files": [...]},
    "executing-plans": {"prompt": "...", "files": [...]},
    # ... all 14 skills
}
```

### Git Operations via Subprocess
```python
def git_commit(message=None):
    if not message:
        # Use AI to generate commit message from diff
        diff = subprocess.run(["git", "diff", "--staged"], capture_output=True)
        message = generate_commit_message(diff.stdout)
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", message])

def git_diff(file=None):
    cmd = ["git", "diff"]
    if file:
        cmd.append(file)
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout.decode()

def git_branch(name):
    subprocess.run(["git", "checkout", "-b", name])

def git_pr(title=None):
    # Use gh CLI if available, else instruct user
    if not title:
        diff = git_diff()
        title = generate_pr_title(diff)
    subprocess.run(["gh", "pr", "create", "--title", title, "--body", "..."])
```

### /commit Command Flow
1. Check if in a git repo (look for .git)
2. Run `git status` to see changes
3. If no staged changes, run `git add .`
4. Generate commit message using AI (context: diff + recent history)
5. Show message and ask for confirmation
6. Commit with generated message

## Error-Proofing Strategy

### 1. Dependency Check (startup)
```python
REQUIRED_PACKAGES = ["rich", "openai"]
missing = []
for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print(f"Missing dependencies: {', '.join(missing)}")
    print("Install with: pip install rich openai")
    sys.exit(1)
```

### 2. First-Run Setup
```python
def ensure_config():
    if not os.path.exists(CONFIG_PATH):
        print("First run detected. Starting setup wizard...")
        cmd_setup()
```

### 3. API Validation on /addmodel
```python
def validate_model(api_key, model_id):
    try:
        client = openai.OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        return True, None
    except Exception as e:
        return False, str(e)
```

### 4. Graceful API Failures
- All API calls wrapped in try/except
- Clear error messages with actionable advice
- Rate limit: wait 5s and retry once
- Timeout: show message, allow retry with /retry

### 5. Input Validation
- File paths: check os.path.exists() before reading
- Model IDs: validate format (contains "/")
- API keys: check non-empty, starts with "nvapi-"
- Numeric inputs: wrap in try/except ValueError

## File Structure (Single File)

```
ia_terminal.py
│
├── [Lines 1-30]   Imports + Shebang
├── [Lines 31-50]  Constants (colors, paths, URLs)
├── [Lines 51-100] Config manager (load/save/validate)
├── [Lines 101-200] ANSI Terminal UI helpers
├── [Lines 201-350] NVIDIA API client (stream + non-stream)
├── [Lines 351-500] Session persistence (save/resume/list)
├── [Lines 501-700] Superpowers skills (frozen snapshot)
├── [Lines 701-900] Git operations (commit/diff/pr/etc)
├── [Lines 901-1500] Command handler (39 commands)
├── [Lines 1501-1700] Main loop (REPL)
└── [Lines 1701-1800] Entry point + error handling
```

## Implementation Notes

1. **Core 2 Duo Optimization**: No threading for UI, no Rich Live, direct ANSI writes
2. **Self-contained**: Single file, frozen superpowers, no runtime downloads
3. **Portable**: Works on any Linux with Python 3.8+ and pip
4. **Git Integration**: Uses subprocess, not pygit2 (reduces dependencies)
5. **Session Files**: JSON for human readability and debugging
6. **Streaming**: Token-by-token to stdout, no buffering

## Success Criteria

- [ ] Single file `ia_terminal.py` that runs with `python3 ia_terminal.py`
- [ ] Visual clone of Open-Claude-Code (header, borders, colors)
- [ ] Streaming output via direct ANSI stdout writes
- [ ] All 39 commands implemented and working
- [ ] /sessions with save/resume/list functionality
- [ ] Superpowers skills bundled and invocable via /skills
- [ ] Git operations: /commit, /diff, /pr working
- [ ] Error-proof: dependency check, first-run setup, API validation
- [ ] Config persists to ~/.amplicode_config.json
- [ ] Runs smoothly on Core 2 Duo hardware
