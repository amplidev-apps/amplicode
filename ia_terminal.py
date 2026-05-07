#!/usr/bin/env python3
"""
AmpliCode - IA Oficial da AmpliDEV (Divisão de Software da AmpliGroup)
Clone funcional do Open-Claude-Code com integração NVIDIA API
Otimizado para hardware Core 2 Duo (Zero-Bloat, ANSI direto)

Instalação:
    pip install rich openai
    chmod +x ia_terminal.py
    ./ia_terminal.py

Ou crie um alias:
    alias amplicode='python3 /caminho/para/ia_terminal.py'
"""

# ==================== IMPORTS ====================
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Rich imports (verificadas na inicialização)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.box import ROUNDED, SIMPLE
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    import openai
except ImportError as e:
    print(f"Erro: Dependência faltando: {e}")
    print("Instale com: pip install rich openai")
    sys.exit(1)

# ==================== FILE TOOLS ====================

def write_file(path, content):
    """
    Escreve/sobrescreve arquivo com conteúdo.
    Retorna (sucesso, mensagem).
    """
    try:
        # Garante que o diretório existe
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True, f"Arquivo '{path}' salvo com sucesso ({len(content)} chars)"
    except IOError as e:
        return False, f"Erro ao escrever arquivo: {e}"

def patch_file(path, search_text, replace_text):
    """
    Edição cirúrgica: substitui search_text por replace_text.
    Retorna (sucesso, mensagem).
    """
    if not os.path.exists(path):
        return False, f"Arquivo '{path}' não encontrado."

    try:
        with open(path, 'r', encoding='utf-8') as f:
            original = f.read()

        if search_text not in original:
            return False, "Texto de busca não encontrado no arquivo."

        modified = original.replace(search_text, replace_text, 1)  # Apenas primeira ocorrência

        if modified == original:
            return False, "Nenhuma alteração realizada."

        with open(path, 'w', encoding='utf-8') as f:
            f.write(modified)

        return True, f"Arquivo '{path}' patchado com sucesso"

    except IOError as e:
        return False, f"Erro ao patchar arquivo: {e}"

def read_file_tool(path):
    """
    Lê arquivo para contexto dinâmico (usado pela IA).
    Retorna (sucesso, conteudo ou erro).
    """
    if not os.path.exists(path):
        return False, f"Arquivo '{path}' não encontrado."

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if len(content) > 10000:
            content = content[:10000] + "\n... (truncado)"

        return True, content
    except IOError as e:
        return False, f"Erro ao ler arquivo: {e}"

def run_terminal_command(command):
    """
    Executa comando de shell com segurança.
    Pede confirmação do usuário antes de executar.
    Retorna (sucesso, saida ou erro).
    """
    console.print()
    console.print(f"[bold yellow]IA quer executar:[/bold yellow] {command}")
    
    if not Confirm.ask("Deseja executar este comando?", default=True):
        return False, "Comando cancelado pelo usuário."

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        return True, output or "Comando executado (sem saída)."
    except subprocess.TimeoutExpired:
        return False, "Comando excedeu o tempo limite (30s)."
    except Exception as e:
        return False, f"Erro ao executar: {e}"

# ==================== PERMISSION SYSTEM ====================

# Permission modes
PERMISSION_MODES = ['bypass', 'acceptEdits', 'auto', 'default', 'dontAsk', 'plan']
PERMISSION_MODE = 'default'  # Can be changed via /permissions command
TOOL_ALLOW_LIST = set()  # Tools auto-approved
TOOL_DENY_LIST = set()   # Tools always denied

def check_tool_permission(tool_name, tool_input=None):
    """
    Check if tool can be executed based on permission mode.
    Returns (allowed: bool, reason: str).
    """
    if PERMISSION_MODE == 'bypass':
        return True, None  # All tools auto-approved

    if PERMISSION_MODE == 'plan':
        # Read-only: deny mutations
        if tool_name in ['write_file', 'patch_file', 'bash', 'run_terminal_command']:
            return False, "Read-only mode (plan)"
        return True, None

    if tool_name in TOOL_DENY_LIST:
        return False, f"Tool '{tool_name}' is in deny list"

    if tool_name in TOOL_ALLOW_LIST:
        return True, None

    if PERMISSION_MODE == 'acceptEdits':
        if tool_name in ['write_file', 'patch_file']:
            return True, None  # Auto-approve edits
        # Fall through to user prompt

    if PERMISSION_MODE == 'auto':
        # Known-safe tools auto-approved
        if tool_name in ['read_file', 'list_sessions', 'show_history', 'ls', 'glob', 'grep']:
            return True, None
        # Fall through to user prompt

    if PERMISSION_MODE == 'dontAsk':
        return False, "Tool execution denied (dontAsk mode)"

    # mode == 'default' or fallthrough: ask user
    console.print()
    console.print(f"[yellow]Ferramenta '{tool_name}' quer executar:[/yellow]")
    if tool_input:
        preview = str(tool_input)[:200]
        console.print(f"[dim]{preview}[/dim]")

    response = Prompt.ask("Permitir? (s/n/a=always/d=deny always)", default='s')

    if response.lower() == 'a':
        TOOL_ALLOW_LIST.add(tool_name)
        return True, None
    elif response.lower() == 'd':
        TOOL_DENY_LIST.add(tool_name)
        return False, f"Tool '{tool_name}' added to deny list"
    elif response.lower() == 's':
        return True, None
    else:
        return False, "User denied"

def cmd_permissions(mode=None):
    """Handle /permissions command"""
    global PERMISSION_MODE

    if not mode:
        console.print(f"[dim]Modo atual: {PERMISSION_MODE}[/dim]")
        console.print(f"[dim]Allow list: {TOOL_ALLOW_LIST}[/dim]")
        console.print(f"[dim]Deny list: {TOOL_DENY_LIST}[/dim]")
        return

    if mode in PERMISSION_MODES:
        PERMISSION_MODE = mode
        console.print(f"[green]✓ Modo alterado para: {mode}[/green]")
    elif mode.startswith('allow '):
        tool = mode[6:].strip()
        TOOL_ALLOW_LIST.add(tool)
        console.print(f"[green]✓ '{tool}' adicionado à allow list[/green]")
    elif mode.startswith('deny '):
        tool = mode[5:].strip()
        TOOL_DENY_LIST.add(tool)
        console.print(f"[green]✓ '{tool}' adicionado à deny list[/green]")
    else:
        console.print(f"[red]Modo inválido. Use: {', '.join(PERMISSION_MODES)}[/red]")

# ==================== HOOKS ENGINE ====================
HOOKS = {
    'PreToolUse': [],      # Before any tool execution
    'PostToolUse': [],     # After tool execution
    'PostEdit': [],       # After file edits
    'PostSessionStart': [], # After session loads
    'PostSessionEnd': [],  # Before session ends
    'Notification': [],    # On notifications
    'Stop': []            # On stop/interrupt
}

def register_hook(event, func):
    """Register a hook function for an event"""
    if event in HOOKS:
        HOOKS[event].append(func)
        console.print(f"[dim]Hook registered: {event}[/dim]")

def run_hooks(event, **kwargs):
    """Execute all hooks for an event"""
    if event not in HOOKS:
        return
    for hook in HOOKS[event]:
        try:
            hook(**kwargs)
        except Exception as e:
            console.print(f"[yellow]Hook error ({event}): {e}[/yellow]")

def cmd_hooks(action=None, event=None):
    """Manage hooks: list, run, clear"""
    if not action:
        console.print("[dim]Events disponíveis:[/dim]")
        for evt in HOOKS:
            console.print(f"  {evt}: {len(HOOKS[evt])} hooks")
        return

    if action == "list":
        if event and event in HOOKS:
            console.print(f"[dim]Hooks para {event}:[/dim]")
            for h in HOOKS[event]:
                console.print(f"  {h.__name__}")
        else:
            for evt, hooks in HOOKS.items():
                console.print(f"[dim]{evt}:[/dim] {len(hooks)} hooks")
    elif action == "clear":
        if event:
            HOOKS[event] = []
            console.print(f"[green]✓ Hooks limpos para {event}[/green]")
        else:
            for evt in HOOKS:
                HOOKS[evt] = []
            console.print("[green]✓ Todos os hooks limpos[/green]")

# ==================== MCP CLIENT ====================
MCP_SERVERS = {}  # name -> config
MCP_TOOLS = {}    # server -> tools mapping

def mcp_add_server(name, command_or_url, transport='stdio', env=None):
    """Add an MCP server"""
    config = {
        'transport': transport,
        'command' if transport == 'stdio' else 'url': command_or_url,
        'env': env or {}
    }
    MCP_SERVERS[name] = config
    console.print(f"[green]✓ MCP server '{name}' adicionado ({transport})[/green]")

def mcp_remove_server(name):
    """Remove an MCP server"""
    if name in MCP_SERVERS:
        del MCP_SERVERS[name]
        if name in MCP_TOOLS:
            del MCP_TOOLS[name]
        console.print(f"[green]✓ MCP server '{name}' removido[/green]")
    else:
        console.print(f"[yellow]Server '{name}' não encontrado[/yellow]")

def mcp_list_servers():
    """List configured MCP servers"""
    if not MCP_SERVERS:
        console.print("[dim]Nenhum MCP server configurado[/dim]")
        return
    for name, config in MCP_SERVERS.items():
        transport = config['transport']
        target = config.get('command', config.get('url', 'N/A'))
        console.print(f"[dim]{name}[/dim]: {transport} - {target}")

