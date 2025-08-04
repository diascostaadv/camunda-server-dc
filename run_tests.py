#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar suites de testes específicas
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", verbose=False, coverage=True, markers=None):
    """Executa testes baseado no tipo especificado"""
    
    # Comando base do pytest
    cmd = ["python", "-m", "pytest"]
    
    # Adicionar verbosidade
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Configurar cobertura
    if coverage:
        cmd.extend([
            "--cov=camunda-swarm/workers",
            "--cov-report=html:reports/htmlcov",
            "--cov-report=term-missing"
        ])
    
    # Configurar relatório HTML
    cmd.extend(["--html=reports/test_report.html", "--self-contained-html"])
    
    # Adicionar markers específicos
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])
    
    # Configurar diretórios de teste baseado no tipo
    if test_type == "unit":
        cmd.append("tests/unit/")
        if not markers:
            cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.append("tests/integration/")
        if not markers:
            cmd.extend(["-m", "integration"])
    elif test_type == "e2e":
        cmd.append("tests/e2e/")
        if not markers:
            cmd.extend(["-m", "e2e"])
    elif test_type == "smoke":
        cmd.append("tests/")
        cmd.extend(["-m", "smoke"])
    elif test_type == "worker":
        cmd.append("tests/")
        cmd.extend(["-m", "worker"])
    elif test_type == "api":
        cmd.append("tests/")
        cmd.extend(["-m", "api"])
    elif test_type == "csrf":
        cmd.append("tests/")
        cmd.extend(["-m", "csrf"])
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"❌ Tipo de teste desconhecido: {test_type}")
        return False
    
    print(f"🧪 Executando testes: {test_type}")
    print(f"📋 Comando: {' '.join(cmd)}")
    print("=" * 60)
    
    # Executar testes
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n⚠️  Testes interrompidos pelo usuário")
        return False
    except Exception as e:
        print(f"❌ Erro ao executar testes: {e}")
        return False

def install_dependencies():
    """Instala dependências de teste"""
    print("📦 Instalando dependências de teste...")
    
    try:
        subprocess.run([
            "pip", "install", "-r", "requirements-test.txt"
        ], check=True)
        print("✅ Dependências instaladas com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

def create_reports_dir():
    """Cria diretório de relatórios se não existir"""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "htmlcov").mkdir(exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description="Executor de testes do projeto Camunda")
    
    parser.add_argument(
        "test_type", 
        nargs="?", 
        default="all",
        choices=["all", "unit", "integration", "e2e", "smoke", "worker", "api", "csrf"],
        help="Tipo de teste para executar"
    )
    
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Modo verboso"
    )
    
    parser.add_argument(
        "--no-coverage", 
        action="store_true",
        help="Desabilitar relatório de cobertura"
    )
    
    parser.add_argument(
        "-m", "--markers",
        nargs="+",
        help="Markers específicos do pytest para filtrar testes"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true", 
        help="Instalar dependências antes de executar"
    )
    
    args = parser.parse_args()
    
    # Criar diretório de relatórios
    create_reports_dir()
    
    # Instalar dependências se solicitado
    if args.install_deps:
        if not install_dependencies():
            sys.exit(1)
    
    # Executar testes
    success = run_tests(
        test_type=args.test_type,
        verbose=args.verbose,
        coverage=not args.no_coverage,
        markers=args.markers
    )
    
    if success:
        print("\n🎉 Testes executados com sucesso!")
        print(f"📊 Relatórios disponíveis em: reports/")
        sys.exit(0)
    else:
        print("\n❌ Alguns testes falharam!")
        sys.exit(1)

if __name__ == "__main__":
    main()
