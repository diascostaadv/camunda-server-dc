#!/usr/bin/env python3
# scripts/deploy_bpmns.py

import os
import requests
import glob
from pathlib import Path
import time


def deploy_bpmn_files():
    """Deploy BPMN files to Camunda Platform"""

    # Configuração
    CAMUNDA_BASE_URL = "http://localhost:8080"
    CAMUNDA_USERNAME = "admin"
    CAMUNDA_PASSWORD = "admin"

    # Diretório dos BPMNs
    BPMN_DIR = "resources"

    print("🚀 Starting BPMN deployment...")

    # Aguardar Camunda estar disponível
    wait_for_camunda(CAMUNDA_BASE_URL, CAMUNDA_USERNAME, CAMUNDA_PASSWORD)

    # Encontrar arquivos BPMN
    bpmn_files = glob.glob(f"{BPMN_DIR}/*.bpmn")

    if not bpmn_files:
        print("❌ No BPMN files found in resources directory")
        return

    print(f"📋 Found {len(bpmn_files)} BPMN files:")
    for file in bpmn_files:
        print(f"  - {file}")

    # Deploy cada BPMN
    for bpmn_file in bpmn_files:
        try:
            deploy_single_bpmn(
                bpmn_file, CAMUNDA_BASE_URL, CAMUNDA_USERNAME, CAMUNDA_PASSWORD
            )
        except Exception as e:
            print(f"❌ Error deploying {bpmn_file}: {e}")

    print("✅ BPMN deployment completed!")


def wait_for_camunda(base_url, username, password, max_attempts=30):
    """Wait for Camunda to be available"""
    print("⏳ Waiting for Camunda to be available...")

    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"{base_url}/engine-rest/version", auth=(username, password), timeout=5
            )
            if response.status_code == 200:
                print("✅ Camunda is available!")
                return
        except:
            pass

        print(f"⏳ Attempt {attempt + 1}/{max_attempts} - Waiting for Camunda...")
        time.sleep(10)

    raise Exception("❌ Camunda not available after maximum attempts")


def deploy_single_bpmn(bpmn_file, base_url, username, password):
    """Deploy a single BPMN file"""

    with open(bpmn_file, "rb") as f:
        files = {
            "deployment-name": f"deployment-{Path(bpmn_file).stem}",
            "deployment-source": "python-script",
            "file": (Path(bpmn_file).name, f, "application/xml"),
        }

        response = requests.post(
            f"{base_url}/engine-rest/deployment/create",
            files=files,
            auth=(username, password),
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Deployed {Path(bpmn_file).name} - ID: {result.get('id')}")
        else:
            print(f"❌ Failed to deploy {Path(bpmn_file).name}: {response.text}")


if __name__ == "__main__":
    deploy_bpmn_files()
