#!/usr/bin/env python3
"""
Script para deploy automático de arquivos BPMN no Camunda Platform
"""

import os
import requests
import glob
from pathlib import Path
import time
import sys


def deploy_bpmn_files():
    """Deploy BPMN files to Camunda Platform"""

    # Configuração
    CAMUNDA_BASE_URL = os.getenv("CAMUNDA_BASE_URL", "http://localhost:8080")
    CAMUNDA_USERNAME = os.getenv("CAMUNDA_USERNAME", "admin")
    CAMUNDA_PASSWORD = os.getenv("CAMUNDA_PASSWORD", "admin")

    # Diretório dos BPMNs
    BPMN_DIR = os.getenv("BPMN_DIR", "bpmn")

    print("🚀 Starting BPMN deployment...")
    print(f"📁 BPMN Directory: {BPMN_DIR}")
    print(f"🌐 Camunda URL: {CAMUNDA_BASE_URL}")

    # Aguardar Camunda estar disponível
    wait_for_camunda(CAMUNDA_BASE_URL, CAMUNDA_USERNAME, CAMUNDA_PASSWORD)

    # Encontrar arquivos BPMN, DMN e FORM
    bpmn_files = glob.glob(f"{BPMN_DIR}/*.bpmn")
    dmn_files = glob.glob(f"{BPMN_DIR}/*.dmn")
    form_files = glob.glob(f"{BPMN_DIR}/*.form")

    all_files = bpmn_files + dmn_files + form_files

    if not all_files:
        print("❌ No BPMN/DMN/FORM files found in bpmn directory")
        return

    print(f"📋 Found {len(all_files)} files:")
    print(f"  - {len(bpmn_files)} BPMN files")
    print(f"  - {len(dmn_files)} DMN files")
    print(f"  - {len(form_files)} FORM files")

    for file in all_files:
        print(f"  - {file}")

    # Deploy cada arquivo
    success_count = 0
    for bpmn_file in all_files:
        try:
            deploy_single_bpmn(
                bpmn_file, CAMUNDA_BASE_URL, CAMUNDA_USERNAME, CAMUNDA_PASSWORD
            )
            success_count += 1
        except Exception as e:
            print(f"❌ Error deploying {bpmn_file}: {e}")

    print(
        f"✅ Deployment completed! {success_count}/{len(all_files)} files deployed successfully"
    )


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
        except Exception as e:
            if attempt < max_attempts - 1:
                print(
                    f"⏳ Attempt {attempt + 1}/{max_attempts} - Waiting for Camunda... ({e})"
                )
                time.sleep(10)
            else:
                print(f"❌ Failed to connect to Camunda: {e}")

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
    try:
        deploy_bpmn_files()
    except Exception as e:
        print(f"💥 Deployment failed: {e}")
        sys.exit(1)
