#!/usr/bin/env python3
"""
Teste local simples - Verifica se as correções foram aplicadas
NÃO requer dependências externas, apenas lê o código fonte
"""

import os
import sys

# Cores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'

def print_header(text):
    """Imprime cabeçalho"""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{END}")
    print(f"{BOLD}{BLUE}{text.center(70)}{END}")
    print(f"{BOLD}{BLUE}{'=' * 70}{END}\n")

def print_success(text):
    """Imprime sucesso"""
    print(f"{GREEN}✅ {text}{END}")

def print_error(text):
    """Imprime erro"""
    print(f"{RED}❌ {text}{END}")

def print_info(text):
    """Imprime info"""
    print(f"{BLUE}ℹ️  {text}{END}")

def verificar_correcao_intexportada():
    """Verifica se intExportada foi descomentado"""
    print_info("Verificando arquivo intimation_service.py...")

    arquivo = "app/services/intimation_service.py"

    if not os.path.exists(arquivo):
        print_error(f"Arquivo não encontrado: {arquivo}")
        return False

    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
        linhas = conteudo.split('\n')

    # Verificar se intExportada está DESCOMENTADO (ativo)
    encontrou_ativo = False
    encontrou_comentado = False
    linha_ativa = -1
    linha_comentada = -1

    for i, linha in enumerate(linhas, 1):
        # Buscar linha com intExportada ativo (não comentado)
        if '"intExportada": 0' in linha and not linha.strip().startswith('#'):
            encontrou_ativo = True
            linha_ativa = i

        # Buscar linha comentada
        if '# "intExportada": 0' in linha or '#"intExportada": 0' in linha:
            encontrou_comentado = True
            linha_comentada = i

    print()
    if encontrou_ativo:
        print_success(f"Parâmetro intExportada ATIVO encontrado na linha {linha_ativa}")
        print(f"   Linha {linha_ativa}: {linhas[linha_ativa-1].strip()}")
        resultado = True
    else:
        print_error("Parâmetro intExportada NÃO ENCONTRADO na forma ativa")
        resultado = False

    if encontrou_comentado:
        print_error(f"⚠️  ATENÇÃO: Ainda há linha comentada na linha {linha_comentada}")
        print(f"   Linha {linha_comentada}: {linhas[linha_comentada-1].strip()}")

    return resultado

def verificar_logs_adicionados():
    """Verifica se os logs foram adicionados"""
    print_info("Verificando se logs detalhados foram adicionados...")

    arquivo = "app/services/intimation_service.py"

    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    logs_esperados = [
        '📤 Parâmetros SOAP',
        '📥 Resultado:',
        '⚠️ NENHUMA PUBLICAÇÃO ENCONTRADA',
        '📤 Buscando publicações não exportadas',
        '📥 Obtidas %d publicações não exportadas',
    ]

    print()
    todos_encontrados = True
    for log in logs_esperados:
        if log in conteudo:
            print_success(f"Log encontrado: '{log}'")
        else:
            print_error(f"Log NÃO encontrado: '{log}'")
            todos_encontrados = False

    return todos_encontrados

def verificar_estrutura_params():
    """Verifica estrutura do dicionário params"""
    print_info("Verificando estrutura do dicionário params...")

    arquivo = "app/services/intimation_service.py"

    with open(arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    # Procurar por params = { ... intExportada ... }
    dentro_params = False
    tem_data_inicial = False
    tem_data_final = False
    tem_cod_grupo = False
    tem_int_exportada = False
    tem_versao = False

    for i, linha in enumerate(linhas):
        if 'params = {' in linha:
            dentro_params = True
        elif dentro_params and '}' in linha:
            dentro_params = False

        if dentro_params:
            if 'dteDataInicial' in linha:
                tem_data_inicial = True
            if 'dteDataFinal' in linha:
                tem_data_final = True
            if 'intCodGrupo' in linha:
                tem_cod_grupo = True
            if '"intExportada"' in linha and not linha.strip().startswith('#'):
                tem_int_exportada = True
            if 'numVersao' in linha:
                tem_versao = True

    print()
    campos = {
        'dteDataInicial': tem_data_inicial,
        'dteDataFinal': tem_data_final,
        'intCodGrupo': tem_cod_grupo,
        'intExportada': tem_int_exportada,
        'numVersao': tem_versao,
    }

    todos_presentes = True
    for campo, presente in campos.items():
        if presente:
            print_success(f"Campo '{campo}' presente")
        else:
            print_error(f"Campo '{campo}' AUSENTE ou comentado")
            todos_presentes = False

    return todos_presentes

def main():
    """Executa testes"""
    print_header("VALIDAÇÃO LOCAL DAS CORREÇÕES")

    print_info("Diretório atual: " + os.getcwd())
    print()

    # Testes
    resultados = {
        'intExportada_ativo': False,
        'logs_adicionados': False,
        'estrutura_params': False,
    }

    print_header("TESTE 1: Parâmetro intExportada")
    resultados['intExportada_ativo'] = verificar_correcao_intexportada()

    print_header("TESTE 2: Logs Detalhados")
    resultados['logs_adicionados'] = verificar_logs_adicionados()

    print_header("TESTE 3: Estrutura do Dicionário params")
    resultados['estrutura_params'] = verificar_estrutura_params()

    # Resumo
    print_header("RESUMO DOS TESTES")

    sucesso_total = all(resultados.values())

    for teste, passou in resultados.items():
        status = f"{GREEN}✅ PASSOU{END}" if passou else f"{RED}❌ FALHOU{END}"
        print(f"  {teste}: {status}")

    print()
    if sucesso_total:
        print_success("TODAS AS CORREÇÕES FORAM APLICADAS CORRETAMENTE!")
        print()
        print_info("Próximos passos:")
        print("  1. Reinicie o API Gateway: docker-compose restart gateway")
        print("  2. Monitore os logs para ver mensagens como:")
        print("     📤 Parâmetros SOAP: periodo=... cod_grupo=... intExportada=0")
        print("     📥 Resultado: X publicações encontradas...")
        print()
        return 0
    else:
        print_error("ALGUMAS CORREÇÕES ESTÃO FALTANDO!")
        print()
        print_info("Revise o arquivo app/services/intimation_service.py")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
