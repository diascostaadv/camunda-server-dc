#!/usr/bin/env python3
"""Teste rápido para verificar se a mudança está funcionando"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.intimation_service import IntimationService

print("="*70)
print("TESTE RÁPIDO - VERIFICAR SE BUSCA TODAS AS PUBLICAÇÕES")
print("="*70)

service = IntimationService(usuario='100049', senha='DcDpW@24')

# Testar com período de 1 dia (28/10/2025 - sabemos que tem 146 publicações)
print("\n🧪 Testando período 2025-10-28 (1 dia) com grupo 2...")
pubs = service.get_publicacoes_periodo_safe('2025-10-28', '2025-10-28', cod_grupo=2)
print(f"📊 Resultado: {len(pubs)} publicações")

if len(pubs) > 0:
    print("\n✅ SUCESSO! Encontrou publicações!")
    print(f"\nPrimeira publicação:")
    pub = pubs[0]
    print(f"  - Código: {pub.cod_publicacao}")
    print(f"  - Data: {pub.data_publicacao}")
    print(f"  - UF: {pub.uf_publicacao}")
    print(f"  - Processo: {pub.numero_processo}")
    print(f"  - Órgão: {pub.orgao_descricao}")
    print(f"  - Exportada: {pub.publicacao_exportada}")
else:
    print("\n❌ FALHA! Ainda retornando 0 publicações")
    print("\nPossíveis causas:")
    print("1. Código não foi atualizado (verificar se intimation_service.py mudou)")
    print("2. Servidor API Gateway não foi reiniciado")
    print("3. Grupo 2 não tem dados")

    print("\n🔄 Tentando com grupo 5...")
    pubs = service.get_publicacoes_periodo_safe('2025-10-28', '2025-10-28', cod_grupo=5)
    print(f"📊 Grupo 5: {len(pubs)} publicações")

    print("\n🔄 Tentando com grupo 0...")
    pubs = service.get_publicacoes_periodo_safe('2025-10-28', '2025-10-28', cod_grupo=0)
    print(f"📊 Grupo 0: {len(pubs)} publicações")

print("\n" + "="*70)
