#!/usr/bin/env python3
"""
Teste de múltiplos grupos - Verifica qual grupo tem dados
Testa grupos 0, 1, 2, 3, 4, 5 para encontrar onde há publicações
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.intimation_service import IntimationService

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

def testar_grupo(service, grupo, data_inicial, data_final):
    """Testa um grupo específico"""
    print(f"{BOLD}🧪 Testando GRUPO {grupo}:{END}")
    print(f"   Período: {data_inicial} a {data_final}")

    try:
        pubs = service.get_publicacoes_periodo_safe(
            data_inicial,
            data_final,
            cod_grupo=grupo
        )

        if len(pubs) > 0:
            print(f"   {GREEN}✅ {len(pubs)} publicações encontradas!{END}")

            # Mostra detalhes da primeira publicação
            pub = pubs[0]
            print(f"\n   {BOLD}📄 Amostra (primeira publicação):{END}")
            print(f"      • Código: {pub.cod_publicacao}")
            print(f"      • Data: {pub.data_publicacao}")
            print(f"      • UF: {pub.uf_publicacao}")
            print(f"      • Processo: {pub.numero_processo}")
            print(f"      • Órgão: {pub.orgao_descricao}")
            print(f"      • Exportada: {pub.publicacao_exportada}")

            # Estatísticas
            exportadas = sum(1 for p in pubs if p.publicacao_exportada == 1)
            nao_exportadas = len(pubs) - exportadas

            print(f"\n   {BOLD}📊 Estatísticas:{END}")
            print(f"      • Total: {len(pubs)}")
            print(f"      • Não exportadas: {nao_exportadas}")
            print(f"      • Exportadas: {exportadas}")

            return True, len(pubs), nao_exportadas, exportadas
        else:
            print(f"   {YELLOW}⚠️  0 publicações (grupo vazio ou sem dados){END}")
            return False, 0, 0, 0

    except Exception as e:
        print(f"   {RED}❌ ERRO: {e}{END}")
        return False, 0, 0, 0

def main():
    """Executa testes em múltiplos grupos"""
    print_header("TESTE DE MÚLTIPLOS GRUPOS - BUSCA DE PUBLICAÇÕES")

    print(f"{CYAN}Inicializando serviço...{END}")
    service = IntimationService(usuario='100049', senha='DcDpW@24')

    # Períodos para testar
    periodos = [
        ("2025-10-28", "2025-10-28", "28/10/2025 (hoje)"),
        ("2025-10-01", "2025-10-28", "Outubro/2025 completo"),
        ("2025-08-01", "2025-10-28", "Agosto-Outubro/2025"),
    ]

    # Grupos para testar
    grupos = [0, 1, 2, 3, 4, 5]

    # Resultados
    resultados = {}

    for data_inicial, data_final, descricao in periodos:
        print_header(f"PERÍODO: {descricao}")
        print(f"Datas: {data_inicial} a {data_final}\n")

        resultados[descricao] = {}

        for grupo in grupos:
            sucesso, total, nao_exp, exp = testar_grupo(
                service, grupo, data_inicial, data_final
            )
            resultados[descricao][grupo] = {
                'sucesso': sucesso,
                'total': total,
                'nao_exportadas': nao_exp,
                'exportadas': exp
            }
            print()  # Linha em branco entre grupos

    # Resumo final
    print_header("RESUMO GERAL")

    for periodo, grupos_resultado in resultados.items():
        print(f"\n{BOLD}{CYAN}📅 {periodo}{END}")

        grupos_com_dados = {
            g: r for g, r in grupos_resultado.items() if r['total'] > 0
        }

        if grupos_com_dados:
            for grupo, stats in grupos_com_dados.items():
                print(f"   {GREEN}✅ Grupo {grupo}: {stats['total']} total "
                      f"({stats['nao_exportadas']} não exportadas, "
                      f"{stats['exportadas']} exportadas){END}")
        else:
            print(f"   {RED}❌ Nenhum grupo retornou dados neste período{END}")

    # Recomendações
    print_header("RECOMENDAÇÕES")

    # Encontrar grupo com mais dados
    melhor_grupo = None
    max_publicacoes = 0

    for periodo, grupos_resultado in resultados.items():
        for grupo, stats in grupos_resultado.items():
            if stats['total'] > max_publicacoes:
                max_publicacoes = stats['total']
                melhor_grupo = grupo

    if melhor_grupo is not None:
        print(f"{GREEN}✅ GRUPO RECOMENDADO: {melhor_grupo}{END}")
        print(f"   Este grupo tem mais publicações ({max_publicacoes} no total)")
        print(f"\n{BOLD}💡 Configure cod_grupo={melhor_grupo} como padrão em:{END}")
        print(f"   • app/models/buscar_request.py (linha 14)")
        print(f"   • Ou passe cod_grupo={melhor_grupo} nas requisições\n")
    else:
        print(f"{RED}❌ NENHUM GRUPO RETORNOU DADOS{END}")
        print(f"\n{BOLD}Possíveis causas:{END}")
        print(f"   1. Credenciais incorretas")
        print(f"   2. Parâmetro intExportada ainda comentado")
        print(f"   3. API SOAP com problemas")
        print(f"   4. Períodos testados não têm dados\n")

    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  Teste interrompido pelo usuário{END}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}❌ ERRO FATAL: {e}{END}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
