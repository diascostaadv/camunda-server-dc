#!/usr/bin/env python3
"""
Script de Verificação de Saúde - Workers e Gateway
Verifica sintaxe, imports e problemas comuns
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

# Cores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title: str):
    """Imprime cabeçalho de seção"""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}{title:^70}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")


def check_syntax(file_path: str) -> Tuple[bool, str]:
    """
    Verifica sintaxe de arquivo Python

    Returns:
        (sucesso, mensagem_erro)
    """
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def check_imports(file_path: str) -> List[str]:
    """
    Verifica imports que podem estar faltando

    Returns:
        Lista de problemas encontrados
    """
    problems = []

    # Padrões comuns de uso sem import
    patterns = [
        ("time.time()", "import time"),
        ("time.sleep(", "import time"),
        ("datetime.now()", "from datetime import datetime"),
        ("json.dumps(", "import json"),
        ("json.loads(", "import json"),
        ("logging.getLogger", "import logging"),
        ("requests.get(", "import requests"),
        ("requests.post(", "import requests"),
    ]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extrair imports
        import_lines = [line for line in content.split('\n') if line.strip().startswith(('import ', 'from '))]
        imports_text = '\n'.join(import_lines)

        # Verificar cada padrão
        for usage, required_import in patterns:
            if usage in content and required_import not in imports_text:
                problems.append(f"Usa '{usage}' mas falta '{required_import}'")

    except Exception as e:
        problems.append(f"Erro ao ler arquivo: {e}")

    return problems


def verify_gateway():
    """Verifica arquivos do Gateway"""
    print_section("GATEWAY - Verificação")

    base_path = Path("camunda-worker-api-gateway/app")
    files_to_check = [
        "main.py",
        "services/lote_service.py",
        "services/intimation_service.py",
        "routers/buscar_publicacoes.py",
        "routers/publicacoes.py",
    ]

    all_ok = True

    for file_rel in files_to_check:
        file_path = base_path / file_rel

        if not file_path.exists():
            print(f"{YELLOW}⚠️  {file_rel}: Arquivo não encontrado{RESET}")
            continue

        print(f"📄 Verificando: {file_rel}")

        # Sintaxe
        ok, error = check_syntax(str(file_path))
        if ok:
            print(f"   {GREEN}✅ Sintaxe OK{RESET}")
        else:
            print(f"   {RED}❌ Erro de sintaxe:{RESET}")
            print(f"      {error}")
            all_ok = False

        # Imports
        problems = check_imports(str(file_path))
        if problems:
            print(f"   {YELLOW}⚠️  Possíveis imports faltando:{RESET}")
            for problem in problems:
                print(f"      - {problem}")
            all_ok = False
        else:
            print(f"   {GREEN}✅ Imports OK{RESET}")

        print()

    return all_ok


def verify_workers():
    """Verifica arquivos dos Workers"""
    print_section("WORKERS - Verificação")

    base_path = Path("camunda-workers-platform/workers")
    files_to_check = [
        "common/base_worker.py",
        "common/gateway_client.py",
        "publicacao_unified/main.py",
    ]

    all_ok = True

    for file_rel in files_to_check:
        file_path = base_path / file_rel

        if not file_path.exists():
            print(f"{YELLOW}⚠️  {file_rel}: Arquivo não encontrado{RESET}")
            continue

        print(f"📄 Verificando: {file_rel}")

        # Sintaxe
        ok, error = check_syntax(str(file_path))
        if ok:
            print(f"   {GREEN}✅ Sintaxe OK{RESET}")
        else:
            print(f"   {RED}❌ Erro de sintaxe:{RESET}")
            print(f"      {error}")
            all_ok = False

        # Imports
        problems = check_imports(str(file_path))
        if problems:
            print(f"   {YELLOW}⚠️  Possíveis imports faltando:{RESET}")
            for problem in problems:
                print(f"      - {problem}")
            all_ok = False
        else:
            print(f"   {GREEN}✅ Imports OK{RESET}")

        print()

    return all_ok


def check_docker_containers():
    """Verifica status dos containers Docker"""
    print_section("DOCKER CONTAINERS - Status")

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(result.stdout)

            # Verificar containers específicos
            required_containers = [
                "gateway",
                "camunda",
                "postgres",
                "mongodb",
                "rabbitmq",
                "redis",
            ]

            running_containers = result.stdout.lower()

            print(f"\n{BLUE}Verificando containers críticos:{RESET}\n")
            all_running = True

            for container in required_containers:
                if container in running_containers:
                    print(f"   {GREEN}✅ {container} está rodando{RESET}")
                else:
                    print(f"   {RED}❌ {container} NÃO encontrado{RESET}")
                    all_running = False

            return all_running
        else:
            print(f"{RED}❌ Erro ao verificar containers: {result.stderr}{RESET}")
            return False

    except Exception as e:
        print(f"{RED}❌ Erro ao executar docker ps: {e}{RESET}")
        return False


def check_gateway_health():
    """Verifica saúde do Gateway via HTTP"""
    print_section("GATEWAY - Health Check HTTP")

    try:
        import requests

        gateway_url = "http://localhost:8000/health"

        print(f"📡 Testando: {gateway_url}")

        response = requests.get(gateway_url, timeout=5)

        if response.status_code == 200:
            print(f"{GREEN}✅ Gateway está respondendo (HTTP 200){RESET}")

            try:
                data = response.json()
                print(f"\n   Status: {data.get('status', 'unknown')}")

                # Verificar componentes
                components = data.get('components', {})
                if components:
                    print(f"\n   {BLUE}Componentes:{RESET}")
                    for name, status in components.items():
                        if status == 'healthy':
                            print(f"      {GREEN}✅ {name}: {status}{RESET}")
                        else:
                            print(f"      {RED}❌ {name}: {status}{RESET}")
            except:
                print(f"   Resposta: {response.text[:200]}")

            return True
        else:
            print(f"{RED}❌ Gateway retornou HTTP {response.status_code}{RESET}")
            return False

    except ImportError:
        print(f"{YELLOW}⚠️  Módulo 'requests' não instalado - pulando teste HTTP{RESET}")
        return None
    except Exception as e:
        print(f"{RED}❌ Erro ao testar Gateway: {e}{RESET}")
        return False


def main():
    """Função principal"""
    print(f"{BLUE}")
    print("=" * 70)
    print("  VERIFICAÇÃO DE SAÚDE - CAMUNDA ECOSYSTEM")
    print("=" * 70)
    print(f"{RESET}")

    # Verificar se estamos no diretório correto
    if not Path("camunda-worker-api-gateway").exists():
        print(f"{RED}❌ Erro: Execute este script na raiz do projeto{RESET}")
        print(f"   Diretório atual: {os.getcwd()}")
        sys.exit(1)

    results = {}

    # 1. Verificar arquivos Python
    results['gateway_files'] = verify_gateway()
    results['worker_files'] = verify_workers()

    # 2. Verificar Docker
    results['docker'] = check_docker_containers()

    # 3. Health Check HTTP
    results['gateway_http'] = check_gateway_health()

    # Resumo final
    print_section("RESUMO FINAL")

    status_map = {
        True: f"{GREEN}✅ OK{RESET}",
        False: f"{RED}❌ ERRO{RESET}",
        None: f"{YELLOW}⚠️  PULADO{RESET}",
    }

    print(f"Gateway Files:     {status_map.get(results['gateway_files'], '?')}")
    print(f"Worker Files:      {status_map.get(results['worker_files'], '?')}")
    print(f"Docker Containers: {status_map.get(results['docker'], '?')}")
    print(f"Gateway HTTP:      {status_map.get(results['gateway_http'], '?')}")

    # Exit code
    all_ok = all(v in [True, None] for v in results.values())

    if all_ok:
        print(f"\n{GREEN}{'=' * 70}")
        print(f"  ✅ TODAS AS VERIFICAÇÕES PASSARAM")
        print(f"{'=' * 70}{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}{'=' * 70}")
        print(f"  ❌ ALGUNS PROBLEMAS FORAM ENCONTRADOS")
        print(f"{'=' * 70}{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