def mcp_connect_server(name):
    """Connect to an MCP server and fetch its tools/prompts/resources"""
    if name not in MCP_SERVERS:
        console.print(f"[red]Server '{name}' não encontrado[/red]")
        return False

    config = MCP_SERVERS[name]
    transport = config['transport']

    try:
        if transport == 'stdio':
            # Launch process and communicate via stdio
            cmd = config['command'].split()
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **config.get('env', {})}
            )
            # TODO: Implement MCP protocol handshake
            console.print(f"[dim]Conectando via stdio: {cmd}[/dim]")
            MCP_TOOLS[name] = {'tools': [], 'prompts': [], 'resources': []}
            return True

        elif transport in ('sse', 'streamable-http'):
            # HTTP-based transports
            url = config['url']
            console.print(f"[dim]Conectando via {transport}: {url}[/dim]")
            # TODO: Implement HTTP MCP client
            MCP_TOOLS[name] = {'tools': [], 'prompts': [], 'resources': []}
            return True

        elif transport == 'in-process':
            # Python module loaded in-process
            module = config['command']
            console.print(f"[dim]Carregando in-process: {module}[/dim]")
            # TODO: Import and inspect module
            MCP_TOOLS[name] = {'tools': [], 'prompts': [], 'resources': []}
            return True

    except Exception as e:
        console.print(f"[red]Erro conectando '{name}': {e}[/red]")
        return False

def cmd_mcp(action=None, arg=None):
    """Manage MCP servers"""
    if not action:
        mcp_list_servers()
        return

    if action == "add":
        # Parse: /mcp add <name> <transport> <command-or-url>
        parts = arg.split() if arg else []
        if len(parts) < 3:
            console.print("[red]Uso: /mcp add <name> <transport> <command-or-url>[/red]")
            console.print("[dim]Transports: stdio, sse, streamable-http, in-process[/dim]")
            return
        name, transport, target = parts[0], parts[1], ' '.join(parts[2:])
        mcp_add_server(name, target, transport)

    elif action == "remove" or action == "rm":
        mcp_remove_server(arg)

    elif action == "connect":
        if mcp_connect_server(arg):
            console.print(f"[green]✓ Conectado a '{arg}'[/green]")

    elif action == "list" or action == "ls":
        mcp_list_servers()

    else:
        console.print(f"[red]Ação inválida: {action}[/red]")
        console.print("[dim]Ações: add, remove, connect, list[/dim]")

# ==================== SETTINGS CHAIN ====================
# 5 layers: defaults < project (.amplicode/settings.json) < user (~/.amplicode/settings.json) < session < command-line

SETTINGS = {
    'model': None,
    'temperature': 0.7,
    'max_tokens': 4096,
    'stream': True,
    'auto_commit': False,
    'permission_mode': 'default',
    'theme': 'default',
    'hooks': {},
    'mcp_servers': {},
}

def load_settings_file(path):
    """Load settings from a JSON file"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[yellow]Erro lendo {path}: {e}[/yellow]")
        return {}

def save_settings_file(path, settings):
    """Save settings to a JSON file"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        console.print(f"[red]Erro salvando {path}: {e}[/red]")
        return False

def load_all_settings():
    """Load settings from all 5 layers"""
    global SETTINGS

    # Layer 1: Defaults (already in SETTINGS)

    # Layer 2: Project settings
    project_settings = load_settings_file('.amplicode/settings.json')

    # Layer 3: User settings
    user_settings = load_settings_file(os.path.expanduser('~/.amplicode/settings.json'))

    # Layer 4: Session settings (loaded elsewhere when session loads)

    # Merge: project < user (user overrides project)
    merged = {**project_settings, **user_settings}

    # Apply merged settings
    for key, value in merged.items():
        if key in SETTINGS:
            SETTINGS[key] = value

    # Layer 5: Command-line args (applied at startup)

def cmd_settings(action=None, key=None, value=None):
    """Manage settings across all layers"""
    if not action:
        console.print("[dim]Settings atuais:[/dim]")
        for k, v in SETTINGS.items():
            console.print(f"  {k}: {v}")
        return

    if action == "get":
        if key in SETTINGS:
            console.print(f"[dim]{key}:[/dim] {SETTINGS[key]}")
        else:
            console.print(f"[red]Setting '{key}' não encontrado[/red]")

    elif action == "set":
        if not key or not value:
            console.print("[red]Uso: /settings set <key> <value>[/red]")
            return
        # Convert value to appropriate type
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.isdigit():
            value = int(value)
        elif value.replace('.', '').isdigit():
            value = float(value)

        SETTINGS[key] = value
        console.print(f"[green]✓ {key} = {value}[/green]")

        # Save to user settings
        user_path = os.path.expanduser('~/.amplicode/settings.json')
        user_settings = load_settings_file(user_path)
        user_settings[key] = value
        save_settings_file(user_path, user_settings)

    elif action == "reset":
        if key:
            if key in SETTINGS:
                # Reset to default (would need defaults dict)
                console.print(f"[yellow]Reset {key} to default[/yellow]")
        else:
            console.print("[yellow]Use /settings reset <key>[/yellow]")

    elif action == "layers":
        console.print("[dim]Layer 1: Defaults (hardcoded)[/dim]")
        console.print(f"[dim]Layer 2: Project (.amplicode/settings.json)[/dim]")
        console.print(f"[dim]Layer 3: User (~/.amplicode/settings.json)[/dim]")
        console.print(f"[dim]Layer 4: Session (loaded with session)[/dim]")
        console.print(f"[dim]Layer 5: Command-line (at startup)[/dim]")

# ==================== CUSTOM AGENTS ====================
# Agents defined in JSON or Markdown files
CUSTOM_AGENTS = {}

AGENTS_DIR = os.path.expanduser('~/.amplicode/agents')
PROJECT_AGENTS_DIR = '.amplicode/agents'

def load_agent_file(path):
    """Load an agent from JSON or Markdown file"""
    if not os.path.exists(path):
        return None

    try:
        if path.endswith('.json'):
            with open(path, 'r') as f:
                return json.load(f)
        elif path.endswith('.md'):
            # Parse Markdown frontmatter
            with open(path, 'r') as f:
                content = f.read()
            # Simple YAML frontmatter parser
            if content.startswith('---'):
                end = content.find('---', 3)
                if end != -1:
                    import yaml
                    try:
                        metadata = yaml.safe_load(content[3:end])
                        return {**metadata, 'content': content[end+3:], 'type': 'markdown'}
                    except:
                        pass
            return {'content': content, 'type': 'markdown'}
    except Exception as e:
        console.print(f"[yellow]Erro carregando agente {path}: {e}[/yellow]")
    return None

def load_all_agents():
    """Load all agents from user and project directories"""
    global CUSTOM_AGENTS

    # Load from user directory
    if os.path.exists(AGENTS_DIR):
        for f in os.listdir(AGENTS_DIR):
            if f.endswith(('.json', '.md')):
                path = os.path.join(AGENTS_DIR, f)
                agent = load_agent_file(path)
                if agent:
                    name = agent.get('name', f.replace('.json', '').replace('.md', ''))
                    CUSTOM_AGENTS[name] = agent

    # Load from project directory (overrides user)
    if os.path.exists(PROJECT_AGENTS_DIR):
        for f in os.listdir(PROJECT_AGENTS_DIR):
            if f.endswith(('.json', '.md')):
                path = os.path.join(PROJECT_AGENTS_DIR, f)
                agent = load_agent_file(path)
                if agent:
                    name = agent.get('name', f.replace('.json', '').replace('.md', ''))
                    CUSTOM_AGENTS[name] = agent

def get_agent(name):
    """Get an agent by name"""
    return CUSTOM_AGENTS.get(name)

def list_agents():
    """List all available agents"""
    if not CUSTOM_AGENTS:
        console.print("[dim]Nenhum agente customizado encontrado[/dim]")
        return
    for name, agent in CUSTOM_AGENTS.items():
        desc = agent.get('description', 'Sem descrição')
        console.print(f"[dim]{name}[/dim]: {desc}")

def cmd_agents(action=None, name=None):
    """Manage custom agents"""
    if not action:
        list_agents()
        return

    if action == "list" or action == "ls":
        list_agents()

    elif action == "load":
        load_all_agents()
        console.print(f"[green]✓ {len(CUSTOM_AGENTS)} agentes carregados[/green]")

    elif action == "show":
        if not name:
            console.print("[red]Uso: /agents show <name>[/red]")
            return
        agent = get_agent(name)
        if agent:
            console.print(f"[bold]{name}[/bold]")
            console.print(f"[dim]{agent.get('description', '')}[/dim]")
            if 'content' in agent:
                console.print(agent['content'][:500])
        else:
            console.print(f"[yellow]Agente '{name}' não encontrado[/yellow]")

    elif action == "add":
        console.print("[yellow]Para adicionar agentes, crie arquivos em ~/.amplicode/agents/[/yellow]")
        console.print("[dim]Formatos: JSON ou Markdown com frontmatter[/dim]")

