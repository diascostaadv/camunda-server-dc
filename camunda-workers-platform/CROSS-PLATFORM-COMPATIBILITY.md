# Cross-Platform Compatibility Guide

## Detecção Automática de Sistema Operacional

O Makefile agora detecta automaticamente o sistema operacional e configura os comandos apropriados para cada plataforma.

### Sistemas Suportados

#### Windows
- **Detecção**: Variável de ambiente `OS=Windows_NT`
- **Python**: `python` (padrão no Windows)
- **Shell**: `cmd`
- **Separador de path**: `\`
- **Extensão executável**: `.exe`

#### macOS
- **Detecção**: `uname -s` retorna `Darwin`
- **Python**: Detecta automaticamente `python3` ou fallback para `python`
- **Shell**: `bash`
- **Separador de path**: `/`
- **Extensão executável**: (nenhuma)

#### Linux
- **Detecção**: `uname -s` retorna `Linux`
- **Python**: Detecta automaticamente `python3` ou fallback para `python`
- **Shell**: `bash`
- **Separador de path**: `/`
- **Extensão executável**: (nenhuma)

### Como Funciona a Detecção

```makefile
# Detecta o sistema operacional
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    PYTHON_CMD := python
else
    ifeq ($(UNAME_S),Linux)
        DETECTED_OS := Linux
    endif
    ifeq ($(UNAME_S),Darwin)
        DETECTED_OS := macOS
    endif
    
    # Para Unix-like, testa se python3 existe
    PYTHON_CMD := $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)
endif
```

### Variáveis Configuradas Automaticamente

- `DETECTED_OS`: Sistema operacional detectado
- `PYTHON_CMD`: Comando Python apropriado (`python3` ou `python`)
- `SHELL_CMD`: Shell padrão (`bash` ou `cmd`)
- `PATH_SEP`: Separador de caminhos (`/` ou `\`)
- `EXE_EXT`: Extensão de executáveis (`.exe` ou vazio)

### Comandos Atualizados

Todos os comandos Python agora usam `$(PYTHON_CMD)` em vez de hardcoded `python` ou `python3`:

```makefile
list-workers:
    @cd workers && $(PYTHON_CMD) _config/worker_discovery.py --list

new-worker:
    @cd workers && $(PYTHON_CMD) _config/new-worker.py

generate-compose:
    @cd workers && $(PYTHON_CMD) _config/generate-compose.py
```

### Verificando a Configuração

Use o comando `make system-info` para ver as configurações detectadas:

```bash
make system-info
```

Saída exemplo no macOS:
```
🖥️ System Information:
  OS: macOS
  Architecture: arm64
  Python Command: python3
  Shell: bash
  Path Separator: /
  Environment: local

Python Version:
Python 3.12.9
```

### Solução de Problemas

#### Python não encontrado
Se o Python não for encontrado, instale-o:

**Windows:**
```cmd
# Via Microsoft Store ou python.org
# Certifique-se que está no PATH
```

**macOS:**
```bash
# Via Homebrew
brew install python3

# Via MacPorts
sudo port install python311
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

#### Comando específico não funciona
Para forçar um comando específico, defina a variável:

```bash
make list-workers PYTHON_CMD=python3.11
```

### Vantagens da Implementação

1. **Compatibilidade automática**: Funciona em Windows, macOS e Linux sem modificações
2. **Detecção inteligente**: Prefere `python3` quando disponível, fallback para `python`
3. **Flexibilidade**: Permite override manual das variáveis se necessário
4. **Transparência**: `make system-info` mostra exatamente o que está sendo usado
5. **Manutenção**: Centralizada - mudanças em um lugar afetam todos os comandos

### Extensões Futuras

Essa base pode ser estendida para:
- Detecção de gerenciadores de pacote (pip, pip3, pipx)
- Configuração automática de paths
- Detecção de ferramentas específicas (Docker, git, etc.)
- Configurações específicas por distribuição Linux