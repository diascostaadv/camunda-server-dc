#!/usr/bin/env python3
"""
Script para debugar XML bruto da API SOAP
Exibe exatamente o que a API está retornando
"""

import sys
import os
import requests
from datetime import datetime

# Credenciais
USUARIO = "100049"
SENHA = "DcDpW@24"
URL = "https://intimation-panel.azurewebsites.net/wsPublicacao.asmx"

def build_soap_request(method, params):
    """Constrói envelope SOAP"""
    param_elements = ""
    for key, value in params.items():
        if value is not None:
            param_elements += f"<{key}>{value}</{key}>"

    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <{method} xmlns="http://tempuri.org/">
            {param_elements}
        </{method}>
    </soap:Body>
</soap:Envelope>"""

def test_request(method, params, description):
    """Faz requisição e exibe XML bruto"""
    print(f"\n{'='*70}")
    print(f"TESTE: {description}")
    print(f"Método: {method}")
    print(f"Parâmetros: {params}")
    print(f"{'='*70}\n")

    # Adicionar credenciais
    params.update({"strUsuario": USUARIO, "strSenha": SENHA})

    # Montar envelope
    soap_body = build_soap_request(method, params)

    print("📤 REQUEST SOAP:")
    print(soap_body)

    # Headers
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"http://tempuri.org/{method}"',
    }

    try:
        print(f"\n⏳ Enviando requisição para {URL}...")
        response = requests.post(URL, data=soap_body, headers=headers, timeout=90)

        print(f"\n✅ Status: {response.status_code}")
        print(f"⏱️  Tempo: {response.elapsed.total_seconds():.2f}s")
        print(f"📦 Tamanho: {len(response.text)} bytes\n")

        print("📥 RESPONSE SOAP (COMPLETO):")
        print(response.text)

        # Análise básica
        if '<ArrayOfPublicacaoV2 />' in response.text or '<ArrayOfPublicacaoV2/>' in response.text:
            print("\n⚠️  ANÁLISE: Array de publicações VAZIO detectado")
        elif 'publicacaoV2' in response.text.lower():
            print("\n✅ ANÁLISE: Publicações encontradas no XML!")
        else:
            print("\n❓ ANÁLISE: Formato de resposta inesperado")

        return response.text

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        return None

def main():
    """Executa testes"""
    print("=" * 70)
    print("DEBUG SOAP XML - API DE INTIMAÇÕES")
    print("=" * 70)
    print(f"URL: {URL}")
    print(f"Usuário: {USUARIO}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # TESTE 1: getPublicacoesV com período recente
    test_request(
        method="getPublicacoesV",
        params={
            "dteDataInicial": "2025-09-28",
            "dteDataFinal": "2025-10-28",
            "intCodGrupo": 5,
            "intExportada": 0,
            "numVersao": 5
        },
        description="Buscar publicações por período (grupo 5, últimos 30 dias)"
    )

    input("\n\nPressione ENTER para próximo teste...")

    # TESTE 2: getPublicacoesV com grupo 0
    test_request(
        method="getPublicacoesV",
        params={
            "dteDataInicial": "2025-09-28",
            "dteDataFinal": "2025-10-28",
            "intCodGrupo": 0,
            "intExportada": 0,
            "numVersao": 5
        },
        description="Buscar publicações por período (grupo 0, últimos 30 dias)"
    )

    input("\n\nPressione ENTER para próximo teste...")

    # TESTE 3: getPublicacoesNaoExportadas
    test_request(
        method="getPublicacoesNaoExportadas",
        params={
            "intCodGrupo": 5
        },
        description="Buscar publicações não exportadas (grupo 5)"
    )

    input("\n\nPressione ENTER para próximo teste...")

    # TESTE 4: getPublicacoesNaoExportadas grupo 0
    test_request(
        method="getPublicacoesNaoExportadas",
        params={
            "intCodGrupo": 0
        },
        description="Buscar publicações não exportadas (grupo 0)"
    )

    input("\n\nPressione ENTER para próximo teste...")

    # TESTE 5: getEstatisticasPublicacoes
    test_request(
        method="getEstatisticasPublicacoes",
        params={
            "dteData": "2025-10-28",
            "intCodGrupo": 5,
            "strTipoAgrupamento": "",
            "numVersao": 1
        },
        description="Buscar estatísticas de publicações"
    )

    input("\n\nPressione ENTER para próximo teste...")

    # TESTE 6: Período de 2024 (dados históricos)
    test_request(
        method="getPublicacoesV",
        params={
            "dteDataInicial": "2024-08-01",
            "dteDataFinal": "2024-08-31",
            "intCodGrupo": 5,
            "intExportada": 0,
            "numVersao": 5
        },
        description="Buscar publicações agosto/2024 (grupo 5)"
    )

    print("\n" + "=" * 70)
    print("TESTES CONCLUÍDOS")
    print("=" * 70)
    print("\n💡 PRÓXIMOS PASSOS:")
    print("1. Analise os XMLs acima")
    print("2. Verifique se há mensagens de erro no XML")
    print("3. Compare com documentação da API")
    print("4. Entre em contato com suporte da API se necessário")

if __name__ == "__main__":
    main()