def cmd_bash(arg):
    """Execute bash command with permission check"""
    if not arg:
        arg = Prompt.ask("[bold]Comando bash[/bold]")
    if not arg:
        return

    allowed, reason = check_tool_permission('bash', arg)
    if not allowed:
        console.print(f"[yellow]{reason}[/yellow]")
        return

    try:
        result = subprocess.run(
            arg, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Comando excedeu tempo limite (30s).[/red]")
    except Exception as e:
        console.print(f"[red]Erro: {e}[/red]")

def cmd_read(path=None, offset=0, limit=2000):
    """Read file with line numbers (like Claude Code's Read tool)"""
    if not path:
        path = Prompt.ask("[bold]Caminho do arquivo[/bold]")
    if not path:
        return

    allowed, reason = check_tool_permission('read_file', path)
    if not allowed:
        console.print(f"[yellow]{reason}[/yellow]")
        return

    if not os.path.exists(path):
        console.print(f"[red]Arquivo '{path}' não encontrado.[/red]")
        return

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        total_lines = len(lines)
        start = max(0, offset)
        end = min(total_lines, start + limit)

        console.print(f"[dim]{path} ({total_lines} linhas)[/dim]")
        for i in range(start, end):
            console.print(f"[dim]{i+1:>4}:[/dim] {lines[i].rstrip()}")

        if end < total_lines:
            console.print(f"[dim]... mais {total_lines - end} linhas[/dim]")
    except IOError as e:
        console.print(f"[red]Erro ao ler: {e}[/red]")

def cmd_edit(path, old_text, new_text):
    """Edit file (replaces old_text with new_text)"""
    allowed, reason = check_tool_permission('edit', (path, old_text))
    if not allowed:
        console.print(f"[yellow]{reason}[/yellow]")
        return

    if not old_text or not new_text:
        console.print("[red]Uso: /edit <path> <old_text> <new_text>[/red]")
        return

    sucesso, msg = patch_file(path, old_text, new_text)
    if sucesso:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[red]{msg}[/red]")

def cmd_glob(pattern, path=None):
    """Pattern matching for files (like Claude Code's Glob tool)"""
    allowed, reason = check_tool_permission('glob', pattern)
    if not allowed:
        console.print(f"[yellow]{reason}[/yellow]")
        return

    import glob as glob_module
    search_path = path or '.'
    matches = glob_module.glob(os.path.join(search_path, pattern), recursive=True)
    if matches:
        console.print(f"[dim]{len(matches)} arquivos encontrados:[/dim]")
        for match in matches[:50]:  # Limit to 50
            console.print(f"  {match}")
        if len(matches) > 50:
            console.print(f"[dim]... mais {len(matches) - 50} arquivos[/dim]")
    else:
        console.print("[yellow]Nenhum arquivo encontrado.[/yellow]")

def cmd_grep(pattern, path=None, case_sensitive=False):
    """Pattern matching in file contents (like Claude Code's Grep tool)"""
    allowed, reason = check_tool_permission('grep', pattern)
    if not allowed:
        console.print(f"[yellow]{reason}[/yellow]")
        return

    import re
    flags = re.IGNORECASE if i else 0
    search_path = path or '.'

    results = []
    for root, dirs, files in os.walk(search_path):
        # Skip ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line, flags):
                            results.append((file_path, i, line.rstrip()))
            except:
                continue

    if results:
        console.print(f"[dim]{len(results)} ocorrências encontradas:[/dim]")
        for file_path, line_num, line in results[:30]:  # Limit to 30
            console.print(f"[dim]{file_path}:{line_num}:[/dim] {line[:100]}")
        if len(results) > 30:
            console.print(f"[dim]... mais {len(results) - 30} resultados[/dim]")
    else:
        console.print("[yellow]Nenhum resultado encontrado.[/yellow]")

def cmd_ls(path=None):
    """List directory contents (like Claude Code's LS tool)"""
    allowed, reason = check_tool_permission('ls', path)
    if not allowed:
        console.print(f"[yellow]{reason}[/yellow]")
        return

    target = path or '.'
    if not os.path.exists(target):
        console.print(f"[red]Diretório '{target}' não encontrado.[/red]")
        return

    try:
        entries = os.listdir(target)
        dirs = []
        files = []
        for entry in entries:
            full_path = os.path.join(target, entry)
            if os.path.isdir(full_path):
                dirs.append(entry + '/')
            else:
                files.append(entry)

        console.print(f"[dim]{target}:[/dim]")
        for d in sorted(dirs):
            console.print(f"[bold blue]{d}[/bold blue]")
        for f in sorted(files):
            console.print(f"  {f}")
    except IOError as e:
        console.print(f"[red]Erro: {e}[/red]")
def cmd_btw(message=None):
    """
    Brainstorming Twist: Quick context injection.
    Adds a note/insight/reminder to the current session history.
    Without breaking the flow of running plans (TDD, Debugging, etc.).
    """
    if not message:
        message = Prompt.ask("[bold]Mensagem BTW[/bold]")
    if not message:
        return

    # Inject as a system message in conversation history
    note = f"[BTW Note from User]: {message}"
    conversation_history.append({"role": "system", "content": note})

    console.print(f"[green]✓ Nota BTW adicionada ao histórico[/green]")
    console.print(f"[dim]{message}[/dim]")



# ==================== COMMAND LINE ARGS ====================
WORK_DIR = os.getcwd()  # Default: current directory
WORK_DIR_CONTEXT = ""  # Will store initial file context
WORK_DIR_FILES = []  # List of files found

# Diretórios e arquivos a ignorar
IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                'dist', 'build', '.idea', '.vscode', '__MACOSX'}
IGNORE_EXTENSIONS = {'.pyc', '.pyo', '.so', '.o', '.class', '.jar',
                  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
                  '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.zip',
                  '.tar', '.gz', '.rar', '.7z', '.exe', '.dll'}

def scan_work_dir(max_chars=40000):
    """
    Lê arquivos de texto do WORK_DIR para contexto inicial.
    Limita a ~10k tokens (40k chars) para não estourar contexto.
    Ignora pastas pesadas e arquivos binários.
    """
    global WORK_DIR_CONTEXT, WORK_DIR_FILES

    if not os.path.isdir(WORK_DIR):
        return False

    files_content = []
    total_chars = 0

    for root, dirs, files in os.walk(WORK_DIR):
        # Remove ignored dirs (modifies dirs in-place for os.walk)
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if total_chars >= max_chars:
                break

            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORE_EXTENSIONS:
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, WORK_DIR)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Limita conteudo por arquivo (max 5000 chars)
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"

                if content.strip():  # Só adiciona se não vazio
                    files_content.append(f"=== Arquivo: {rel_path} ===\n{content}")
                    WORK_DIR_FILES.append(rel_path)
                    total_chars += len(content)

            except (IOError, UnicodeDecodeError):
                # Ignora arquivos que não conseguir ler
                continue

        if total_chars >= max_chars:
            break

    if files_content:
        WORK_DIR_CONTEXT = "\n\n".join(files_content)
        return True
    return False


def parse_args():
    """Processa argumentos de linha de comando"""
    global WORK_DIR
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == ".":
            # amplicode . → use current directory as work context
            WORK_DIR = os.getcwd()
            sys.stdout.write(f"\033[2K\r[dim]Diretório de trabalho: {WORK_DIR}[/dim]\n")
            sys.stdout.flush()
        elif os.path.isdir(arg):
            WORK_DIR = os.path.abspath(arg)
            sys.stdout.write(f"\033[2K\r[dim]Diretório de trabalho: {WORK_DIR}[/dim]\n")
            sys.stdout.flush()
        elif arg in ["-h", "--help"]:
            print("AmpliCode - IA Oficial da AmpliDEV")
            print("Uso: amplicode [diretório]")
            print("  .         → usa diretório atual como contexto")
            print("  <dir>     → usa diretório especificado")
            print("  -h, --help → mostra esta ajuda")
            sys.exit(0)
        elif arg in ["-v", "--version"]:
            print(f"AmpliCode v{AMPLI_VERSION}")
            sys.exit(0)
        else:
            print(f"Erro: '{arg}' não é um diretório válido.")
            print("Uso: amplicode [.]")
            sys.exit(1)

# Chama parse_args imediatamente após imports
parse_args()

