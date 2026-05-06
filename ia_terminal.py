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

# ==================== COMMAND LINE ARGS ====================
WORK_DIR = os.getcwd()  # Default: current directory

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

# Dependências externas (verificadas na inicialização)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.box import ROUNDED, SIMPLE
    from rich.prompt import Prompt, Confirm
    import openai
except ImportError as e:
    print(f"Erro: Dependência faltando: {e}")
    print("Instale com: pip install rich openai")
    sys.exit(1)

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

def render_assitant_message_start():
    """Inicia mensagem da IA (prefixo 'AmpliCode' em verde) - uma única escrita"""
    sys.stdout.write("\033[1;92m  AmpliCode \033[0m")
    sys.stdout.flush()

def render_assistant_message_start():
    """Inicia mensagem da IA (prefixo 'AmpliCode' em verde)"""
    sys.stdout.write(COLOR_BOLD_GREEN + "  AmpliCode " + COLOR_RESET)
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
    console.print(Text("AmpliCode v" + AMPLI_VERSION + " — IA Oficial da AmpliDEV", style="bold cyan"))
    console.print(Text(f"Modelo: {model_name}", style="dim"))
    console.print(Text("Digite /help para comandos ou sua pergunta abaixo.", style="dim"))
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
        ("/setup", "Configurar/Adicionar modelo", "", ""),
        ("/addmodel", "Adicionar novo modelo NVIDIA", "/models", "Listar/Selecionar modelos"),
        ("/sessions", "Gerenciar sessões salvas", "/save [nome]", "Salvar sessão atual"),
        ("/resume <id>", "Retomar sessão salva", "/history", "Ver histórico da sessão"),
        ("/readfile <path>", "Adicionar arquivo ao contexto", "/clear", "Limpar histórico e contexto"),
        ("/tokens", "Mostrar uso de tokens", "/cost", "Mostrar custo da sessão"),
        ("/compact", "Compactar janela de contexto", "/status", "Mostrar status atual"),
        ("/commit", "Auto-commit Git com IA", "/diff [file]", "Mostrar git diff + IA"),
        ("/branch <name>", "Criar nova branch Git", "/pr [title]", "Criar Pull Request"),
        ("/review", "Revisar alterações (IA)", "", ""),
        ("/undo", "Desfazer última edição", "/redo", "Refazer edição"),
        ("/bash <cmd>", "Executar comando bash", "/search <query>", "Busca web"),
        ("/fetch <url>", "Buscar conteúdo de URL", "/todo", "Gerenciar lista de tarefas"),
        ("/agents", "Listar/Managar agentes", "/skills", "Listar skills Superpowers"),
        ("/hook", "Gerenciar eventos hook", "/permissions", "Modo de permissão"),
        ("/sandbox", "Ativar/Desativar sandbox", "/mcp", "Gerenciar servidores MCP"),
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

def cmd_hook():
    """Placeholder para hooks"""
    console.print("[yellow]Hook Events: funcionalidade em desenvolvimento.[/yellow]")

def cmd_permissions():
    """Placeholder para permissions"""
    console.print("[yellow]Permission Modes: funcionalidade em desenvolvimento.[/yellow]")

def cmd_sandbox():
    """Placeholder para sandbox"""
    console.print("[yellow]Sandbox Mode: funcionalidade em desenvolvimento.[/yellow]")

def cmd_mcp():
    """Placeholder para MCP"""
    console.print("[yellow]MCP Servers: funcionalidade em desenvolvimento.[/yellow]")

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
    if cmd == "setup":
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
        cmd_agents()
    elif cmd == "skills":
        list_skills()
    elif cmd == "hook":
        cmd_hook()
    elif cmd == "permissions":
        cmd_permissions()
    elif cmd == "sandbox":
        cmd_sandbox()
    elif cmd == "mcp":
        cmd_mcp()
    elif cmd == "telemetry":
        cmd_telemetry()
    elif cmd == "theme":
        cmd_theme()
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

# ==================== MAIN LOOP (REPL) ====================

def main():
    """Função principal - REPL loop"""
    # Verificação de dependências
    dependency_check()

    # Garante pastas necessárias
    ensure_sessions_dir()

    # Verifica configuração
    ensure_config()

    # Limpa tela e mostra cabeçalho
    clear_and_show_header()
    show_welcome_banner()

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
