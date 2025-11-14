#!/usr/bin/env python3
"""
Script de teste para cadastrar tarefa CPJ via Worker API Gateway
Endpoint: POST /cpj/tramitacao/tarefa/cadastrar/{pj}
"""

import requests
import json
from datetime import datetime

# Configurações
GATEWAY_URL = "http://localhost:8000"  # Ajustar conforme necessário
# GATEWAY_URL = "http://201.23.67.197:8080"  # URL de produção

def cadastrar_tarefa_cpj(pj: int, evento: str = "evento_cpj", texto: str = None,
                         id_pessoa_solicitada: int = 1, id_pessoa_atribuida: int = None):
    """
    Cadastra uma nova tarefa no CPJ via API Gateway

    Args:
        pj: Número do PJ do processo
        evento: Código do evento (default: "evento_cpj")
        texto: Descrição da tarefa
        id_pessoa_solicitada: ID da pessoa solicitante
        id_pessoa_atribuida: ID da pessoa atribuída (opcional)

    Returns:
        Response da API
    """
    # Data/hora atual no formato ISO
    data_hora_atual = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Preparar payload
    payload = {
        "evento": evento,
        "texto": texto or f"Tarefa criada automaticamente em {data_hora_atual}",
        "id_pessoa_solicitada": id_pessoa_solicitada,
        "ag_data_hora": data_hora_atual  # Data de agendamento = data de hoje
    }

    # Adicionar pessoa atribuída se fornecida
    if id_pessoa_atribuida:
        payload["id_pessoa_atribuida"] = id_pessoa_atribuida

    # URL do endpoint
    url = f"{GATEWAY_URL}/cpj/tramitacao/tarefa/cadastrar/{pj}"

    print("=" * 80)
    print("CADASTRANDO TAREFA CPJ")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("\n" + "=" * 80)

    try:
        # Fazer requisição
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        # Mostrar resultado
        print(f"\nStatus Code: {response.status_code}")
        print(f"\nResponse:")

        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))

            if result.get("success"):
                print(f"\n✅ SUCESSO! Tarefa cadastrada com ID: {result.get('id_tramitacao')}")
            else:
                print(f"\n❌ FALHA: {result.get('message')}")
        else:
            print(response.text)
            print(f"\n❌ ERRO HTTP: {response.status_code}")

        print("\n" + "=" * 80)
        return response

    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERRO DE CONEXÃO: Não foi possível conectar ao Gateway em {GATEWAY_URL}")
        print(f"   Verifique se o Gateway está rodando com: docker ps | grep gateway")
        print(f"   Erro: {e}")
        return None

    except requests.exceptions.Timeout:
        print(f"\n❌ TIMEOUT: A requisição excedeu 60 segundos")
        return None

    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        return None


def main():
    """
    Função principal - Executa teste de cadastro de tarefa
    """
    print("\n🧪 TESTE: Cadastrar Tarefa CPJ\n")

    # ===== CONFIGURAR AQUI OS DADOS DO TESTE =====

    # Número do PJ do processo (OBRIGATÓRIO)
    PJ_PROCESSO = 12345  # ⚠️ ALTERAR PARA UM PJ VÁLIDO!

    # Código do evento (OBRIGATÓRIO)
    EVENTO = "evento_cpj"

    # Texto/descrição da tarefa (OBRIGATÓRIO)
    TEXTO = "Tarefa de teste criada via API Gateway"

    # ID da pessoa solicitante (OBRIGATÓRIO)
    ID_PESSOA_SOLICITADA = 1  # ⚠️ ALTERAR PARA UM ID VÁLIDO!

    # ID da pessoa atribuída (OPCIONAL)
    ID_PESSOA_ATRIBUIDA = 2  # ⚠️ ALTERAR PARA UM ID VÁLIDO OU None!

    # ==============================================

    # Executar teste
    response = cadastrar_tarefa_cpj(
        pj=PJ_PROCESSO,
        evento=EVENTO,
        texto=TEXTO,
        id_pessoa_solicitada=ID_PESSOA_SOLICITADA,
        id_pessoa_atribuida=ID_PESSOA_ATRIBUIDA
    )

    if response and response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"\n🎉 Teste concluído com sucesso!")
            print(f"   ID Tramitação: {result.get('id_tramitacao')}")
        else:
            print(f"\n⚠️  Teste falhou: {result.get('message')}")
    else:
        print(f"\n⚠️  Teste não foi concluído devido a erros")


if __name__ == "__main__":
    main()
