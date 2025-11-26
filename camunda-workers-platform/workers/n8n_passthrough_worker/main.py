#!/usr/bin/env python3
"""
N8n Passthrough Worker - Versão Standalone com Auto-Discovery

Worker minimalista que descobre TODOS os topics do Camunda automaticamente
e repassa tasks para n8n via HTTP POST.
Sem dependências externas (pasta common/), pronto para deploy standalone.
"""

import os
import time
import logging
import requests
from typing import Dict, Any, List
from camunda.external_task.external_task_worker import ExternalTaskWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class N8nPassthroughWorker:
    """Worker standalone que descobre e repassa ALL topics para n8n"""

    def __init__(self):
        # Camunda config
        self.camunda_url = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
        self.camunda_username = os.getenv("CAMUNDA_USERNAME", "demo")
        self.camunda_password = os.getenv("CAMUNDA_PASSWORD", "demo")
        
        # n8n webhook (único ponto de entrada)
        self.n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/camunda-tasks")

        # Auto-discovery: busca TODOS os topics do Camunda
        self.topics = self._discover_all_topics()
        
        if not self.topics:
            logger.warning("⚠️ Nenhum topic descoberto! Usando fallback...")
            self.topics = [
                "buscar_publicacoes",
                "tratar_publicacao",
                "nova_publicacao",
                "classificar_publicacao",
            ]
        
        # Camunda worker
        config = {
            "maxTasks": int(os.getenv("MAX_TASKS", "300")),
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
        
        logger.info("🚀 N8n Passthrough Worker (AUTO-DISCOVERY)")
        logger.info(f"📡 Camunda URL: {self.camunda_url}")
        logger.info(f"🔗 n8n Webhook URL: {self.n8n_webhook_url}")
        logger.info(f"📋 Topics descobertos: {len(self.topics)}")
        for topic in self.topics:
            logger.info(f"   ✓ {topic}")

    def _discover_all_topics(self) -> List[str]:
        """Descobre TODOS os topics registrados no Camunda via API"""
        try:
            logger.info("🔍 Descobrindo topics do Camunda...")
            
            # API: GET /external-task (busca todas as tasks pendentes)
            url = f"{self.camunda_url}/external-task"
            response = requests.get(
                url,
                auth=(self.camunda_username, self.camunda_password),
                timeout=10
            )
            response.raise_for_status()
            
            tasks = response.json()
            
            # Extrair topics únicos
            topics = list(set(task.get("topicName") for task in tasks if task.get("topicName")))
            
            if topics:
                logger.info(f"✅ {len(topics)} topics encontrados via external-task")
                return topics
            
            # Fallback: buscar via process definitions
            logger.info("🔍 Tentando descobrir via process definitions...")
            url = f"{self.camunda_url}/process-definition"
            response = requests.get(
                url,
                auth=(self.camunda_username, self.camunda_password),
                timeout=10
            )
            response.raise_for_status()
            
            definitions = response.json()
            logger.info(f"📦 {len(definitions)} process definitions encontradas")
            
            # Por ora, retorna vazio se não houver tasks pendentes
            # (topics são descobertos dinamicamente quando tasks aparecem)
            return []
            
        except requests.RequestException as e:
            logger.error(f"❌ Erro ao descobrir topics: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"💥 Erro inesperado: {str(e)}")
            return []

    def _passthrough_to_n8n(self, task) -> Dict[str, Any]:
        """Repassa task para n8n"""
        task_id = task.get_task_id()
        topic = task.get_topic_name()
        business_key = task.get_business_key()
        variables = task.get_variables()
        
        logger.info(f"📤 Task {task_id} | Topic: {topic}")
        logger.info(f"🔗 Enviando para: {self.n8n_webhook_url}")
        
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
            
            # n8n deve retornar {"variables": {...}}
            # Se não tiver, retorna vazio mas completa a task
            output_variables = result.get("variables", {})

            logger.info(f"[DEBUG] result recebido do n8n: {result}")
            logger.info(f"[DEBUG] tipo do result: {type(result)}")
            
            if not output_variables:
                logger.warning(f"⚠️ n8n não retornou 'variables' no response. Completando task sem variáveis.")
            
            return task.complete(global_variables={}, local_variables=output_variables)
            
        except requests.Timeout:
            logger.error(f"⏱️ n8n timeout para topic: {topic}")
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
        """Inicia worker com descoberta dinâmica de topics"""
        logger.info("🎯 Starting worker...")
        
        # Subscreve a TODOS os topics COM A MESMA FUNÇÃO
        # A biblioteca permite passar lista de topics OU chamar subscribe() múltiplas vezes
        logger.info(f"� Subscrevendo a {len(self.topics)} topics: {', '.join(self.topics)}")
        
        # Tenta subscrever passando lista (se suportado)
        try:
            self.worker.subscribe(self.topics, self._passthrough_to_n8n)
            logger.info(f"✅ Subscribed to all topics via list")
        except (TypeError, ValueError) as e:
            # Fallback: subscreve um por um
            logger.warning(f"⚠️ List subscription failed ({e}), trying individual subscriptions...")
            for topic in self.topics:
                self.worker.subscribe(topic, self._passthrough_to_n8n)
                logger.info(f"✅ Subscribed: {topic}")
        
        logger.info(f"🔄 Running (long-polling)...")
        
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
