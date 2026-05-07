# AmpliCode v2.0 Design Spec — Full Claude Code v2 Parity

## Status
Approved (Single Large Design)

## Overview
AmpliCode v2.0 achieves 1:1 feature parity with Claude Code v2 (open-claude-code) in a single Python file (`ia_terminal.py`), optimized for Core 2 Duo hardware.

## Architecture (Single File: ~6000 lines)

```
ia_terminal.py
├── Imports (rich, openai, subprocess, os, sys, json, re, typing)
├── Constants (colors, paths, version)
├── Global State (console, history, context, tokens, permissions, hooks, settings)
├── Command Line Args (parse ., dir, -h, -v)
├── Config Manager (load/save/validate ~/.amplicode_config.json)
├── ANSI Terminal UI (header, messages, streaming, spinner)
├── NVIDIA API Client (stream, non-stream, error handling)
├── Session Persistence (save/resume/list/delete ~/.amplicode/sessions/)
├── File Tools (write_file, patch_file, read_file, run_terminal_command)
├── Permission System (6 modes: bypass, acceptEdits, auto, default, dontAsk, plan)
├── Hooks Engine (7 events: PreToolUse, PostToolUse, Stop, etc.)
├── MCP Client (4 transports: stdio, SSE, WebSocket, streamable-HTTP)
├── Settings Chain (5 layers: user, project, local, managed, feature_flags)
├── Custom Agents (JSON + Markdown frontmatter)
├── Superpowers Skills (frozen snapshot of 14 skills)
├── Git Operations (commit, diff, pr, branch, review)
├── Command Handler (39+ commands)
└── Main Loop (REPL with dynamic context injection)
```

## Section 1: Permission System ✅ (Designed)

**6 Permission Modes:**
- `bypass`: All tools auto-approved (no prompts)
- `acceptEdits`: File edits auto-approved, others prompt
- `auto`: Known-safe tools auto-approved, others prompt
- `default`: Most tools require user confirmation
- `dontAsk`: Deny rather than prompt
- `plan`: Read-only mode, no mutations

**Implementation:**
```python
PERMISSION_MODES = ['bypass', 'acceptEdits', 'auto', 'default', 'dontAsk', 'plan']
permission_mode = 'default'
tool_allowlist = set()
tool_denylist = set()

def check_tool_permission(tool_name, tool_input):
    # Implementation from Section 1 design
    # Returns (allowed: bool, reason: str)
```

**/permissions command:**
- `/permissions` - Show current mode
- `/permissions bypass` - Set mode
- `/permissions allow <tool>` - Add to allowlist
- `/permissions deny <tool>` - Add to denylist

## Section 2: Hooks Engine

**7 Hook Events:**
- `PreToolUse` - Before tool execution (can block)
- `PostToolUse` - After tool execution
- `PreToolUseFailure` - Tool validation failed
- `PostToolUseFailure` - Tool execution failed
- `Notification` - System notification
- `Stop` - Generation stopped
- `SessionStart` - Session initialized

**Hook Types:**
- `command` - Execute shell command, parse JSON stdout
- `http` - POST to webhook URL, parse JSON response

**Implementation:**
```python
HOOKS = {
    'PreToolUse': [],
    'PostToolUse': [],
    # ...
}

def fire_hook(event, tool_name, tool_input):
    for hook in HOOKS.get(event, []):
        if hook['type'] == 'command':
            result = subprocess.run(hook['command'], capture_output=True, text=True)
            if result.stdout:
                decision = json.loads(result.stdout)
                if decision.get('decision') == 'block':
                    return False, decision.get('reason', 'Blocked by hook')
        elif hook['type'] == 'http':
            # POST to hook['url'] with tool info
            pass
    return True, None
```

## Section 3: MCP Client

**4 Transports:**
- `stdio` - Spawn child process, communicate via stdin/stdout
- `SSE` - Server-Sent Events over HTTP (legacy)
- `WebSocket` - Bidirectional WebSocket
- `Streamable HTTP` - New MCP transport (POST with SSE response)

**Protocol Methods:**
- `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `completion/complete`

**Implementation:**
```python
class MCPClient:
    def __init__(self):
        self.servers = {}  # name -> server config
    
    def add_server(self, name, transport, command=None, url=None):
        # Add MCP server with specified transport
        pass
    
    def list_tools(self):
        # Aggregate tools from all servers
        # Namespace as mcp__server__tool
        pass
