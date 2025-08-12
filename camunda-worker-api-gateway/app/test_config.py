#!/usr/bin/env python3
"""
Script para testar qual configuração está sendo usada pela aplicação
"""

import os
import sys

# Adiciona o diretório app ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carrega as variáveis do .env.local
from dotenv import load_dotenv
env_file = os.path.join(os.path.dirname(__file__), '..', '.env.local')
load_dotenv(env_file)

print(f"📁 Arquivo .env carregado: {env_file}")
print(f"   Existe: {os.path.exists(env_file)}")

# Importa configurações
from core.config import get_settings

settings = get_settings()

print("\n🔧 Configurações atuais:")
print(f"   ENVIRONMENT: {settings.ENVIRONMENT}")
print(f"   EXTERNAL_SERVICES_MODE: {os.getenv('EXTERNAL_SERVICES_MODE', 'NOT SET')}")
print(f"   MONGODB_URI (env): {os.getenv('MONGODB_URI', 'NOT SET')[:50]}...")
print(f"   MONGODB_CONNECTION_STRING (settings): {settings.MONGODB_CONNECTION_STRING[:50]}...")
print(f"   MONGODB_DATABASE: {settings.MONGODB_DATABASE}")

# Testa conexão com o MongoDB configurado
from pymongo import MongoClient

print("\n🔗 Testando conexão com MongoDB configurado...")
try:
    client = MongoClient(settings.MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    
    # Verifica o host
    db_host = client.address
    print(f"✅ Conectado com sucesso!")
    print(f"   Host: {db_host}")
    
    # Lista bancos de dados
    dbs = client.list_database_names()
    print(f"   Bancos disponíveis: {dbs[:5]}...")  # Mostra apenas primeiros 5
    
    # Verifica o banco configurado
    db = client[settings.MONGODB_DATABASE]
    collections = db.list_collection_names()
    print(f"   Coleções em '{settings.MONGODB_DATABASE}': {collections}")
    
    # Conta documentos
    if 'execucoes' in collections:
        count = db.execucoes.count_documents({})
        print(f"   Documentos em 'execucoes': {count}")
    
    client.close()
    
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")

print("\n💡 Diagnóstico:")
if "mongodb+srv" in settings.MONGODB_CONNECTION_STRING:
    print("   ✅ Configurado para usar MongoDB Atlas")
elif "localhost" in settings.MONGODB_CONNECTION_STRING or "mongodb:" in settings.MONGODB_CONNECTION_STRING:
    print("   ⚠️  Configurado para usar MongoDB local/container")
else:
    print("   ❓ Configuração não identificada")

if os.getenv('EXTERNAL_SERVICES_MODE') == 'true':
    print("   ✅ EXTERNAL_SERVICES_MODE está true (deve usar Atlas)")
else:
    print("   ⚠️  EXTERNAL_SERVICES_MODE não está true (vai usar local)")