#!/usr/bin/env python3
"""
Script para testar e debugar a API SOAP
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.intimation_service import IntimationService

def test_soap_calls():
    """Test different SOAP calls to understand the issue"""
    
    # Initialize service
    service = IntimationService()
    
    print("\n1️⃣ Testing connection...")
    if service.test_connection():
        print("✅ Connection OK")
    else:
        print("❌ Connection failed")
        return
    
    print("\n2️⃣ Testing get_publicacoes_nao_exportadas (cod_grupo=0)...")
    pubs1 = service.get_publicacoes_nao_exportadas(cod_grupo=0)
    print(f"   Found: {len(pubs1)} publications")
    
    print("\n3️⃣ Testing get_publicacoes_nao_exportadas (cod_grupo=5)...")
    pubs2 = service.get_publicacoes_nao_exportadas(cod_grupo=5)
    print(f"   Found: {len(pubs2)} publications")
    
    print("\n4️⃣ Testing get_publicacoes_periodo_safe...")
    pubs3 = service.get_publicacoes_periodo_safe(
        data_inicial="2025-05-01",
        data_final="2025-05-01",
        cod_grupo=0,
        timeout_override=120
    )
    print(f"   Found: {len(pubs3)} publications")
    
    print("\n5️⃣ Testing get_publicacoes_periodo_safe with cod_grupo=5...")
    pubs4 = service.get_publicacoes_periodo_safe(
        data_inicial="2025-05-01",
        data_final="2025-05-01",
        cod_grupo=5,
        timeout_override=120
    )
    print(f"   Found: {len(pubs4)} publications")
    
    # Show sample publication if any found
    all_pubs = pubs1 + pubs2 + pubs3 + pubs4
    if all_pubs:
        print("\n📄 Sample publication:")
        pub = all_pubs[0]
        print(f"   cod_publicacao: {pub.cod_publicacao}")
        print(f"   numero_processo: {pub.numero_processo}")
        print(f"   data_publicacao: {pub.data_publicacao}")
        print(f"   cod_grupo: {pub.cod_grupo}")
    
    print("\n✅ Test complete!")
    print(f"   Total publications found across all tests: {len(all_pubs)}")

if __name__ == "__main__":
    test_soap_calls()