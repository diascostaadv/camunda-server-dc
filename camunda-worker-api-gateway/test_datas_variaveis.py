#!/usr/bin/env python3
"""
Teste com várias datas - Tenta encontrar período com dados
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.intimation_service import IntimationService
from datetime import datetime, timedelta

# Cores
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
END = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 70}{END}")
    print(f"{BOLD}{BLUE}{text.center(70)}{END}")
    print(f"{BOLD}{BLUE}{'=' * 70}{END}\n")

def testar_periodo(service, data_inicial, data_final, cod_grupo, descricao):
    """Testa um período específico"""
    print(f"{BOLD}📅 {descricao}{END}")
    print(f"   Período: {data_inicial} a {data_final}, Grupo: {cod_grupo}")

    try:
        pubs = service.get_publicacoes_periodo_safe(
            data_inicial,
            data_final,
            cod_grupo=cod_grupo
        )

        if len(pubs) > 0:
            print(f"   {GREEN}✅ {len(pubs)} publicações encontradas!{END}\n")
            return True, len(pubs)
        else:
            print(f"   {YELLOW}⚠️  0 publicações{END}\n")
            return False, 0

    except Exception as e:
        print(f"   {RED}❌ ERRO: {str(e)[:100]}{END}\n")
        return False, 0

def main():
    """Testa vários períodos"""
    print_header("TESTE COM MÚLTIPLAS DATAS")

    service = IntimationService(usuario='100049', senha='DcDpW@24')

    # Data atual
    hoje = datetime.now()

    # Períodos para testar (datas reais, não futuras)
    periodos_teste = [
        # Últimos 30 dias
        ((hoje - timedelta(days=30)).strftime("%Y-%m-%d"),
         hoje.strftime("%Y-%m-%d"),
         5,
         "Últimos 30 dias (grupo 5)"),

        # Últimos 60 dias
        ((hoje - timedelta(days=60)).strftime("%Y-%m-%d"),
         hoje.strftime("%Y-%m-%d"),
         5,
         "Últimos 60 dias (grupo 5)"),

        # Últimos 90 dias
        ((hoje - timedelta(days=90)).strftime("%Y-%m-%d"),
         hoje.strftime("%Y-%m-%d"),
         5,
         "Últimos 90 dias (grupo 5)"),

        # Outubro 2024
        ("2024-10-01", "2024-10-31", 5, "Outubro 2024 (grupo 5)"),

        # Setembro 2024
        ("2024-09-01", "2024-09-30", 5, "Setembro 2024 (grupo 5)"),

        # Agosto 2024
        ("2024-08-01", "2024-08-31", 5, "Agosto 2024 (grupo 5)"),

        # Julho 2024
        ("2024-07-01", "2024-07-31", 5, "Julho 2024 (grupo 5)"),

        # Janeiro 2025
        ("2025-01-01", "2025-01-31", 5, "Janeiro 2025 (grupo 5)"),

        # Fevereiro 2025
        ("2025-02-01", "2025-02-28", 5, "Fevereiro 2025 (grupo 5)"),

        # Testar grupo 0 também
        ((hoje - timedelta(days=90)).strftime("%Y-%m-%d"),
         hoje.strftime("%Y-%m-%d"),
         0,
         "Últimos 90 dias (grupo 0)"),

        # Testar grupo 2 também
        ((hoje - timedelta(days=90)).strftime("%Y-%m-%d"),
         hoje.strftime("%Y-%m-%d"),
         2,
         "Últimos 90 dias (grupo 2)"),
    ]

    resultados = []

    for data_ini, data_fim, grupo, desc in periodos_teste:
        sucesso, total = testar_periodo(service, data_ini, data_fim, grupo, desc)
        if sucesso:
            resultados.append((desc, total))

    # Resumo
    print_header("RESUMO - PERÍODOS COM DADOS")

    if resultados:
        print(f"{GREEN}✅ Encontrados dados em {len(resultados)} período(s):{END}\n")
        for desc, total in resultados:
            print(f"   • {desc}: {total} publicações")
    else:
        print(f"{RED}❌ NENHUM PERÍODO RETORNOU DADOS!{END}\n")
        print(f"{YELLOW}Possíveis causas:{END}")
        print("   1. Credenciais incorretas (usuário: 100049)")
        print("   2. Grupos 0, 2, 5 não têm publicações não exportadas")
        print("   3. Problema com o servidor da API SOAP")
        print("   4. Parâmetro intExportada=0 está filtrando tudo")
        print()
        print(f"{CYAN}Sugestões:{END}")
        print("   1. Verificar credenciais com o fornecedor da API")
        print("   2. Testar sem intExportada (buscar todas as publicações)")
        print("   3. Contactar suporte da API de intimações")

    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  Teste interrompido{END}\n")
    except Exception as e:
        print(f"\n\n{RED}❌ ERRO: {e}{END}\n")
        import traceback
        traceback.print_exc()