```

**/mcp commands:**
- `/mcp` - List configured servers
- `/mcp add <name> <transport> <command_or_url>` - Add server
- `/mcp remove <name>` - Remove server

## Section 4: Settings Chain

**5 Layers (later overrides earlier):**
1. **User settings**: `~/.amplicode/settings.json`
2. **Project settings**: `.amplicode/settings.json` (committed to repo)
3. **Local settings**: `.amplicode/settings.local.json` (gitignored)
4. **Managed settings**: Enterprise policy (remote fetch)
5. **Feature flags**: Runtime feature toggles

**76 Settings Properties:**
- `allowedTools`, `deniedTools`
- `mcpServers`
- `hookEvents`
- `permissionMode`
- `modelPreferences`
- `apiConfiguration`
- `uiBehavior`

**Implementation:**
```python
def load_settings():
    settings = {}
    # Layer 1: User settings
    if os.path.exists(os.path.expanduser('~/.amplicode/settings.json')):
        with open(...) as f:
            settings.update(json.load(f))
    
    # Layer 2: Project settings
    if os.path.exists('.amplicode/settings.json'):
        with open(...) as f:
            settings.update(json.load(f))
    
    # Layer 3: Local settings
    # Layer 4: Managed settings
    # Layer 5: Feature flags
    
    return settings
```

## Section 5: Custom Agents

**Agent Definition (JSON + Markdown):**
```json
{
  "name": "research-agent",
  "description": "Agent for research tasks",
  "model": "nvidia/llama-3.1-8b-instruct",
  "tools": ["read_file", "web_search"],
  "systemPrompt": "You are a research agent..."
}
```

**Implementation:**
```python
def load_agents():
    agents = {}
    agent_dir = os.path.join(WORK_DIR, '.amplicode', 'agents')
    if not os.path.isdir(agent_dir):
        return agents
    
    for filename in os.listdir(agent_dir):
        if filename.endswith('.md'):
            with open(os.path.join(agent_dir, filename)) as f:
                content = f.read()
                # Parse YAML frontmatter
                # Store agent
    return agents
```

**/agents commands:**
- `/agents` - List available agents
- `/agents run <name> <task>` - Run an agent

## Section 6: Enhanced Tools (25+ total)

**Current Tools (8):**
- `write_file`, `patch_file`, `read_file`, `run_terminal_command`
- `list_sessions`, `save_session`, `resume_session`, `delete_session`

**New Tools (17+):**
- `Bash` - Execute bash commands
- `Read` - Read file with line numbers
- `Edit` - Edit file (replaces text)
- `MultiEdit` - Multiple edits in one operation
- `Glob` - Pattern matching for files
- `Grep` - Pattern matching in file contents
- `LS` - List directory contents
- `NotebookEdit` - Edit Jupyter notebooks
- `Agent` - Run sub-agent
- `WebFetch` - Fetch URL content
- `WebSearch` - Search the web
- `TodoWrite` - Manage todo list
- Plus MCP tools namespaced as `mcp__server__tool`

## Section 7: Superpowers Integration (Enhanced)

**Current (basic):**
- 14 skills embedded as frozen dict
- `/skillname` invokes skill

**Enhanced:**
- Skills can define `prompt`, `files`, `dependencies`
- Skills can chain: brainstorming → writing-plans → executing-plans
- Visual companion for brainstorming (browser-based)
- Auto-activation: detect skill need from context

## Success Criteria (v2.0)

- [ ] Single file `ia_terminal.py` (~6000 lines)
- [ ] All 39+ commands from v2 implemented
- [ ] Permission System (6 modes) working
- [ ] Hooks Engine (7 events) working
- [ ] MCP Client (4 transports) working
- [ ] Settings Chain (5 layers) working
- [ ] Custom Agents working
- [ ] 25+ tools working
- [ ] Superpowers Skills enhanced
- [ ] Full 1:1 parity with Claude Code v2
- [ ] README.md updated with all features
- [ ] Core 2 Duo optimized (ANSI direct, no bloat)

## Implementation Order

1. **Permission System** (depends on nothing)
2. **Hooks Engine** (depends on Permission System)
3. **MCP Client** (depends on nothing)
4. **Settings Chain** (depends on nothing)
5. **Custom Agents** (depends on nothing)
6. **Enhanced Tools** (depends on Permission System)
7. **Superpowers Enhanced** (depends on nothing)
8. **Update README.md**
9. **Test on Core 2 Duo**
10. **Commit and Push**

---
**AmpliCode v2.0** — *Full Claude Code v2 Parity, Core 2 Duo Optimized*
