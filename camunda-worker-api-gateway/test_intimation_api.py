#!/usr/bin/env python3
"""
Script de teste isolado para API SOAP de Intimações
Diagnostica problemas com busca de publicações

Uso:
    python test_intimation_api.py
"""

import sys
import os
import json
import time
from datetime import datetime, date, timedelta

# Adicionar path do projeto para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.intimation_service import IntimationService

# Configurações
USUARIO = "100049"
SENHA = "DcDpW@24"

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Imprime cabeçalho formatado"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")

def print_test(number, total, description):
    """Imprime início de teste"""
    print(f"{Colors.BOLD}[{number}/{total}] {description}...{Colors.END}")

def print_success(message):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    """Imprime mensagem de erro"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message):
    """Imprime mensagem de aviso"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message):
    """Imprime mensagem informativa"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def test_connection(service):
    """Testa conexão com a API"""
    print_test(1, 7, "Testando conexão com API")

    try:
        start = time.time()
        result = service.test_connection()
        elapsed = time.time() - start

        if result:
            print_success(f"Conexão OK (tempo: {elapsed:.2f}s)")
            return True
        else:
            print_error("Falha na conexão")
            return False
    except Exception as e:
        print_error(f"Erro na conexão: {e}")
        return False

def test_periodo(service, data_inicial, data_final, cod_grupo, descricao):
    """Testa busca de publicações por período"""
    print(f"  📅 Período: {data_inicial} a {data_final}")
    print(f"  🏷️  Grupo: {cod_grupo}")

    try:
        start = time.time()
        publicacoes = service.get_publicacoes_periodo_safe(
            data_inicial=data_inicial,
            data_final=data_final,
            cod_grupo=cod_grupo,
            timeout_override=90
        )
        elapsed = time.time() - start

        print(f"  ⏱️  Tempo: {elapsed:.2f}s")
        print(f"  📊 Resultado: {len(publicacoes)} publicações encontradas")

        if len(publicacoes) > 0:
            print_success(f"{descricao}: {len(publicacoes)} publicações")
            print(f"\n  {Colors.BOLD}Amostra (primeira publicação):{Colors.END}")
            pub = publicacoes[0]
            print(f"    - Código: {pub.cod_publicacao}")
            print(f"    - Data: {pub.data_publicacao}")
            print(f"    - Processo: {pub.numero_processo}")
            print(f"    - Órgão: {pub.orgao_descricao}")
            print(f"    - Texto: {pub.texto_publicacao[:100]}...")
            return True
        else:
            print_warning(f"{descricao}: Nenhuma publicação encontrada")
            return False

    except Exception as e:
        print_error(f"{descricao}: Erro - {e}")
        return False

def test_periodo_atual(service):
    """Testa período atual (2025-08-01 a hoje)"""
    print_test(2, 7, "Testando período atual (2025-08-01 a hoje)")

    hoje = datetime.now().strftime("%Y-%m-%d")
    return test_periodo(service, "2025-08-01", hoje, 5, "Período atual (grupo 5)")

def test_periodo_agosto_2024(service):
    """Testa agosto de 2024"""
    print_test(3, 7, "Testando agosto de 2024")

    return test_periodo(service, "2024-08-01", "2024-08-31", 5, "Agosto 2024 (grupo 5)")

def test_periodo_2024_completo(service):
    """Testa ano 2024 completo"""
    print_test(4, 7, "Testando ano 2024 completo (pode demorar)")

    # Dividir em trimestres para evitar timeout
    trimestres = [
        ("2024-01-01", "2024-03-31", "Q1 2024"),
        ("2024-04-01", "2024-06-30", "Q2 2024"),
        ("2024-07-01", "2024-09-30", "Q3 2024"),
        ("2024-10-01", "2024-12-31", "Q4 2024"),
    ]

    total_encontradas = 0
    for inicio, fim, desc in trimestres:
        print(f"\n  {Colors.BOLD}Testando {desc}...{Colors.END}")
        try:
            pubs = service.get_publicacoes_periodo_safe(inicio, fim, 5, 90)
            print(f"    {desc}: {len(pubs)} publicações")
            total_encontradas += len(pubs)
        except Exception as e:
            print_error(f"    {desc}: Erro - {e}")

    print(f"\n  {Colors.BOLD}Total 2024: {total_encontradas} publicações{Colors.END}")
    return total_encontradas > 0

def test_grupos_diferentes(service):
    """Testa grupos diferentes"""
    print_test(5, 7, "Testando grupos diferentes")

    # Período recente para teste rápido
    hoje = datetime.now()
    data_final = hoje.strftime("%Y-%m-%d")
    data_inicial = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"  📅 Período de teste: {data_inicial} a {data_final}")

    grupos_teste = [0, 5, 1, 2, 3]
    resultados = {}

    for grupo in grupos_teste:
        try:
            start = time.time()
            pubs = service.get_publicacoes_periodo_safe(
                data_inicial, data_final, grupo, 90
            )
            elapsed = time.time() - start
            resultados[grupo] = len(pubs)

            if len(pubs) > 0:
                print_success(f"Grupo {grupo}: {len(pubs)} publicações (tempo: {elapsed:.2f}s)")
            else:
                print(f"  Grupo {grupo}: 0 publicações (tempo: {elapsed:.2f}s)")

        except Exception as e:
            print_error(f"Grupo {grupo}: Erro - {e}")
            resultados[grupo] = -1

    # Encontrar grupo com mais dados
    grupo_com_dados = max(resultados, key=resultados.get)
    if resultados[grupo_com_dados] > 0:
        print(f"\n  {Colors.BOLD}💡 Grupo com mais dados: {grupo_com_dados} ({resultados[grupo_com_dados]} publicações){Colors.END}")
        return True
    else:
        print_warning("Nenhum grupo retornou dados")
        return False

def test_nao_exportadas(service):
    """Testa busca de publicações não exportadas"""
    print_test(6, 7, "Testando publicações não exportadas")

    grupos_teste = [0, 5]

    for grupo in grupos_teste:
        try:
            start = time.time()
            pubs = service.get_publicacoes_nao_exportadas(grupo)
            elapsed = time.time() - start

            print(f"  Grupo {grupo}: {len(pubs)} publicações não exportadas (tempo: {elapsed:.2f}s)")

            if len(pubs) > 0:
                print_success(f"Grupo {grupo} tem {len(pubs)} publicações não exportadas")
                print(f"\n  {Colors.BOLD}Amostra (primeira publicação):{Colors.END}")
                pub = pubs[0]
                print(f"    - Código: {pub.cod_publicacao}")
                print(f"    - Data: {pub.data_publicacao}")
                print(f"    - Processo: {pub.numero_processo}")
                return True

        except Exception as e:
            print_error(f"Grupo {grupo}: Erro - {e}")

    print_warning("Nenhuma publicação não exportada encontrada")
    return False

def test_estatisticas(service):
    """Testa estatísticas de publicações"""
    print_test(7, 7, "Testando estatísticas de publicações")

    # Testar últimos 7 dias
    for i in range(7):
        data_teste = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

        try:
            stats = service.get_estatisticas_publicacoes(data_teste, cod_grupo=5)

            if stats and stats.total_publicacoes > 0:
                print_success(f"Data {data_teste}: {stats.total_publicacoes} publicações")
                print(f"    - Total não importadas: {stats.total_nao_importadas}")
                return True
            else:
                print(f"  Data {data_teste}: 0 publicações")

        except Exception as e:
            print(f"  Data {data_teste}: Erro - {e}")

    print_warning("Nenhuma estatística com dados encontrada nos últimos 7 dias")
    return False

def print_diagnostico(resultados):
    """Imprime diagnóstico final"""
    print_header("DIAGNÓSTICO")

    if resultados['conexao']:
        print_success("API está funcionando corretamente")
    else:
        print_error("Problema de conexão com a API")
        return

    if any([resultados['periodo_atual'], resultados['periodo_2024'],
            resultados['grupos'], resultados['nao_exportadas'], resultados['estatisticas']]):
        print_success("API retorna dados em alguns cenários")
    else:
        print_error("API não retorna dados em nenhum cenário testado")

    print(f"\n{Colors.BOLD}Resumo:{Colors.END}")
    print(f"  - Período atual (2025-08-01 a hoje, grupo 5): {'✅' if resultados['periodo_atual'] else '❌'}")
    print(f"  - Período 2024 (grupo 5): {'✅' if resultados['periodo_2024'] else '❌'}")
    print(f"  - Outros grupos: {'✅' if resultados['grupos'] else '❌'}")
    print(f"  - Não exportadas: {'✅' if resultados['nao_exportadas'] else '❌'}")
    print(f"  - Estatísticas: {'✅' if resultados['estatisticas'] else '❌'}")

    print(f"\n{Colors.BOLD}Possíveis causas:{Colors.END}")

    if not resultados['periodo_atual'] and not resultados['grupos']:
        print_warning("Não há dados para cod_grupo=5 no período especificado")
        print_info("Sugestão: Verificar se o grupo correto está sendo usado")

    if resultados['grupos']:
        print_info("Dados encontrados em outros grupos - verificar configuração do cod_grupo")

    if not any([r for r in resultados.values()]):
        print_warning("Possível problema com credenciais ou permissões")
        print_info(f"Credenciais usadas: usuário={USUARIO}")

def main():
    """Função principal"""
    print_header("TESTE API SOAP DE INTIMAÇÕES")

    print_info(f"Usuário: {USUARIO}")
    print_info(f"URL: https://intimation-panel.azurewebsites.net/wsPublicacao.asmx")

    # Inicializar serviço
    try:
        service = IntimationService(usuario=USUARIO, senha=SENHA, timeout=90, max_retries=1)
    except Exception as e:
        print_error(f"Erro ao inicializar serviço: {e}")
        return 1

    # Executar testes
    resultados = {
        'conexao': test_connection(service),
        'periodo_atual': False,
        'periodo_2024': False,
        'grupos': False,
        'nao_exportadas': False,
        'estatisticas': False,
    }

    if not resultados['conexao']:
        print_error("Abortando testes - sem conexão")
        return 1

    resultados['periodo_atual'] = test_periodo_atual(service)
    resultados['periodo_2024'] = test_periodo_agosto_2024(service)
    # resultados['periodo_2024_completo'] = test_periodo_2024_completo(service)  # Comentado - muito lento
    resultados['grupos'] = test_grupos_diferentes(service)
    resultados['nao_exportadas'] = test_nao_exportadas(service)
    resultados['estatisticas'] = test_estatisticas(service)

    # Diagnóstico
    print_diagnostico(resultados)

    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Testes concluídos{Colors.END}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