# ==================== CONSTANTS ====================
CONFIG_PATH = os.path.expanduser("~/.amplicode_config.json")
SESSIONS_DIR = os.path.expanduser("~/.amplicode/sessions")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Cores ANSI (Core 2 Duo friendly - sem renderização GPU)
COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD_CYAN = "\033[1;96m"
COLOR_GREEN = "\033[92m"
COLOR_BOLD_GREEN = "\033[1;92m"
COLOR_BLUE = "\033[94m"
COLOR_BOLD_BLUE = "\033[1;94m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_GRAY = "\033[90m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"

# Versão
AMPLI_VERSION = "1.0.0"

# ==================== GLOBAL STATE ====================
console = Console()
conversation_history = []
context_files = {}
session_start = time.time()
total_tokens = 0
session_cost = 0.0

# ==================== CONFIG MANAGER ====================
def load_config():
    """Carrega configurações do ~/.amplicode_config.json"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            console.print(f"[yellow]Aviso: Erro ao ler config: {e}[/yellow]")
            return get_default_config()
    return get_default_config()

def get_default_config():
    """Retorna configuração padrão"""
    return {
        "models": [],
        "current_model": None,
        "settings": {
            "max_tokens": 2048,
            "temperature": 0.7,
            "auto_compact": True
        }
    }

def save_config(config):
    """Salva configurações no ~/.amplicode_config.json"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        console.print(f"[red]Erro ao salvar config: {e}[/red]")

def ensure_config():
    """Verifica se config existe, senão inicia setup"""
    if not os.path.exists(CONFIG_PATH):
        console.print("\n[bold yellow]Primeira execução detectada. Iniciando configuração...[/bold yellow]\n")
        cmd_setup()

def ensure_sessions_dir():
    """Garante que o diretório de sessões existe"""
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def dependency_check():
    """Verifica se todas as dependências estão instaladas"""
    REQUIRED_PACKAGES = ["rich", "openai"]
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Erro: Dependências faltando: {', '.join(missing)}")
        print("Instale com: pip install rich openai")
        sys.exit(1)

def validate_model(api_key, model_id):
    """Valida API key e model_id com uma requisição mínima"""
    try:
        client = openai.OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        return True, None
    except openai.AuthenticationError:
        return False, "Chave de API inválida. Verifique sua NVIDIA API Key."
    except openai.NotFoundError as e:
        return False, f"Modelo não encontrado. Verifique o ID (ex: nvidia/llama-3.1-8b-instruct). Erro: {str(e)}"
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"

def get_current_model_config():
    """Obtém configuração do modelo atual"""
    config = load_config()
    if not config["current_model"]:
        return None
    return next((m for m in config["models"] if m["name"] == config["current_model"]), None)

def cmd_setup():
    """Wizard de configuração inicial e adição de modelos"""
    console.print()
    console.print("=" * console.width, style="bold cyan")
    console.print("  AmpliCode - Configuração Inicial", style="bold cyan")
    console.print("=" * console.width, style="bold cyan")
    console.print()

    config = load_config()

    # Se já tem modelos, pergunta se quer adicionar outro
    if config["models"]:
        console.print(f"[dim]{len(config['models'])} modelo(s) já configurado(s).[/dim]")
        if not Confirm.ask("Deseja adicionar um novo modelo?", default=True):
            return

    # Coleta informações do modelo
    console.print("[bold]Adicionar Novo Modelo NVIDIA[/bold]")
    console.print()

    name = Prompt.ask("[bold]Nome Amigável[/bold] (ex: Llama 3.1 8B)")
    if not name:
        console.print("[red]Nome obrigatório![/red]")
        return

    api_key = Prompt.ask("[bold]NVIDIA API Key[/bold] (começa com nvapi-)")
    if not api_key:
        console.print("[red]API Key obrigatória![/red]")
        return

    # Valida formato da chave
    if not api_key.startswith("nvapi-"):
        console.print("[yellow]Aviso: API Key geralmente começa com 'nvapi-'. Continue mesmo assim?[/yellow]")
        if not Confirm.ask("Prosseguir?", default=False):
            return

    console.print()
    console.print("[dim]Modelos NVIDIA disponíveis:[/dim]")
    console.print("[dim]  • nvidia/llama-3.1-8b-instruct[/dim]")
    console.print("[dim]  • nvidia/llama-3.1-70b-instruct[/dim]")
    console.print("[dim]  • nvidia/llama-3.2-1b-instruct[/dim]")
    console.print("[dim]  • mistralai/mistral-7b-instruct-v0.3[/dim]")
    console.print()

    model_id = Prompt.ask("[bold]ID do Modelo NVIDIA[/bold]", default="nvidia/llama-3.1-8b-instruct")

    # Valida formato do model_id
    if "/" not in model_id:
        console.print("[red]Formato inválido! Use: organizacao/modelo[/red]")
        return

    # Testa a configuração
    console.print()
    console.print("[yellow]Validando configuração...[/yellow]")
    valid, error = validate_model(api_key, model_id)

    if not valid:
        console.print(f"[red]Erro na validação: {error}[/red]")
        return

    console.print("[green]✓ Configuração válida![/green]")

    # Salva o modelo
    config["models"].append({
        "name": name,
        "api_key": api_key,
        "model_id": model_id
    })

    # Define como modelo atual se for o primeiro
    if not config["current_model"]:
        config["current_model"] = name

    save_config(config)
    console.print()
    console.print(f"[green]✓ Modelo '{name}' adicionado com sucesso![/green]")
    console.print(f"[dim]Model ID: {model_id}[/dim]")

    # Pergunta se deve trocar para este modelo
    if config["current_model"] != name:
        if Confirm.ask(f"Trocar para o modelo '{name}' agora?", default=True):
            config["current_model"] = name
            save_config(config)
            console.print(f"[green]✓ Modelo atual alterado para '{name}'[/green]")

# Bloco 1 concluído: Imports + Config Manager

# ==================== ANSI TERMINAL UI HELPERS ====================

def get_terminal_width():
    """Retorna largura do terminal (fallback 80)"""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def ansi_move_to(line):
    """Move cursor para linha absoluta (1-indexed)"""
    sys.stdout.write(f"\033[{line};1H")
    sys.stdout.flush()

def ansi_clear_screen():
    """Limpa tela e reposiciona cursor"""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def ansi_clear_line():
    """Limpa linha atual"""
    sys.stdout.write("\033[2K")
    sys.stdout.flush()

def ansi_save_cursor():
    """Salva posição do cursor"""
    sys.stdout.write("\033[s")
    sys.stdout.flush()

def ansi_restore_cursor():
    """Restaura posição do cursor"""
    sys.stdout.write("\033[u")
    sys.stdout.flush()

def ansi_hide_cursor():
    """Esconde cursor"""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def ansi_show_cursor():
    """Mostra cursor"""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def render_header(model_name, tokens_used, max_ctx=200000):
    """
    Renderiza cabeçalho fixo estilo Claude Code usando ANSI puro.
    Formato: █ AmpliCode │ model │ ● XX% ctx │ ⏱ XXs │ $X.XXXX
    Otimizado para Core 2 Duo: mínimo de operações, ANSI direto.
    """
    elapsed = int(time.time() - session_start)
    mins, secs = divmod(elapsed, 60)
    time_str = f"{mins}m{secs:02d}s" if mins > 0 else f"{secs}s"

    ctx_pct = min(100, int((tokens_used / max_ctx) *100)) if max_ctx > 0 else 0
    # Cores ANSI diretas (evita concatenar strings intermediárias)
    if ctx_pct < 50:
        ctx_color = "\033[92m"  # GREEN
    elif ctx_pct < 80:
        ctx_color = "\033[93m"  # YELLOW
    else:
        ctx_color = "\033[91m"  # RED

    width = get_terminal_width()

    # Linha 1: Cabeçalho (uma única escrita para reduzir syscalls)
    header = (
        "\033[H"  # Cursor home
        "\033[1;96m█ AmpliCode\033[0m"  # Bold cyan
        "\033[90m │ \033[0m"
        f"\033[97m{model_name or 'não selecionado'}\033[0m"
        "\033[90m │ \033[0m"
        f"{ctx_color}● {ctx_pct}% ctx\033[0m"
        "\033[90m │ \033[0m"
        f"\033[97m⏱ {time_str}\033[0m"
        "\033[90m │ \033[0m"
        f"\033[97m${session_cost:.4f}\033[0m"
        " " * (width - 80) + "\n"  # Padding (aproximado)
        "\033[90m" + "─" * width + "\033[0m\n"
    )

    sys.stdout.write(header)
    sys.stdout.flush()

def render_user_message(content):
    """
    Renderiza mensagem do usuário com borda azul (ANSI).
    Otimizado para Core 2 Duo: escrita única sempre que possível.
    """
    width = get_terminal_width()
    max_w = width - 6  # Margens da borda

    # Pré-processa conteúdo para evitar múltiplas escritas
    lines = []
    for line in content.split('\n'):
        while len(line) > max_w:
            lines.append(line[:max_w])
            line = line[max_w:]
        lines.append(line)

    # Escreve tudo de uma vez (minimiza syscalls)
    output = "\033[1;94m  You\033[0m\n"  # Bold blue
    output += f"\033[94m  ╭{'─' * (width - 4)}╮\033[0m\n"

    for line in lines:
        padding = " " * (width - 6 - len(line))
        output += f"\033[94m  │ \033[0m{line}{padding}\033[94m │\033[0m\n"

    output += f"\033[94m  ╰{'─' * (width - 4)}╯\033[0m\n\n"
    sys.stdout.write(output)
    sys.stdout.flush()

def stream_token(token):
    """
    Escreve token diretamente no stdout (Core 2 Duo optimized).
    Sem buffer, sem Rich Live, flush imediato.
    """
    sys.stdout.write(token)
    sys.stdout.flush()

def render_assistant_message_done():
    """Finaliza mensagem da IA (nova linha)"""
    sys.stdout.write("\n\n")
    sys.stdout.flush()

def render_error(message):
    """Renderiza erro com borda vermelha"""
    width = get_terminal_width()
    sys.stdout.write(COLOR_RED + "  ╭" + "─" * (width - 4) + "╮" + COLOR_RESET + "\n")
    sys.stdout.write(COLOR_RED + "  │ " + COLOR_RESET + "ERRO: " + message + COLOR_RED + " │" + COLOR_RESET + "\n")
    sys.stdout.write(COLOR_RED + "  ╰" + "─" * (width - 4) + "╯" + COLOR_RESET + "\n")
    sys.stdout.write("\n")
    sys.stdout.flush()

def render_separator():
    """Linha separadora discreta"""
    width = get_terminal_width()
    sys.stdout.write(COLOR_GRAY + "  " + "─" * (width - 2) + COLOR_RESET + "\n")
    sys.stdout.flush()

def ansi_spinner(start=False, message="Processando..."):
    """
    Spinner ANSI simples (sem animação, apenas texto estático).
    Para Core 2 Duo, evitamos overhead de thread/animção.
    """
    if start:
        sys.stdout.write(COLOR_CYAN + "  ⠋ " + COLOR_DIM + message + COLOR_RESET)
        sys.stdout.flush()
    else:
        # Clear and stop
        sys.stdout.write("\r")
        sys.stdout.flush()

def clear_and_show_header():
    """Limpa tela e mostra cabeçalho (para /clear)"""
    ansi_clear_screen()
    config = load_config()
    render_header(config.get("current_model", "não selecionado"), total_tokens)

def show_welcome_banner():
    """Mostra banner de boas-vindas (usando Rich para formatação estática)"""
    config = load_config()
    model_name = config.get("current_model", "nenhum selecionado")

    console.print()
    console.print(f"[bold cyan]AmpliCode v{AMPLI_VERSION} — IA Oficial da AmpliDEV[/bold cyan]")
    console.print(f"[dim]Modelo: {model_name}[/dim]")
    console.print("[dim]Digite /help para comandos ou sua pergunta abaixo.[/dim]")
    render_separator()

# Bloco 2 concluído: ANSI Terminal UI Helpers

# ==================== NVIDIA API CLIENT ====================

def create_nvidia_client(api_key):
    """Cria cliente OpenAI configurado para NVIDIA API"""
    return openai.OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=api_key
    )

def estimate_tokens(text):
    """Estimativa rápida de tokens (~4 chars por token)"""
    return len(text) // 4

def stream_response(client, model_id, messages, max_tokens=2048, temperature=0.7):
    """
    Streaming via NVIDIA API (Core 2 Duo optimized).
    Escreve tokens diretamente no stdout, sem buffer.
    Retorna (full_response, error).
    """
    full_response = []
    try:
        stream = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                stream_token(token)
                full_response.append(token)

        render_assistant_message_done()
        return "".join(full_response), None

    except openai.AuthenticationError:
        return None, "Erro de autenticação. Verifique sua NVIDIA API Key."
    except openai.NotFoundError as e:
        return None, f"Modelo não encontrado. Verifique o ID. Erro: {str(e)}"
    except openai.RateLimitError:
        return None, "Limite de taxa atingido. Tente novamente em alguns segundos."
    except openai.APITimeoutError:
        return None, "Tempo esgotado. Verifique sua conexão."
    except Exception as e:
        return None, f"Erro na API NVIDIA: {str(e)}"

