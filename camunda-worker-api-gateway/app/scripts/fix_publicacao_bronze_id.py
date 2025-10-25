#!/usr/bin/env python3
"""
Script de migração para corrigir publicacao_bronze_id na camada Prata.

Problema: O campo publicacao_bronze_id estava sendo preenchido com cod_publicacao (int)
ao invés do _id do MongoDB (ObjectId).

Este script:
1. Busca todos os registros prata com publicacao_bronze_id inválido
2. Para cada registro, encontra o documento bronze correspondente via cod_publicacao
3. Atualiza o publicacao_bronze_id com o _id correto do bronze
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Configurações
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "publicacoes")

def conectar_mongodb():
    """Conecta ao MongoDB"""
    print(f"🔌 Conectando ao MongoDB: {MONGODB_URI}")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    return db

def is_valid_objectid(value):
    """Verifica se um valor é um ObjectId válido"""
    if not value:
        return False
    try:
        # ObjectId deve ter 24 caracteres hexadecimais
        if len(str(value)) != 24:
            return False
        ObjectId(value)
        return True
    except:
        return False

def migrar_publicacao(db, pub_prata):
    """
    Migra uma única publicação prata, corrigindo o publicacao_bronze_id.

    Args:
        db: Database connection
        pub_prata: Documento da publicação prata

    Returns:
        dict: Resultado da migração
    """
    try:
        prata_id = pub_prata["_id"]
        bronze_id_atual = pub_prata.get("publicacao_bronze_id")

        # Se já é válido, pular
        if is_valid_objectid(bronze_id_atual):
            return {
                "success": True,
                "skipped": True,
                "prata_id": str(prata_id),
                "reason": "já válido"
            }

        # Tentar converter para int (cod_publicacao)
        try:
            cod_publicacao = int(bronze_id_atual)
        except (ValueError, TypeError):
            return {
                "success": False,
                "prata_id": str(prata_id),
                "error": f"Não foi possível converter {bronze_id_atual} para int"
            }

        # Buscar documento bronze pelo cod_publicacao
        pub_bronze = db.publicacoes_bronze.find_one(
            {"cod_publicacao": cod_publicacao}
        )

        if not pub_bronze:
            return {
                "success": False,
                "prata_id": str(prata_id),
                "cod_publicacao": cod_publicacao,
                "error": "Documento bronze não encontrado"
            }

        # Atualizar publicacao_bronze_id com o _id correto
        bronze_id_correto = str(pub_bronze["_id"])

        result = db.publicacoes_prata.update_one(
            {"_id": prata_id},
            {
                "$set": {
                    "publicacao_bronze_id": bronze_id_correto,
                    "migrado_em": datetime.now(),
                    "bronze_id_anterior": bronze_id_atual
                }
            }
        )

        return {
            "success": True,
            "prata_id": str(prata_id),
            "cod_publicacao": cod_publicacao,
            "bronze_id_anterior": bronze_id_atual,
            "bronze_id_novo": bronze_id_correto,
            "updated": result.modified_count
        }

    except Exception as e:
        return {
            "success": False,
            "prata_id": str(pub_prata.get("_id", "unknown")),
            "error": str(e)
        }

def main():
    """Executa a migração"""
    print("=" * 80)
    print("🔧 MIGRAÇÃO: Correção de publicacao_bronze_id")
    print("=" * 80)
    print()

    # Conectar ao banco
    db = conectar_mongodb()

    # Contar registros prata
    total_prata = db.publicacoes_prata.count_documents({})
    print(f"📊 Total de publicações prata: {total_prata}")
    print()

    # Buscar publicações prata com IDs inválidos
    print("🔍 Buscando publicações com publicacao_bronze_id inválido...")
    publicacoes_prata = list(db.publicacoes_prata.find({}))

    invalidos = [
        pub for pub in publicacoes_prata
        if not is_valid_objectid(pub.get("publicacao_bronze_id"))
    ]

    total_invalidos = len(invalidos)
    print(f"❌ Encontrados {total_invalidos} registros inválidos")
    print()

    if total_invalidos == 0:
        print("✅ Nenhuma migração necessária!")
        return

    # Confirmar migração
    print("⚠️  Esta operação irá:")
    print(f"   - Atualizar {total_invalidos} registros na coleção publicacoes_prata")
    print("   - Adicionar campos: migrado_em, bronze_id_anterior")
    print()

    resposta = input("Deseja continuar? (s/N): ").strip().lower()
    if resposta != 's':
        print("❌ Migração cancelada pelo usuário")
        return

    print()
    print("🚀 Iniciando migração...")
    print()

    # Migrar cada publicação
    resultados = {
        "sucesso": 0,
        "pulados": 0,
        "erros": 0,
        "detalhes_erros": []
    }

    for i, pub_prata in enumerate(invalidos, 1):
        resultado = migrar_publicacao(db, pub_prata)

        if resultado.get("success"):
            if resultado.get("skipped"):
                resultados["pulados"] += 1
                print(f"[{i}/{total_invalidos}] ⏭️  Pulado: {resultado['prata_id']} - {resultado.get('reason')}")
            else:
                resultados["sucesso"] += 1
                print(f"[{i}/{total_invalidos}] ✅ Migrado: {resultado['prata_id']}")
                print(f"             Antes: {resultado['bronze_id_anterior']}")
                print(f"             Depois: {resultado['bronze_id_novo']}")
        else:
            resultados["erros"] += 1
            resultados["detalhes_erros"].append(resultado)
            print(f"[{i}/{total_invalidos}] ❌ Erro: {resultado['prata_id']} - {resultado.get('error')}")

        # Progresso a cada 10 registros
        if i % 10 == 0:
            print(f"\n📈 Progresso: {i}/{total_invalidos} ({i*100//total_invalidos}%)\n")

    # Relatório final
    print()
    print("=" * 80)
    print("📊 RELATÓRIO FINAL")
    print("=" * 80)
    print(f"✅ Sucesso: {resultados['sucesso']}")
    print(f"⏭️  Pulados: {resultados['pulados']}")
    print(f"❌ Erros: {resultados['erros']}")
    print()

    if resultados["erros"] > 0:
        print("⚠️  ERROS ENCONTRADOS:")
        for erro in resultados["detalhes_erros"]:
            print(f"   - {erro.get('prata_id')}: {erro.get('error')}")
        print()

    # Validação final
    print("🔍 Validando migração...")
    ainda_invalidos = [
        pub for pub in db.publicacoes_prata.find({})
        if not is_valid_objectid(pub.get("publicacao_bronze_id"))
    ]

    if len(ainda_invalidos) == 0:
        print("✅ Todos os registros foram corrigidos!")
    else:
        print(f"⚠️  Ainda existem {len(ainda_invalidos)} registros inválidos")

    print()
    print("=" * 80)
    print("🏁 Migração concluída!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Migração interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
