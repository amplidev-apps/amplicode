# AmpliCode

**IA Oficial da AmpliDEV — Divisão de Software da AmpliGroup**

AmpliCode é um clone funcional e visualmente idêntico ao Claude Code v2, adaptado para o ecossistema NVIDIA e otimizado para hardware limitado (Core 2 Duo com Linux).

## Diferenciais

### 🚀 Portabilidade Absoluta
Código contido em um único arquivo de fácil distribuição (`ia_terminal.py`). Sem dependências pesadas, sem complexidade de build. Apenas baixe, configure e use.

### ⚡ Otimização de Hardware
Design focado em performance para processadores Core 2 Duo (Zero-Bloat). Utiliza manipulação direta de buffer de terminal (ANSI Escapes) para garantir fluidez sem renderização de GPU.

### 🔥 Integração com NVIDIA
Uso nativo da infraestrutura NVIDIA API para máxima velocidade de resposta. Suporte a múltiplos modelos via sistema de gestão dinâmico de APIs.

### 🧠 Workflow Superpowers
Inclusão de comandos avançados de Git e gestão de sessões para criadores e desenvolvedores. Recursos de brainstorming, debugging e execução de planos embutidos nativamente.

## Novidades da v2.0.0

### 🔐 Permission System (6 Modos)
Controle granular sobre execução de ferramentas:
- `bypass`: Todos os comandos aprovados automaticamente
- `acceptEdits`: Edições automáticas, outros pedem confirmação
- `auto`: Comandos seguros automáticos, outros pedem confirmação
- `default`: Sempre pede confirmação (padrão)
- `dontAsk`: Bloqueia execução de ferramentas
- `plan`: Modo somente leitura

Use `/permissions <mode>` para alterar.

### 🪝 Hooks Engine (7 Eventos)
Automatize tarefas com hooks em eventos:
- `PreToolUse`: Antes de qualquer ferramenta
- `PostToolUse`: Após execução de ferramenta
- `PostEdit`: Após edições de arquivo
- `PostSessionStart`: Após carregar sessão
- `PostSessionEnd`: Antes de encerrar sessão
- `Notification`: Em notificações
- `Stop`: Em interrupções

Gerencie com `/hook <action> [arg]`.

### 🔌 MCP Client (4 Transportes)
Conecte servidores MCP (Model Context Protocol):
- **stdio**: Processos locais via stdin/stdout
- **sse**: Server-Sent Events (HTTP)
- **streamable-http**: HTTP com streaming
- **in-process**: Módulos Python carregados diretamente

Gerencie com `/mcp <action> [args]`.

### ⚙️ Settings Chain (5 Camadas)
Configurações hierárquicas:
1. **Defaults**: Valores padrão no código
2. **Project**: `.amplicode/settings.json`
3. **User**: `~/.amplicode/settings.json`
4. **Session**: Carregado com a sessão
5. **Command-line**: Na inicialização

Gerencie com `/settings <action> [key] [value]`.

### 🤖 Custom Agents
Agentes personalizados definidos em arquivos JSON ou Markdown (com frontmatter YAML):
- Salve em `~/.amplicode/agents/` (usuário) ou `.amplicode/agents/` (projeto)
- Liste com `/agents`
- Carregue com `/agents load`

### 💡 BTW (Brainstorming Twist)
Injeta contexto sem bloquear o pipeline atual (TDD, Debugging, etc.):
```
/btw Lembre-se: a função X deve ser async
```
A nota é adicionada ao histórico como mensagem do sistema, sem interromper fluxos em andamento.

## Instalação

### Dependências
```bash
pip install rich openai
```

### Download e Configuração
```bash
# Clone o repositório
git clone https://github.com/amplidev-apps/amplicode.git
cd amplicode

# Torne executável (opcional)
chmod +x ia_terminal.py

# Crie um alias (recomendado)
echo "alias amplicode='python3 $(pwd)/ia_terminal.py'" >> ~/.bashrc
source ~/.bashrc
```

### Uso Rápido
```bash
# Inicia no diretório atual (mapeia como contexto de trabalho)
amplicode .

# Inicia em um diretório específico
amplicode /caminho/para/projeto

# Inicia sem contexto de diretório
amplicode
```

## Primeiro Uso

Na primeira execução, o AmpliCode iniciará automaticáticamente o wizard de configuração:

```bash
python3 ia_terminal.py
# ou simplesmente:
amplicode
```

### Adicionando um Modelo NVIDIA

1. Obtenha sua API Key em: https://build.nvidia.com/explore/discover
2. Use o comando `/addmodel` dentro do AmpliCode
3. Preencha:
   - **Nome Amigável**: Ex: "Llama 3.1 8B"
   - **NVIDIA API Key**: Seu `nvapi-...`
   - **Model ID**: Ex: `nvidia/llama-3.1-8b-instruct`

## Comandos Principais (39 Total)

### Básicos
| Comando | Descrição |
|---------|-----------|
| `/btw <msg>` | Brainstorming Twist (non-blocking) |
| `/setup` | Executar wizard de configuração |
| `/addmodel` | Adicionar novo modelo NVIDIA |
| `/models` | Listar e selecionar modelos |
| `/help` | Listar todos os comandos |
| `/quit` | Sair do AmpliCode |