def send_to_nvidia(user_message, use_stream=True):
    """
    Envia mensagem para NVIDIA API e retorna resposta.
    Gerencia histórico, contexto de arquivos e contagem de tokens.
    """
    global total_tokens, session_cost

    model_config = get_current_model_config()
    if not model_config:
        return None, "Nenhum modelo selecionado. Use /models."

    # Prepara mensagens
    messages = []

    # Adiciona contexto de arquivos se houver
    if context_files:
        file_context = "\n\n".join([
            f"=== Arquivo: {path} ===\n{content}"
            for path, content in context_files.items()
        ])
        messages.append({
            "role": "system",
            "content": f"Arquivos de contexto:\n{file_context}"
        })

    # Adiciona histórico
    messages.extend(conversation_history)

    # Adiciona mensagem atual
    messages.append({"role": "user", "content": user_message})

    try:
        client = create_nvidia_client(model_config["api_key"])
        model_id = model_config.get("model_id", "nvidia/llama-3.1-8b-instruct")
        config = load_config()
        settings = config.get("settings", {})
        max_tokens = settings.get("max_tokens", 2048)
        temperature = settings.get("temperature", 0.7)

        if use_stream:
            return stream_response(client, model_id, messages, max_tokens, temperature)
        else:
            # Non-stream (fallback)
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            ai_response = response.choices[0].message.content

            # Estimativa de tokens
            input_tokens = estimate_tokens(user_message) + sum(
                estimate_tokens(m.get("content", "")) for m in messages[:-1]
            )
            output_tokens = estimate_tokens(ai_response)
            total_tokens += input_tokens + output_tokens

            # Estimativa de custo (valores NVIDIA)
            session_cost += (input_tokens * 0.00001) + (output_tokens * 0.00003)

            return ai_response, None

    except Exception as e:
        return None, f"Erro inesperado: {str(e)}"

def auto_compact_if_needed():
    """Compacta contexto automaticamente se passar de 80%"""
    global conversation_history
    config = load_config()
    if not config.get("settings", {}).get("auto_compact", True):
        return

    if total_tokens > 160000:  # 80% de 200k
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]
            console.print("[yellow]Contexto compactado automaticamente (80% limite).[/yellow]")

# Bloco 3 concluído: NVIDIA API Client

# ==================== SESSION PERSISTENCE ====================

def save_session(name=None):
    """Salva sessão atual em ~/.amplicode/sessions/"""
    ensure_sessions_dir()

    if not name:
        name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    session_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{name}"
    config = load_config()
    model_name = config.get("current_model", "unknown")

    session_data = {
        "id": session_id,
        "name": name,
        "created": datetime.now().isoformat(),
        "model": model_name,
        "conversation_history": conversation_history,
        "context_files": context_files,
        "total_tokens": total_tokens,
        "session_cost": session_cost
    }

    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✓ Sessão '{name}' salva em ~/.amplicode/sessions/[/green]")
        console.print(f"[dim]{len(conversation_history)} mensagens, {len(context_files)} arquivos[/dim]")
    except IOError as e:
        console.print(f"[red]Erro ao salvar sessão: {e}[/red]")

def list_sessions():
    """Lista todas as sessões salvas"""
    ensure_sessions_dir()

    sessions = []
    try:
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SESSIONS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        sessions.append(data)
                except (json.JSONDecodeError, IOError):
                    continue

        if not sessions:
            console.print("[yellow]Nenhuma sessão salva.[/yellow]")
            return

        # Ordena por data (mais recente primeiro)
        sessions.sort(key=lambda x: x.get("created", ""), reverse=True)

        console.print()
        console.print(COLOR_BOLD_CYAN + "  Sessões Salvas" + COLOR_RESET)
        console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)

        for i, sess in enumerate(sessions, 1):
            name = sess.get("name", "sem-nome")
            created = sess.get("created", "")
            model = sess.get("model", "unknown")
            tokens = sess.get("total_tokens", 0)
            msgs = len(sess.get("conversation_history", []))

            try:
                dt = datetime.fromisoformat(created)
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except:
                date_str = created[:16]

            console.print(f"  {i}. [bold]{name}[/bold] - {date_str}")
            console.print(f"     Modelo: {model} | Mensagens: {msgs} | Tokens: ~{tokens}")

        console.print()

    except IOError as e:
        console.print(f"[red]Erro ao ler sessões: {e}[/red]")

