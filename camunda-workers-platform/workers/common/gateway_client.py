"""
Gateway Client for Workers
HTTP and RabbitMQ client for communicating with Worker API Gateway
"""

import json
import logging
import os
from typing import Dict, Any, Optional, Union
import requests
import pika
from dataclasses import dataclass

from .utils import get_timestamp


logger = logging.getLogger(__name__)


@dataclass
class TaskStatus:
    """Task status response from Gateway"""
    task_id: str
    status: str
    substatus: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamps: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class GatewayClient:
    """Client for communicating with Worker API Gateway"""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        
        # Gateway configuration
        self.gateway_url = os.getenv('GATEWAY_URL', 'http://camunda-worker-api-gateway-gateway-1:8000')
        self.communication_mode = os.getenv('GATEWAY_COMMUNICATION_MODE', 'http')  # 'http' or 'rabbitmq'
        
        # HTTP configuration
        self.http_timeout = int(os.getenv('GATEWAY_HTTP_TIMEOUT', '30'))
        
        # RabbitMQ configuration
        self.rabbitmq_url = os.getenv('RABBITMQ_URL')
        self.rabbitmq_exchange = os.getenv('RABBITMQ_EXCHANGE', 'worker_gateway')
        
        # RabbitMQ connection (lazy initialization)
        self._rabbitmq_connection = None
        self._rabbitmq_channel = None
        
        logger.info(f"Initialized Gateway Client for worker {worker_id} using {self.communication_mode} mode")
    
    def submit_task(self, task_id: str, topic: str, variables: Dict[str, Any]) -> bool:
        """
        Submit task to Gateway for processing
        
        Args:
            task_id: Camunda task ID
            topic: Task topic
            variables: Task variables
            
        Returns:
            True if submitted successfully
        """
        task_data = {
            "task_id": task_id,
            "worker_id": self.worker_id,
            "topic": topic,
            "variables": variables
        }
        
        try:
            if self.communication_mode == 'rabbitmq':
                return self._submit_via_rabbitmq(task_data)
            else:
                return self._submit_via_http(task_data)
                
        except Exception as e:
            logger.error(f"Failed to submit task {task_id}: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get task status from Gateway
        
        Args:
            task_id: Camunda task ID
            
        Returns:
            Task status or None if not found
        """
        try:
            # Status checking is always via HTTP for simplicity
            response = requests.get(
                f"{self.gateway_url}/tasks/{task_id}/status",
                timeout=self.http_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return TaskStatus(
                    task_id=data['task_id'],
                    status=data['status'],
                    substatus=data.get('substatus'),
                    result=data.get('result'),
                    error_message=data.get('error_message'),
                    timestamps=data.get('timestamps'),
                    metadata=data.get('metadata')
                )
            elif response.status_code == 404:
                return None  # Task not found
            else:
                logger.error(f"Failed to get task status {task_id}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get task status {task_id}: {e}")
            return None
    
    def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task
        
        Args:
            task_id: Camunda task ID
            
        Returns:
            True if retry submitted successfully
        """
        try:
            response = requests.post(
                f"{self.gateway_url}/tasks/{task_id}/retry",
                timeout=self.http_timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully submitted retry for task {task_id}")
                return True
            else:
                logger.error(f"Failed to retry task {task_id}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return False
    
    def _submit_via_http(self, task_data: Dict[str, Any]) -> bool:
        """Submit task via HTTP"""
        try:
            response = requests.post(
                f"{self.gateway_url}/tasks/submit",
                json=task_data,
                timeout=self.http_timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully submitted task {task_data['task_id']} via HTTP")
                return True
            else:
                logger.error(f"Failed to submit task via HTTP: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"HTTP submission failed: {e}")
            return False
    
    def _submit_via_rabbitmq(self, task_data: Dict[str, Any]) -> bool:
        """Submit task via RabbitMQ"""
        if not self.rabbitmq_url:
            logger.error("RabbitMQ URL not configured")
            return False
        
        try:
            # Ensure connection
            if not self._ensure_rabbitmq_connection():
                return False
            
            # Publish message
            routing_key = f"task.submit.{task_data['topic']}"
            
            self._rabbitmq_channel.basic_publish(
                exchange=self.rabbitmq_exchange,
                routing_key=routing_key,
                body=json.dumps(task_data),
                properties=pika.BasicProperties(
                    headers={
                        'task_id': task_data['task_id'],
                        'worker_id': task_data['worker_id'],
                        'topic': task_data['topic'],
                        'timestamp': get_timestamp()
                    },
                    delivery_mode=2  # Persistent message
                )
            )
            
            logger.info(f"Successfully submitted task {task_data['task_id']} via RabbitMQ")
            return True
            
        except Exception as e:
            logger.error(f"RabbitMQ submission failed: {e}")
            return False
    
    def _ensure_rabbitmq_connection(self) -> bool:
        """Ensure RabbitMQ connection is established"""
        try:
            if self._rabbitmq_connection and not self._rabbitmq_connection.is_closed:
                return True
            
            # Create new connection
            connection_params = pika.URLParameters(self.rabbitmq_url)
            self._rabbitmq_connection = pika.BlockingConnection(connection_params)
            self._rabbitmq_channel = self._rabbitmq_connection.channel()
            
            # Declare exchange
            self._rabbitmq_channel.exchange_declare(
                exchange=self.rabbitmq_exchange,
                exchange_type='topic',
                durable=True
            )
            
            logger.info("RabbitMQ connection established")
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish RabbitMQ connection: {e}")
            return False
    
    def close(self):
        """Close RabbitMQ connection if open"""
        try:
            if self._rabbitmq_connection and not self._rabbitmq_connection.is_closed:
                self._rabbitmq_connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Gateway connectivity"""
        try:
            response = requests.get(
                f"{self.gateway_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    "gateway_status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "gateway_info": response.json()
                }
            else:
                return {
                    "gateway_status": "unhealthy",
                    "http_status": response.status_code
                }
                
        except Exception as e:
            return {
                "gateway_status": "unreachable",
                "error": str(e)
            }