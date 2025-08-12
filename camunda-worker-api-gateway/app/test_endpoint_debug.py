#!/usr/bin/env python3
"""
Script to test the endpoint and see what's happening with the request
"""

import requests
import json

# Test the endpoint with various configurations
def test_endpoint():
    url = "http://localhost:8000/buscar-publicacoes/processar-task-v2"
    
    # Test 1: With dates (should use Branch 2)
    print("\n1️⃣ Testing with dates...")
    payload1 = {
        "task_id": "test-123",
        "process_instance_id": "proc-456",
        "variables": {
            "cod_grupo": 0,
            "data_inicial": "2025-05-01",
            "data_final": "2025-05-01",
            "limite_publicacoes": 50,
            "apenas_nao_exportadas": True  # Should be overridden to False
        },
        "worker_id": "test-worker",
        "topic_name": "BuscarPublicacoes"
    }
    
    try:
        resp1 = requests.post(url, json=payload1)
        print(f"Status: {resp1.status_code}")
        print(f"Response: {json.dumps(resp1.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Without dates, only apenas_nao_exportadas
    print("\n2️⃣ Testing without dates (apenas_nao_exportadas=True)...")
    payload2 = {
        "task_id": "test-456",
        "process_instance_id": "proc-789",
        "variables": {
            "cod_grupo": 0,
            "limite_publicacoes": 50,
            "apenas_nao_exportadas": True
        },
        "worker_id": "test-worker",
        "topic_name": "BuscarPublicacoes"
    }
    
    try:
        resp2 = requests.post(url, json=payload2)
        print(f"Status: {resp2.status_code}")
        print(f"Response: {json.dumps(resp2.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Without any search criteria
    print("\n3️⃣ Testing without any criteria...")
    payload3 = {
        "task_id": "test-789",
        "process_instance_id": "proc-012",
        "variables": {
            "cod_grupo": 0,
            "limite_publicacoes": 50
        },
        "worker_id": "test-worker",
        "topic_name": "BuscarPublicacoes"
    }
    
    try:
        resp3 = requests.post(url, json=payload3)
        print(f"Status: {resp3.status_code}")
        print(f"Response: {json.dumps(resp3.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoint()