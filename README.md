# AmpliCode

**IA Oficial da AmpliDEV — Divisão de Software da AmpliGroup**

AmpliCode é um clone funcional e visualmente idêntico ao Open-Claude-Code, adaptado para o ecossistema NVIDIA e otimizado para hardware limitado (Core 2 Duo com Linux).

## Diferenciais

### 🚀 Portabilidade Absoluta
Código contido em um único arquivo de fácil distribuição (`ia_terminal.py`). Sem dependências pesadas, sem complexidade de build. Apenas baixe, configure e use.

### ⚡ Otimização de Hardware
Design focado em performance para processadores Core 2 Duo (Zero-Bloat). Utiliza manipulação direta de buffer de terminal (ANSI Escapes) para garantir fluidez sem renderização de GPU.

### 🔥 Integração com NVIDIA
Uso nativo da infraestrutura NVIDIA API para máxima velocidade de resposta. Suporte a múltiplos modelos via sistema de gestão dinâmico de APIs.

### 🧠 Workflow Superpowers
Inclusão de comandos avançados de Git e gestão de sessões para criadores e desenvolvedores. Recursos de brainstorming, debugging e execução de planos embutidos nativamente.

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

## Comandos Principais

| Comando | Descrição |
|---------|-------------|
| `/setup` | Executar wizard de configuração |
| `/addmodel` | Adicionar novo modelo NVIDIA |
| `/models` | Listar e selecionar modelos |
| `/sessions` | Gerenciar sessões salvas |
| `/save [nome]` | Salvar sessão atual |
| `/resume <id>` | Retomar sessão salva |
| `/commit` | Auto-commit Git com IA |
| `/diff [file]` | Mostrar git diff + análise IA |
| `/pr [title]` | Criar Pull Request com IA |
| `/help` | Listar todos os 39 comandos |
| `/quit` | Sair do AmpliCode |

## Novidades da v1.0.0

### 🚀 Argumentos de Linha de Comando
Agora o AmpliCode aceita argumentos na inicialização:

```bash
# Mapeia diretório atual como contexto de trabalho
amplicode .

# Mapeia diretório específico
amplicode /caminho/para/projeto

# Mostra ajuda
amplicode --help

# Mostra versão
amplicode --version
```

### ⚡ Otimização Core 2 Duo (ANSI Fluido)
- Streaming direto via `sys.stdout.write()` + `flush()` (zero buffer)
- Cabeçalho renderizado em uma única operação de escrita
- Mensagens com bordas ANSI pré-processadas (mínimo de syscalls)
- Sem threads para UI, sem Rich Live (economia de CPU e memória)

### 📂 Mapeamento de Contexto
Quando iniciado com `amplicode .`, o diretório atual é mapeado como contexto de trabalho, permitindo que o AmpliCode acesse arquivos locais mais rápido para análise de código.

## Recursos de IA

### Ferramentas de Edição (Superpowers)
O AmpliCode agora possui capacidade de **ler, escrever e editar arquivos** no diretório de trabalho:

**Comandos de Arquivo:**
- **Write File**: IA pode criar/sobrescrever arquivos
- **Patch File**: Edição cirúrgica (substitui trecho específico, evita reescrever arquivo inteiro)
- **Read File**: Lê arquivo específico sob demanda (contexto dinâmico)

**Segurança:**
- Sempre que a IA tentar escrever/patchar um arquivo, o terminal exibe: *"Deseja aplicar esta alteração? (s/n)"*
- O usuário tem controle total sobre o que é modificado

### Session Persistence

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

## Arquitetura

```
ia_terminal.py (~2000 linhas, arquivo único)
├── Config Manager (load/save/validate config)
├── ANSI Terminal UI (direct stdout, no GPU)
├── NVIDIA API Client (streaming + error handling)
├── Session Persistence (save/resume/list)
├── Superpowers Skills (frozen snapshot)
├── Git Operations (commit/diff/pr/branch)
├── Command Handler (39 commands)
└── Main Loop (REPL)
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

**AmpliCode v1.0.0** — *IA Oficial da AmpliDEV*  
Desenvolvido com 🧡 pela Divisão de Software da AmpliGroup