### Sessões
| Comando | Descrição |
|---------|-----------|
| `/sessions` | Gerenciar sessões salvas |
| `/save [nome]` | Salvar sessão atual |
| `/resume <id>` | Retomar sessão salva |
| `/history` | Ver histórico da sessão |
| `/clear` | Limpar histórico e contexto |

### Git
| Comando | Descrição |
|---------|-----------|
| `/commit` | Auto-commit Git com IA |
| `/diff [file]` | Mostrar git diff + análise IA |
| `/pr [title]` | Criar Pull Request com IA |
| `/branch <name>` | Criar nova branch Git |
| `/review` | Revisar alterações com IA |

### Arquivos e Edição
| Comando | Descrição |
|---------|-----------|
| `/readfile <path>` | Adicionar arquivo ao contexto |
| `/bash <cmd>` | Executar comando bash |
| `/tokens` | Mostrar uso de tokens |
| `/cost` | Mostrar custo da sessão |
| `/compact` | Compactar janela de contexto |

### Superpowers & Extensões
| Comando | Descrição |
|---------|-----------|
| `/skills` | Listar skills Superpowers |
| `/brainstorming` | Iniciar brainstorming |
| `/test-driven-development` | TDD workflow |
| `/systematic-debugging` | Debug sistemático |
| `/agents` | Listar agentes customizados |

### Sistema
| Comando | Descrição |
|---------|-----------|
| `/permissions <mode>` | Alterar modo de permissão |
| `/hook <action>` | Gerenciar hooks |
| `/mcp <action>` | Gerenciar servidores MCP |
| `/settings <action>` | Gerenciar configurações |
| `/status` | Mostrar status atual |

## Arquitetura

```
ia_terminal.py (~2700 linhas, arquivo único)
├── Config Manager (load/save/validate config)
├── ANSI Terminal UI (direct stdout, no GPU)
├── NVIDIA API Client (streaming + error handling)
├── Session Persistence (save/resume/list)
├── Permission System (6 modos)
├── Hooks Engine (7 eventos)
├── MCP Client (4 transportes)
├── Settings Chain (5 camadas)
├── Custom Agents (JSON/Markdown)
├── Superpowers Skills (frozen snapshot)
├── Git Operations (commit/diff/pr/branch)
├── Command Handler (39 commands)
└── Main Loop (REPL)
```

## Recursos de IA

### Ferramentas de Edição (Superpowers)
O AmpliCode possui capacidade de **ler, escrever e editar arquivos** no diretório de trabalho:

**Comandos de Arquivo:**
- **Write File**: IA pode criar/sobrescrever arquivos
- **Patch File**: Edição cirúrgica (substitui trecho específico)
- **Read File**: Lê arquivo específico sob demanda (contexto dinâmico)

**Segurança:**
- Sempre que a IA tentar escrever/patchar um arquivo, o terminal exibe: *"Deseja aplicar esta alteração? (s/n)"*
- O usuário tem controle total sobre o que é modificado

### Session Persistence
O AmpliCode permite salvar e retomar sessões completas:

```bash
# Salvar sessão atual
/save meu-projeto

# Listar sessões
/sessions

# Retomar sessão
/resume meu-projeto
```

Sessões são salvas em `~/.amplicode/sessions/` como arquivos JSON individuais.

### Superpowers Integration
O AmpliCode inclui nativamente as skills do projeto [Superpowers](https://github.com/obra/superpowers.git):

- **Brainstorming**: Ideação colaborativa com design visual
- **Test-Driven Development**: Desenvolvimento orientado a testes
- **Systematic Debugging**: Depuração sistemática de erros
- **Writing Plans**: Criação de planos de implementação
- **Executing Plans**: Execução de planos com checkpoints

Use `/skills` para listar e `/<skill-name>` para invocar.

### Git Workflow
Integração nativa com Git para desenvolvedores:

```bash
# Verificar alterações
/diff

# Fazer commit automático (mensagem gerada por IA)
/commit

# Criar Pull Request
/pr "Implementa nova funcionalidade"

# Criar nova branch
/branch feature-nova
```

## Compatibilidade

- **Sistema Operacional**: Linux (testado no Ubuntu 22.04)
- **Hardware**: Otimizado para Core 2 Duo (x86_64)
- **Python**: 3.8+
- **Dependências**: `rich`, `openai`

## Repositório

Código fonte e atualizações:  
🔗 [git@github.com:amplidev-apps/amplicode.git](https://github.com/amplidev-apps/amplicode)

## Manifesto da Marca

O AmpliCode nasce sob o **Ethos de Negócio da AmpliGroup**: independência absoluta e técnica refinada. Projetado para ser uma ferramenta de desenvolvimento completa, mantendo a compatibilidade com hardware legado e a portabilidade que define a AmpliDEV.

---

**AmpliCode v2.0.0** — *IA Oficial da AmpliDEV*  
Desenvolvido com 🧡 pela Divisão de Software da AmpliGroup
