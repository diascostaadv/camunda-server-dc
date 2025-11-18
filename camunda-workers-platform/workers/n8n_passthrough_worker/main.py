#!/usr/bin/env python3
"""
N8n Passthrough Worker - Versão Standalone

Worker minimalista que apenas repassa tasks do Camunda para n8n via HTTP POST.
Sem dependências externas (pasta common/), pronto para deploy standalone.
"""

import os
import logging
import requests
from typing import Dict, Any
from camunda.external_task.external_task_worker import ExternalTaskWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class N8nPassthroughWorker:
    """Worker standalone que repassa tasks para n8n"""

    def __init__(self):
        # Camunda config
        self.camunda_url = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
        self.camunda_username = os.getenv("CAMUNDA_USERNAME", "demo")
        self.camunda_password = os.getenv("CAMUNDA_PASSWORD", "demo")
        
        # n8n webhook (único ponto de entrada)
        self.n8n_webhook_url = os.getenv(
            "N8N_WEBHOOK_URL",
            "http://localhost:5678/webhook/camunda-tasks"
        )
        
        # Topics
        self.topics = [
            "buscar_publicacoes",
            "tratar_publicacao",
            "nova_publicacao",
            "classificar_publicacao",
        ]
        
        # Camunda worker
        config = {
            "maxTasks": int(os.getenv("MAX_TASKS", "5")),
            "lockDuration": 60000,
            "asyncResponseTimeout": 30000,
            "retries": 3,
            "retryTimeout": 5000,
            "sleepSeconds": 10,
            "auth_basic": {
                "username": self.camunda_username,
                "password": self.camunda_password
            }
        }
        
        self.worker = ExternalTaskWorker(
            worker_id="n8n-passthrough-worker",
            base_url=self.camunda_url,
            config=config
        )
        
        logger.info("🚀 N8n Passthrough Worker (standalone)")
        logger.info(f"📡 Camunda: {self.camunda_url}")
        logger.info(f"📡 n8n: {self.n8n_webhook_url}")
        logger.info(f"📋 Topics: {self.topics}")

    def _passthrough_to_n8n(self, task) -> Dict[str, Any]:
        """Repassa task para n8n"""
        task_id = task.get_task_id()
        topic = task.get_topic_name()
        business_key = task.get_business_key()
        variables = task.get_variables()
        
        logger.info(f"📤 Task {task_id} | Topic: {topic}")
        
        try:
            payload = {
                "topic": topic,
                "task_id": task_id,
                "business_key": business_key,
                "variables": variables,
            }
            
            response = requests.post(
                self.n8n_webhook_url,
                json=payload,
                timeout=180,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"✅ n8n OK: {response.status_code}")
            
            output_variables = result.get("variables", {})
            return task.complete(global_variables={}, local_variables=output_variables)
            
        except requests.Timeout:
            logger.error(f"⏱️ n8n timeout")
            return task.failure(
                error_message=f"n8n timeout: {topic}",
                error_details="N8N_TIMEOUT",
                retry_timeout=60000,
                max_retries=3
            )
            
        except requests.RequestException as e:
            logger.error(f"❌ n8n error: {str(e)}")
            return task.failure(
                error_message=f"n8n error: {str(e)}",
                error_details="N8N_ERROR",
                retry_timeout=30000,
                max_retries=3
            )
        
        except Exception as e:
            logger.error(f"💥 Worker error: {str(e)}")
            return task.failure(
                error_message=f"Internal error: {str(e)}",
                error_details="WORKER_ERROR",
                retry_timeout=30000,
                max_retries=3
            )

    def start(self):
        """Inicia worker"""
        logger.info("🎯 Starting worker...")
        
        for topic in self.topics:
            self.worker.subscribe(topic, self._passthrough_to_n8n)
            logger.info(f"✅ Subscribed: {topic}")
        
        logger.info("🔄 Running (long-polling)...")
        
        try:
            self.worker.start()
        except KeyboardInterrupt:
            logger.info("⚠️ Interrupted")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            raise


def main():
    worker = N8nPassthroughWorker()
    worker.start()


if __name__ == "__main__":
    main()