def resume_session(identifier):
    """
    Retoma uma sessão salva por nome ou ID.
    identifier: nome da sessão ou ID (timestamp-nome)
    """
    global conversation_history, context_files, total_tokens, session_cost

    ensure_sessions_dir()

    found_file = None
    try:
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SESSIONS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if (data.get("id") == identifier or
                            data.get("name") == identifier or
                            filename == f"{identifier}.json"):
                            found_file = file_path
                            break
                except (json.JSONDecodeError, IOError):
                    continue
    except IOError as e:
        console.print(f"[red]Erro ao buscar sessões: {e}[/red]")
        return

    if not found_file:
        console.print(f"[red]Sessão '{identifier}' não encontrada.[/red]")
        console.print("[dim]Use /sessions para listar sessões disponíveis.[/dim]")
        return

    try:
        with open(found_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conversation_history = data.get("conversation_history", [])
        context_files = data.get("context_files", {})
        total_tokens = data.get("total_tokens", 0)
        session_cost = data.get("session_cost", 0.0)

        console.print(f"[green]✓ Sessão '{data.get('name')}' retomada![/green]")
        console.print(f"[dim]{len(conversation_history)} mensagens, {len(context_files)} arquivos[/dim]")

    except (json.JSONDecodeError, IOError) as e:
        console.print(f"[red]Erro ao carregar sessão: {e}[/red]")

def delete_session(identifier):
    """Remove uma sessão salva"""
    ensure_sessions_dir()

    found_file = None
    try:
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(SESSIONS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if (data.get("id") == identifier or
                            data.get("name") == identifier):
                            found_file = file_path
                            break
                except (json.JSONDecodeError, IOError):
                    continue
    except IOError as e:
        console.print(f"[red]Erro ao buscar sessões: {e}[/red]")
        return

    if not found_file:
        console.print(f"[red]Sessão '{identifier}' não encontrada.[/red]")
        return

    try:
        os.remove(found_file)
        console.print(f"[green]✓ Sessão removida.[/green]")
    except IOError as e:
        console.print(f"[red]Erro ao remover sessão: {e}[/red]")

def show_history():
    """Mostra histórico da sessão atual"""
    if not conversation_history:
        console.print("[yellow]Histórico vazio.[/yellow]")
        return

    console.print()
    console.print(COLOR_BOLD_CYAN + "  Histórico da Sessão" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)

    for i, msg in enumerate(conversation_history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            console.print(f"  {i}. [bold blue]You:[/bold blue] {content[:80]}{'...' if len(content) > 80 else ''}")
        elif role == "assistant":
            console.print(f"  {i}. [bold green]AmpliCode:[/bold green] {content[:80]}{'...' if len(content) > 80 else ''}")

    console.print()

# Bloco 4 concluído: Session Persistence

# ==================== SUPERPOWERS SKILLS (FROZEN SNAPSHOT) ====================

SUPERPOWERS_SKILLS = {
    "brainstorming": {
        "prompt": """# Skill: brainstorming

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Explore project context** — check files, docs, recent commits
2. **Offer visual companion** (if topic will involve visual questions) — this is its own message, not combined with a clarifying question. See the Visual Companion section below.
3. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** — with trade-offs and your recommendation
5. **Present design** — in sections scaled to their complexity, get user approval after each section
6. **Write design doc** — save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit
7. **Spec self-review** — quick inline check for placeholders, contradictions, ambiguity, scope (see below)
8. **User reviews written spec** — ask user to review the spec file before proceeding
9. **Transition to implementation** — invoke writing-plans skill to create implementation plan

## Process Flow

The terminal state is invoking writing-plans. Do NOT invoke frontend-design, mcp-builder, or any other implementation skill. The ONLY skill you invoke after brainstorming is writing-plans.

## The Process

**Understanding the idea:**

- Check out the current project state first (files, docs, recent commits)
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems, flag this immediately. Don't spend questions refining details of a project that needs to be decomposed first.
- For appropriately-scoped projects, ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**

- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

**Design for isolation and clarity:**

- Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently
- For each unit, you should be able to answer: what does it do, how do you use it, and what does it depend on?
- Can someone understand what a unit does without reading its internals? Can you change the internals without breaking consumers? If not, the boundaries need work.
- Smaller, well-bounded units are also easier for you to work with - you reason better about code you can hold in context at once, and your edits are more reliable when files are focused. When a file grows large, that's often a signal that it's doing too much.

**Working in existing codebases:**

- Explore the current structure before proposing changes. Follow existing patterns.
- Where existing code has problems that affect the work (e.g., a file that's grown too large, unclear boundaries, tangled responsibilities), include targeted improvements as part of the design - the way a good developer improves code they're working in.
- Don't propose unrelated refactoring. Stay focused on what serves the current goal.

## After the Design

**Documentation:**

- Write the validated design (spec) to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
  - (User preferences for spec location override this default)
- Use elements-of-style:writing-clearly-and-concisely skill if available
- Commit the design document to git

**Spec Self-Review:**
After writing the spec document, look at it with fresh eyes:

1. **Placeholder scan:** Any "TBD", "TODO", incomplete sections, or vague requirements? Fix them.
2. **Internal consistency:** Do any sections contradict each other? Does the architecture match the feature descriptions?
3. **Scope check:** Is this focused enough for a single implementation plan, or does it need decomposition?
4. **Ambiguity check:** Could any requirement be interpreted two different ways? If so, pick one and make it explicit.

Fix any issues inline. No need to re-review — just fix and move on.

**User Review Gate:**
After the spec review loop passes, ask the user to review the written spec before proceeding:

> "Spec written and committed to `<path>`. Please review it and let me know if you want to make any changes before we start writing out the implementation plan."

Wait for the user's response. If they request changes, make them and re-run the spec review loop. Only proceed once the user approves.

**Implementation:**

- Invoke the writing-plans skill to create a detailed implementation plan
- Do NOT invoke any other skill. writing-plans is the next step.

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design, get approval before moving on
- **Be flexible** - Go back and clarify when something doesn't make sense
""",
        "files": []
    },
    "test-driven-development": {
        "prompt": "",  # Space for full TDD skill content
        "files": []
    },
    "systematic-debugging": {
        "prompt": "",  # Space for debugging skill content
        "files": []
    },
    "writing-plans": {
        "prompt": "",  # Space for writing-plans skill content
        "files": []
    },
    "executing-plans": {
        "prompt": "",  # Space for executing-plans skill content
        "files": []
    },
    "using-superpowers": {
        "prompt": """## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.
""",
        "files": []
    },
    # ... remaining 9 skills would be embedded here
}

def get_skill(name):
    """Retrieve a skill by name"""
    return SUPERPOWERS_SKILLS.get(name.lower())

def list_skills():
    """List all available superpowers skills"""
    console.print()
    console.print(COLOR_BOLD_CYAN + "  Superpowers Skills Disponíveis" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)

    for i, (name, data) in enumerate(SUPERPOWERS_SKILLS.items(), 1):
        console.print(f"  {i}. [bold cyan]/{name}[/bold cyan] - Skill de {name.replace('-', ' ').title()}")

    console.print()
    console.print("[dim]Use /<skill-name> para invocar um skill[/dim]")
    console.print()

# Bloco 5 concluído: Superpowers Skills

# ==================== GIT OPERATIONS ====================

def is_git_repo():
    """Verifica se está em um repositório Git"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def git_status():
    """Retorna status do git (porcelain format)"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

def git_diff(file=None, staged=False):
    """Retorna diff do git"""
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if file:
            cmd.append(file)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

def git_add(files=None):
    """Adiciona arquivos ao staging"""
    try:
        if files:
            cmd = ["git", "add"] + (files if isinstance(files, list) else [files])
        else:
            cmd = ["git", "add", "."]
        subprocess.run(cmd, capture_output=True, timeout=10)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def git_commit(message):
    """Faz commit com a mensagem fornecida"""
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, "Erro ao executar git commit"

def git_checkout_branch(name):
    """Cria e muda para nova branch"""
    try:
        result = subprocess.run(
            ["git", "checkout", "-b", name],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0, result.stdout + result.stderr
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, "Erro ao criar branch"

def git_current_branch():
    """Retorna branch atual"""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

def generate_commit_message(diff_text):
    """
    Gera mensagem de commit usando a IA atual.
    Envia o diff para a NVIDIA API e pede uma mensagem convencional.
    """
    model_config = get_current_model_config()
    if not model_config:
        return "Update files"  # Fallback

    client = create_nvidia_client(model_config["api_key"])
    model_id = model_config.get("model_id", "nvidia/llama-3.1-8b-instruct")

    prompt = f"""You are a Git commit message generator. Based on the diff below, generate a concise, conventional commit message (max 72 chars).

Format: <type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore

Diff:
{diff_text[:2000]}  # Limit to avoid token overflow

Commit message:"""

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
            stream=False
        )
        message = response.choices[0].message.content.strip()
        # Remove quotes if present
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        return message or "Update files"
    except:
        return "Update files"

def cmd_commit():
    """Auto-gera mensagem de commit e faz commit"""
    if not is_git_repo():
        console.print("[red]Erro: Não está em um repositório Git.[/red]")
        return

    console.print()
    console.print(COLOR_BOLD_YELLOW + "  Git Commit" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)

    # Verifica se há mudanças
    status = git_status()
    if not status:
        console.print("[yellow]Nenhuma mudança detectada.[/yellow]")
        return

    console.print("[dim]Mudanças detectadas:[/dim]")
    for line in status.split('\n')[:10]:  # Mostra primeiras 10 linhas
        if line.strip():
            console.print(f"  {line}")

    # Adiciona ao staging
    console.print("\n[dim]Adicionando arquivos ao staging...[/dim]")
    if not git_add():
        console.print("[red]Erro ao adicionar arquivos.[/red]")
        return

    # Gerar mensagem
    console.print("[dim]Gerando mensagem de commit com IA...[/dim]")
    diff = git_diff(staged=True)
    message = generate_commit_message(diff)

    console.print(f"\n[bold]Mensagem sugerida:[/bold] {message}")
    console.print()

    if Confirm.ask("Usar esta mensagem?", default=True):
        success, output = git_commit(message)
        if success:
            console.print("[green]✓ Commit realizado com sucesso![/green]")
        else:
            console.print(f"[red]Erro no commit: {output}[/red]")
    else:
        custom_msg = Prompt.ask("[bold]Digite sua mensagem[/bold]")
        if custom_msg:
            success, output = git_commit(custom_msg)
            if success:
                console.print("[green]✓ Commit realizado com sucesso![/green]")
            else:
                console.print(f"[red]Erro no commit: {output}[/red]")

def cmd_diff(file=None):
    """Mostra diff com análise da IA"""
    if not is_git_repo():
        console.print("[red]Erro: Não está em um repositório Git.[/red]")
        return

    diff = git_diff(file)
    if not diff:
        console.print("[yellow]Nenhuma diff disponível.[/yellow]")
        return

    # Mostra diff no terminal (formatação básica)
    console.print()
    console.print(COLOR_BOLD_YELLOW + "  Git Diff" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)

    # Coloriza diff básico (ANSI)
    for line in diff.split('\n')[:100]:  # Limita a 100 linhas
        if line.startswith('+'):
            sys.stdout.write(COLOR_GREEN + line + COLOR_RESET + "\n")
        elif line.startswith('-'):
            sys.stdout.write(COLOR_RED + line + COLOR_RESET + "\n")
        elif line.startswith('@@'):
            sys.stdout.write(COLOR_CYAN + line + COLOR_RESET + "\n")
        else:
            sys.stdout.write(line + "\n")
    sys.stdout.flush()

    # Análise com IA (opcional)
    if len(diff) > 10 and Confirm.ask("\nAnalisar diff com AmpliCode?", default=True):
        console.print("[dim]Analisando...[/dim]")
        model_config = get_current_model_config()
        if model_config:
            client = create_nvidia_client(model_config["api_key"])
            model_id = model_config.get("model_id", "nvidia/llama-3.1-8b-instruct")

            prompt = f"""Analyze this git diff and provide a concise summary of changes.

Diff:
{diff[:3000]}

Summary:"""

            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.5,
                    stream=False
                )
                analysis = response.choices[0].message.content
                console.print("\n[bold green]Análise da IA:[/bold green]")
                console.print(analysis)
            except:
                console.print("[yellow]Não foi possível analisar com IA.[/yellow]")

def cmd_branch(name=None):
    """Cria e muda para nova branch"""
    if not is_git_repo():
        console.print("[red]Erro: Não está em um repositório Git.[/red]")
        return

    if not name:
        name = Prompt.ask("[bold]Nome da nova branch[/bold]")
    if not name:
        console.print("[red]Nome obrigatório![/red]")
        return

    success, output = git_checkout_branch(name)
    if success:
        console.print(f"[green]✓ Branch '{name}' criada e ativada![/green]")
    else:
        console.print(f"[red]Erro: {output}[/red]")

def cmd_pr(title=None):
    """Cria Pull Request com descrição gerada por IA"""
    if not is_git_repo():
        console.print("[red]Erro: Não está em um repositório Git.[/red]")
        return

    # Verifica se gh CLI está disponível
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print("[red]Erro: GitHub CLI (gh) não está instalado.[/red]")
        console.print("[dim]Instale em: https://cli.github.com[/dim]")
        return

    console.print()
    console.print(COLOR_BOLD_YELLOW + "  Git Pull Request" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)

    # Gera título e descrição
    if not title:
        diff = git_diff()
        if diff:
            console.print("[dim]Gerando título e descrição com IA...[/dim]")
            model_config = get_current_model_config()
            if model_config:
                client = create_nvidia_client(model_config["api_key"])
                model_id = model_config.get("model_id", "nvidia/llama-3.1-8b-instruct")

                prompt = f"""Based on this git diff, generate a PR title (max 60 chars) and description.

Diff:
{diff[:3000]}

Format:
Title: <title>
Description:
<description>"""

                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500,
                        temperature=0.5,
                        stream=False
                    )
                    ai_output = response.choices[0].message.content

                    # Parse output
                    lines = ai_output.split('\n')
                    title_line = next((l for l in lines if l.startswith('Title:')), None)
                    if title_line:
                        title = title_line.replace('Title:', '').strip()
                    else:
                        title = "Update files"

                    desc_start = ai_output.find('Description:')
                    if desc_start != -1:
                        description = ai_output[desc_start + 13:].strip()
                    else:
                        description = ai_output
                except:
                    title = "Update files"
                    description = "Automated PR via AmpliCode"
            else:
                title = "Update files"
                description = "Automated PR via AmpliCode"
        else:
            title = "Update files"
            description = "Automated PR via AmpliCode"

    console.print(f"[bold]Título:[/bold] {title}")
    console.print(f"[dim]Descrição:[/dim]\n{description[:200]}...")

    if Confirm.ask("\nCriar PR com estas informações?", default=True):
        try:
            result = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", description],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                console.print("[green]✓ Pull Request criado com sucesso![/green]")
                console.print(f"[dim]{result.stdout.strip()}[/dim]")
            else:
                console.print(f"[red]Erro ao criar PR: {result.stderr}[/red]")
        except Exception as e:
            console.print(f"[red]Erro: {e}[/red]")
    else:
        custom_title = Prompt.ask("[bold]Título personalizado[/bold]", default=title)
        custom_desc = Prompt.ask("[bold]Descrição[/bold]", default=description)
        if Confirm.ask("Criar PR agora?", default=True):
            try:
                result = subprocess.run(
                    ["gh", "pr", "create", "--title", custom_title, "--body", custom_desc],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    console.print("[green]✓ Pull Request criado![/green]")
                else:
                    console.print(f"[red]Erro: {result.stderr}[/red]")
            except Exception as e:
                console.print(f"[red]Erro: {e}[/red]")

# Bloco 6 concluído: Git Operations

# ==================== COMMAND HANDLER (39 COMMANDS) ====================

def cmd_help():
    """Exibe ajuda dos comandos"""
    console.print()
    console.print(COLOR_BOLD_CYAN + "  Comandos AmpliCode" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="white")
    table.add_column(style="dim")
    table.add_column(style="cyan")
    table.add_column(style="white")

    commands = [
        ("/btw <msg>", "Brainstorming Twist (non-blocking)", "/setup", "Configurar/Adicionar modelo"),
        ("/addmodel", "Adicionar novo modelo NVIDIA", "/models", "Listar/Selecionar modelos"),
        ("/sessions", "Gerenciar sessões salvas", "/save [nome]", "Salvar sessão atual"),
        ("/resume <id>", "Retomar sessão salva", "/history", "Ver histórico da sessão"),
        ("/readfile <path>", "Adicionar arquivo ao contexto", "/clear", "Limpar histórico e contexto"),
        ("/tokens", "Mostrar uso de tokens", "/cost", "Mostrar custo da sessão"),
        ("/compact", "Compactar janela de contexto", "/status", "Mostrar status atual"),
        ("/commit", "Auto-commit Git com IA", "/diff [file]", "Mostrar git diff + IA"),
        ("/branch <name>", "Criar nova branch Git", "/pr [title]", "Criar Pull Request"),
        ("/review", "Revisar alterações (IA)", "/undo", "Desfazer última edição"),
        ("/redo", "Refazer edição", "/bash <cmd>", "Executar comando bash"),
        ("/search <query>", "Busca web", "/fetch <url>", "Buscar conteúdo de URL"),
        ("/todo", "Gerenciar lista de tarefas", "/agents", "Listar/Managar agentes"),
        ("/skills", "Listar skills Superpowers", "/hook <action>", "Gerenciar eventos hook"),
        ("/permissions <mode>", "Modo de permissão", "/sandbox", "Ativar/Desativar sandbox"),
        ("/mcp <action>", "Gerenciar servidores MCP", "/settings <action>", "Gerenciar configurações"),
        ("/telemetry", "Ativar/Desativar telemetria", "/theme", "Mudar tema de cores"),
        ("/export", "Exportar conversa", "/import", "Importar conversa"),
        ("/reset", "Resetar configurações", "/version", f"Versão atual: {AMPLI_VERSION}"),
        ("/update", "Verificar atualizações", "/help", "Mostrar esta ajuda"),
        ("/quit ou /exit", "Sair do AmpliCode", "", "")
    ]

    for i in range(0, len(commands), 2):
        c1, d1, c2, d2 = commands[i]
        c2 = commands[i+1][0] if i+1 < len(commands) else ""
        d2 = commands[i+1][1] if i+1 < len(commands) else ""
        table.add_row(c1, d1, c2, d2)

    console.print(table)
    console.print()
    console.print("[dim]Dica: Pressione Enter com linha vazia para cancelar inputs.[/dim]")

def cmd_readfile(file_path):
    """Lê arquivo e adiciona ao contexto"""
    if not file_path:
        console.print("[red]Uso: /readfile <caminho>[/red]")
        return

    if not os.path.exists(file_path):
        render_error(f"Arquivo '{file_path}' não encontrado.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        context_files[file_path] = content
        console.print(f"[green]✓ Arquivo '{file_path}' adicionado ao contexto.[/green]")
        console.print(f"[dim]{len(content)} caracteres lidos.[/dim]")
    except Exception as e:
        render_error(f"Erro ao ler arquivo: {str(e)}")

def cmd_clear():
    """Limpa histórico"""
    global conversation_history, context_files
    conversation_history = []
    context_files = {}
    console.print("[yellow]Histórico e contexto limpos.[/yellow]")

def cmd_tokens():
    """Mostra uso de tokens"""
    console.print(f"[cyan]Tokens estimados:[/cyan] ~{total_tokens}")
    console.print(f"[dim]Nota: Estimativa baseada em ~4 chars/token[/dim]")

def cmd_cost():
    """Mostra custo estimado"""
    console.print(f"[cyan]Custo estimado da sessão:[/cyan] ${session_cost:.4f}")

def cmd_compact():
    """Compacta contexto (simulação)"""
    global conversation_history
    if len(conversation_history) > 10:
        conversation_history = conversation_history[-10:]
        console.print("[yellow]Contexto compactado. Mantidas as 10 últimas mensagens.[/yellow]")
    else:
        console.print("[dim]Contexto já está compacto.[/dim]")

def cmd_status():
    """Mostra status atual"""
    config = load_config()
    console.print()
    console.print(COLOR_BOLD_CYAN + "  Status do AmpliCode" + COLOR_RESET)
    console.print(COLOR_GRAY + "  " + "─" * (get_terminal_width() - 4) + COLOR_RESET)
    console.print(f"  [bold]Versão:[/bold] {AMPLI_VERSION}")
    console.print(f"  [bold]Modelo atual:[/bold] {config.get('current_model', 'nenhum')}")
    console.print(f"  [bold]Tokens:[/bold] ~{total_tokens}")
    console.print(f"  [bold]Custo:[/bold] ${session_cost:.4f}")
    console.print(f"  [bold]Arquivos no contexto:[/bold] {len(context_files)}")
    console.print(f"  [bold]Mensagens:[/bold] {len(conversation_history)}")
    console.print(f"  [bold]Git:[/bold] {'Sim (' + git_current_branch() + ')' if is_git_repo() else 'Não'}")
    console.print()

def cmd_version():
    """Mostra versão"""
    console.print(f"[bold cyan]AmpliCode v{AMPLI_VERSION}[/bold cyan]")
    console.print("[dim]IA Oficial da AmpliDEV (Divisão AmpliGroup)[/dim]")

def cmd_undo():
    """Placeholder para undo"""
    console.print("[yellow]Undo: funcionalidade em desenvolvimento.[/yellow]")

def cmd_redo():
    """Placeholder para redo"""
    console.print("[yellow]Redo: funcionalidade em desenvolvimento.[/yellow]")

def cmd_bash(cmd=None):
    """Executa comando bash"""
    if not cmd:
        cmd = Prompt.ask("[bold]Comando bash[/bold]")
    if not cmd:
        return

    console.print(f"[dim]$ {cmd}[/dim]")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Comando excedeu o tempo limite (30s).[/red]")
    except Exception as e:
        console.print(f"[red]Erro: {e}[/red]")

def cmd_search(query=None):
    """Placeholder para busca web"""
    if not query:
        query = Prompt.ask("[bold]Termo de busca[/bold]")
    console.print(f"[yellow]Busca web por '{query}': funcionalidade em desenvolvimento.[/yellow]")
    console.print("[dim]Será integrado com a API de busca NVIDIA.[/dim]")

def cmd_fetch(url=None):
    """Placeholder para fetch URL"""
    if not url:
        url = Prompt.ask("[bold]URL[/bold]")
    console.print(f"[yellow]Fetch de '{url}': funcionalidade em desenvolvimento.[/yellow]")

def cmd_todo():
    """Placeholder para todo list"""
    console.print("[yellow]Todo List: funcionalidade em desenvolvimento.[/yellow]")

def cmd_agents():
    """Placeholder para agents"""
    console.print("[yellow]Custom Agents: funcionalidade em desenvolvimento.[/yellow]")

def cmd_hook(action=None, arg=None):
    """Hook management (delegates to cmd_hooks)"""
    cmd_hooks(action, arg)

def cmd_permissions():
    """Placeholder para permissions"""
    console.print("[yellow]Permission Modes: funcionalidade em desenvolvimento.[/yellow]")

def cmd_sandbox():
    """Placeholder para sandbox"""
    console.print("[yellow]Sandbox Mode: funcionalidade em desenvolvimento.[/yellow]")

def cmd_mcp(action=None, arg=None):
    """MCP management (delegates to cmd_mcp)"""
    cmd_mcp(action, arg)

def cmd_telemetry():
    """Placeholder para telemetry"""
    console.print("[yellow]Telemetry: funcionalidade em desenvolvimento.[/yellow]")

def cmd_theme():
    """Placeholder para theme"""
    console.print("[yellow]Theme Selection: funcionalidade em desenvolvimento.[/yellow]")

def cmd_export():
    """Placeholder para export"""
    console.print("[yellow]Export Conversation: funcionalidade em desenvolvimento.[/yellow]")

def cmd_import():
    """Placeholder para import"""
    console.print("[yellow]Import Conversation: funcionalidade em desenvolvimento.[/yellow]")

def cmd_reset():
    """Reset config"""
    if Confirm.ask("[bold red]Tem certeza? Isso apagará ~/.amplicode_config.json[/bold red]", default=False):
        try:
            os.remove(CONFIG_PATH)
            console.print("[green]✓ Configurações removidas. Reinicie o AmpliCode.[/green]")
        except IOError as e:
            console.print(f"[red]Erro: {e}[/red]")

def cmd_update():
    """Placeholder para update check"""
    console.print("[yellow]Update Check: funcionalidade em desenvolvimento.[/yellow]")
    console.print("[dim]O AmpliCode verificará novas versões no repositório.[/dim]")

def cmd_review():
    """Revisa alterações com IA"""
    if not is_git_repo():
        console.print("[red]Erro: Não está em um repositório Git.[/red]")
        return

    diff = git_diff()
    if not diff:
        console.print("[yellow]Nenhuma alteração para revisar.[/yellow]")
        return

    console.print("[dim]Analisando alterações com IA...[/dim]")
    model_config = get_current_model_config()
    if not model_config:
        console.print("[red]Nenhum modelo selecionado.[/red]")
        return

    client = create_nvidia_client(model_config["api_key"])
    model_id = model_config.get("model_id", "nvidia/llama-3.1-8b-instruct")

    prompt = f"""You are a code reviewer. Review this git diff and provide constructive feedback.

Diff:
{diff[:3000]}

Review:"""

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.5,
            stream=False
        )
        review = response.choices[0].message.content
        console.print("\n[bold green]Revisão da IA:[/bold green]")
        console.print(review)
    except Exception as e:
        console.print(f"[red]Erro na revisão: {e}[/red]")

def process_command(input_text):
    """Processa comandos que começam com /"""
    parts = input_text[1:].strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None

    # Skills Superpowers (/brainstorming, /test-driven-development, etc.)
    if cmd in SUPERPOWERS_SKILLS:
        skill = SUPERPOWERS_SKILLS[cmd]
        console.print(f"\n[bold cyan]Skill: {cmd}[/bold cyan]")
        console.print("[dim]Processando com Superpowers...[/dim]\n")
        # Aqui invocaria o prompt do skill
        console.print(skill["prompt"][:500] + "...")  # Preview
        return

    # Comandos principais
    if cmd == "btw":
        cmd_btw(arg)
    elif cmd == "setup":
        cmd_setup()
    elif cmd == "addmodel":
        cmd_addmodel()
    elif cmd == "models":
        cmd_models()
    elif cmd == "sessions":
        if arg:
            if arg.startswith("delete "):
                delete_session(arg[7:].strip())
            else:
                resume_session(arg)
        else:
            list_sessions()
    elif cmd == "save":
        save_session(arg)
    elif cmd == "resume":
        if arg:
            resume_session(arg)
        else:
            console.print("[red]Uso: /resume <nome-ou-id>[/red]")
    elif cmd == "history":
        show_history()
    elif cmd == "help":
        cmd_help()
    elif cmd == "readfile":
        cmd_readfile(arg)
    elif cmd == "clear":
        cmd_clear()
    elif cmd == "tokens":
        cmd_tokens()
    elif cmd == "cost":
        cmd_cost()
    elif cmd == "compact":
        cmd_compact()
    elif cmd == "status":
        cmd_status()
    elif cmd == "commit":
        cmd_commit()
    elif cmd == "diff":
        cmd_diff(arg)
    elif cmd == "branch":
        cmd_branch(arg)
    elif cmd == "pr":
        cmd_pr(arg)
    elif cmd == "review":
        cmd_review()
    elif cmd == "version":
        cmd_version()
    elif cmd == "undo":
        cmd_undo()
    elif cmd == "redo":
        cmd_redo()
    elif cmd == "bash":
        cmd_bash(arg)
    elif cmd == "search":
        cmd_search(arg)
    elif cmd == "fetch":
        cmd_fetch(arg)
    elif cmd == "todo":
        cmd_todo()
    elif cmd == "agents":
        cmd_agents(arg)
    elif cmd == "skills":
        list_skills()
    elif cmd == "hook":
        # Parse: /hook <action> [arg]
        hook_arg = None
        if arg:
            parts = arg.split(maxsplit=1)
            hook_action = parts[0]
            hook_arg = parts[1] if len(parts) > 1 else None
        else:
            hook_action = None
        cmd_hook(hook_action, hook_arg)
    elif cmd == "permissions":
        cmd_permissions(arg)
    elif cmd == "sandbox":
        cmd_sandbox()
    elif cmd == "mcp":
        # Parse: /mcp <action> [arg]
        mcp_arg = None
        if arg:
            parts = arg.split(maxsplit=1)
            mcp_action = parts[0]
            mcp_arg = parts[1] if len(parts) > 1 else None
        else:
            mcp_action = None
        cmd_mcp(mcp_action, mcp_arg)
    elif cmd == "telemetry":
        cmd_telemetry()
    elif cmd == "theme":
        cmd_theme()
    elif cmd == "settings":
        # Parse: /settings <action> [key] [value]
        if arg:
            parts = arg.split(maxsplit=2)
            set_action = parts[0]
            set_key = parts[1] if len(parts) > 1 else None
            set_value = parts[2] if len(parts) > 2 else None
        else:
            set_action = None
            set_key = None
            set_value = None
        cmd_settings(set_action, set_key, set_value)
    elif cmd == "export":
        cmd_export()
    elif cmd == "import":
        cmd_import()
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "update":
        cmd_update()
    elif cmd in ["exit", "quit"]:
        console.print("[yellow]Saindo do AmpliCode. Até mais![/yellow]")
        sys.exit(0)
    else:
        console.print(f"[red]Comando desconhecido: /{cmd}[/red]")
        console.print("[dim]Digite /help para ver comandos disponíveis.[/dim]")

# Bloco 7 concluído: Command Handler (39 commands)

def check_file_operations(response):
    """
    Verifica se a resposta da IA contém WRITE_FILE ou PATCH_FILE.
    Se encontrar, pede confirmação do usuário antes de aplicar.
    """
    # Check for WRITE_FILE
    if "WRITE_FILE:" in response:
        # Parse WRITE_FILE block
        import re
        pattern = r'WRITE_FILE:\s*(\S+)\s*```(?:[\w+]*)\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)

        for path, content in matches:
            path = path.strip()
            console.print()
            console.print(f"[bold yellow]IA quer escrever arquivo:[/bold yellow] {path}")
            console.print(f"[dim]{len(content)} caracteres[/dim]")

            if Confirm.ask("Deseja aplicar esta alteração?", default=True):
                full_path = os.path.join(WORK_DIR, path) if not os.path.isabs(path) else path
                sucesso, msg = write_file(full_path, content)
                if sucesso:
                    console.print(f"[green]✓ {msg}[/green]")
                else:
                    console.print(f"[red]Erro: {msg}[/red]")
            else:
                console.print("[yellow]Operação cancelada pelo usuário.[/yellow]")

    # Check for PATCH_FILE
    if "PATCH_FILE:" in response:
        pattern = r'PATCH_FILE:\s*(\S+)\s*SEARCH:\s*(.*?)\s*REPLACE:\s*(.*?)(?=PATCH_FILE:|WRITE_FILE:|$)'
        matches = re.findall(pattern, response, re.DOTALL)

        for path, search_text, replace_text in matches:
            path = path.strip()
            console.print()
            console.print(f"[bold yellow]IA quer patchar arquivo:[/bold yellow] {path}")
            console.print(f"[dim]Busca: {search_text[:50]}...[/dim]")

            if Confirm.ask("Deseja aplicar esta alteração?", default=True):
                full_path = os.path.join(WORK_DIR, path) if not os.path.isabs(path) else path
                sucesso, msg = patch_file(full_path, search_text.strip(), replace_text.strip())
                if sucesso:
                    console.print(f"[green]✓ {msg}[/green]")
                else:
                    console.print(f"[red]Erro: {msg}[/red]")
            else:
                console.print("[yellow]Operação cancelada pelo usuário.[/yellow]")

# ==================== MAIN LOOP (REPL) ====================

def main():
    """Função principal - REPL loop"""
    # Verificação de dependências
    dependency_check()

    # Garante pastas necessárias
    ensure_sessions_dir()

    # Verifica configuração
    ensure_config()

    # Scan work directory if WORK_DIR is set
    scanned = False
    if WORK_DIR and os.path.isdir(WORK_DIR):
        scan_work_dir()
        scanned = bool(WORK_DIR_CONTEXT)

    # Limpa tela e mostra cabeçalho
    ansi_clear_screen()

    # Banner: AMPLI CODE (clean text only)
    banner = (
        "\033[1;96m\n"
        "  A   M   P   L   I     C   O   D   E  \n"
        "\033[0m"
        "\033[96m       IA Oficial da AmpliDEV — Divisão de Software da AmpliGroup\033[0m\n"
    )
    sys.stdout.write(banner)
    sys.stdout.flush()


    show_welcome_banner()

    # Inject work dir context as system message
    if scanned:
        system_msg = f"""You are AmpliCode, an AI Programming Assistant developed by AmpliDEV (AmpliGroup).
You have FULL access to the working directory and terminal.

Available tools (you can request the user to execute these):
- write_file(path, content): Create or overwrite a file
- patch_file(path, search_text, replace_text): Surgical edit (replace specific text)
- read_file(path): Read a specific file when you need details
- run_terminal_command(command): Execute shell commands (ls, mkdir, python3, etc.)

Project files from: {WORK_DIR}

{WORK_DIR_CONTEXT}

When asked to create/modify code, output in this format:
WRITE_FILE: path/to/file.py
```
file content here
```

or:
PATCH_FILE: path/to/file.py
SEARCH: exact text to find
REPLACE: new text

Or request terminal execution:
RUN_COMMAND: ls -la

The user will confirm before applying any changes or executing commands.
Use read_file to dynamically request files - keeps context light and fast on Core 2 Duo."""
        conversation_history.append({"role": "system", "content": system_msg})
        console.print(f"[dim]Contexto inicial injetado: {len(WORK_DIR_FILES)} arquivos ({len(WORK_DIR_CONTEXT)} chars)[/dim]")

    config = load_config()
    current_model = config.get("current_model", "não selecionado")

    while True:
        try:
            # Prompt de entrada estilo Claude Code
            user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Saindo do AmpliCode. Até mais![/yellow]")
            break

        if not user_input.strip():
            continue

        # Comando especial
        if user_input.startswith('/'):
            process_command(user_input)
            continue

        # Salva mensagem do usuário
        conversation_history.append({"role": "user", "content": user_input})

        # Mostra mensagem do usuário
        render_user_message(user_input)

        # Mostra spinner de loading
        ansi_spinner(start=True, message=f"Processando com {current_model}...")

        # Envia para NVIDIA API (streaming)
        response, error = send_to_nvidia(user_input, use_stream=True)

        # Limpa spinner
        ansi_spinner(start=False)

        if error:
            render_error(error)
            conversation_history.pop()  # Remove mensagem que falhou
            continue

        if response:
            # Mensagem já foi exibida via streaming
            conversation_history.append({"role": "assistant", "content": response})

            # Verifica se a IA quer escrever/patchar arquivo
            check_file_operations(response)

            # Verifica se a IA quer executar comando
            if "RUN_COMMAND:" in response:
                import re
                pattern = r'RUN_COMMAND:\s*(.+)'
                matches = re.findall(pattern, response)
                for cmd in matches:
                    cmd = cmd.strip()
                    sucesso, output = run_terminal_command(cmd)
                    if sucesso:
                        console.print(f"[green]✓ Comando executado:[/green]")
                        console.print(output[:500] if output else "(sem saída)")
                    else:
                        console.print(f"[red]Erro: {output}[/red]")

            # Verifica se precisa compactar
            auto_compact_if_needed()

        # Atualiza cabeçalho com novos tokens
        clear_and_show_header()

    # Cleanup antes de sair
    ansi_show_cursor()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        ansi_show_cursor()
        console.print("\n[yellow]Interrompido pelo usuário.[/yellow]")
        sys.exit(0)
    except Exception as e:
        ansi_show_cursor()
        console.print(f"\n[red]Erro inesperado: {e}[/red]")
        sys.exit(1)

# Bloco 8 + 9 concluídos: Main Loop + Entry Point
# AmpliCode v1.0.0 - Código completo (Single File)
# Próximo passo: Criar README.md
