"""
Base Worker Class for Camunda External Tasks
Provides common functionality for all workers with Worker API Gateway integration
"""

import logging
import os
import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from camunda.external_task.external_task_worker import ExternalTaskWorker

from .gateway_client import GatewayClient, TaskStatus


# Prometheus Metrics
TASK_COUNTER = Counter('camunda_tasks_total', 'Total number of tasks processed', ['topic', 'status'])
TASK_DURATION = Histogram('camunda_task_duration_seconds', 'Time spent processing tasks', ['topic'])
ACTIVE_TASKS = Gauge('camunda_active_tasks', 'Number of currently active tasks', ['topic'])
GATEWAY_TASKS = Counter('gateway_tasks_total', 'Total number of tasks sent to gateway', ['topic', 'status'])


class BaseWorker:
    """Base class for all Camunda external task workers"""
    
    def __init__(self, worker_id: str, base_url: str = None, auth: tuple = None):
        """
        Initialize the base worker
        
        Args:
            worker_id: Unique identifier for this worker instance
            base_url: Camunda engine REST API URL
            auth: Tuple of (username, password) for basic auth
        """
        self.worker_id = worker_id
        # Default baseado no modo: localhost para embedded, camunda para separated
        default_url = 'http://localhost:8080/camunda/engine-rest' if os.getenv('WORKERS_MODE', 'separated') == 'embedded' else 'http://camunda:8080/camunda/engine-rest'
        self.base_url = base_url or os.getenv('CAMUNDA_URL', default_url)
        self.auth = auth or self._get_auth_from_env()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize Gateway Client
        self.gateway_enabled = os.getenv('GATEWAY_ENABLED', 'false').lower() == 'true'
        self.gateway_client = GatewayClient(worker_id) if self.gateway_enabled else None
        
        if self.gateway_enabled:
            self.logger.info(f"Worker API Gateway integration enabled for {worker_id}")
        else:
            self.logger.info(f"Direct Camunda processing mode for {worker_id}")
        
        # Initialize Camunda worker
        self._init_camunda_worker()
        
        # Start Prometheus metrics server
        self._start_metrics_server()
        
    def _get_auth_from_env(self) -> Optional[tuple]:
        """Get authentication from environment variables"""
        username = os.getenv('CAMUNDA_USERNAME')
        password = os.getenv('CAMUNDA_PASSWORD')
        return (username, password) if username and password else None
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(f'CamundaWorker-{self.worker_id}')
    
    def _init_camunda_worker(self):
        """Initialize the Camunda external task worker"""
        from .config import WorkerConfig
        
        config = {
            "maxTasks": WorkerConfig.MAX_TASKS,
            "lockDuration": WorkerConfig.LOCK_DURATION,
            "asyncResponseTimeout": WorkerConfig.ASYNC_RESPONSE_TIMEOUT,
            "retries": WorkerConfig.RETRIES,
            "retryTimeout": WorkerConfig.RETRY_TIMEOUT,
            "sleepSeconds": WorkerConfig.SLEEP_SECONDS
        }
        
        self.camunda_worker = ExternalTaskWorker(
            worker_id=self.worker_id,
            base_url=self.base_url,
            config=config
        )
        
        self.logger.info(f"Initialized Camunda worker {self.worker_id} connecting to {self.base_url}")
    
    def _start_metrics_server(self):
        """Start Prometheus metrics HTTP server"""
        try:
            metrics_port = int(os.getenv('METRICS_PORT', '8000'))
            start_http_server(metrics_port)
            self.logger.info(f"Started Prometheus metrics server on port {metrics_port}")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
    
    def subscribe(self, topic: str, handler_func):
        """
        Subscribe to a topic with monitoring and error handling
        
        Args:
            topic: The topic name to subscribe to
            handler_func: Function to handle the task (only used in direct mode)
        """
        def wrapped_handler(task):
            """Wrapper function with Gateway integration or direct processing"""
            start_time = time.time()
            task_id = task.get_task_id()
            
            # Update active tasks metric
            ACTIVE_TASKS.labels(topic=topic).inc()
            
            try:
                if self.gateway_enabled:
                    # Gateway mode: Check task status and handle accordingly
                    return self._handle_task_via_gateway(task, topic)
                else:
                    # Direct mode: Process task immediately using handler_func
                    return self._handle_task_direct(task, topic, handler_func)
                    
            finally:
                # Update metrics
                duration = time.time() - start_time
                TASK_DURATION.labels(topic=topic).observe(duration)
                ACTIVE_TASKS.labels(topic=topic).dec()
        
        # Subscribe to the topic
        self.camunda_worker.subscribe(topic, wrapped_handler)
        self.logger.info(f"Subscribed to topic: {topic}")
    
    def subscribe_multiple(self, topic_handlers: Dict[str, Any]):
        """
        Subscribe to multiple topics with their respective handlers
        
        Args:
            topic_handlers: Dictionary mapping topic names to handler functions
                          Format: {"topic_name": handler_function}
        """
        self.logger.info(f"Subscribing to {len(topic_handlers)} topics: {list(topic_handlers.keys())}")
        
        for topic, handler_func in topic_handlers.items():
            self.subscribe(topic, handler_func)
        
        self.logger.info("✅ Multi-topic subscription completed")
    
    def _handle_task_via_gateway(self, task, topic: str):
        """
        Handle task via Worker API Gateway
        
        Args:
            task: Camunda task
            topic: Task topic
            
        Returns:
            Task completion result or None (empty return)
        """
        task_id = task.get_task_id()
        
        try:
            # Check if task is already being processed in Gateway
            task_status = self.gateway_client.get_task_status(task_id)
            
            if task_status is None:
                # First time seeing this task - submit to Gateway
                self.logger.info(f"Submitting new task {task_id} to Gateway")
                
                variables = {}
                try:
                    # Extract all variables from task
                    variables = task.get_variables()
                except Exception as e:
                    self.logger.warning(f"Failed to get task variables: {e}")
                
                # Submit to Gateway
                if self.gateway_client.submit_task(task_id, topic, variables):
                    GATEWAY_TASKS.labels(topic=topic, status='submitted').inc()
                    self.logger.info(f"Task {task_id} submitted to Gateway successfully")
                else:
                    GATEWAY_TASKS.labels(topic=topic, status='submit_failed').inc()
                    self.logger.error(f"Failed to submit task {task_id} to Gateway")
                
                # Return empty (don't complete task yet)
                return None
            
            elif task_status.status == "sucesso":
                # Task completed successfully - complete in Camunda
                self.logger.info(f"Task {task_id} completed successfully in Gateway")
                TASK_COUNTER.labels(topic=topic, status='gateway_success').inc()
                GATEWAY_TASKS.labels(topic=topic, status='completed').inc()
                
                return self.complete_task(task, task_status.result or {})
            
            elif task_status.status == "erro":
                # Task failed in Gateway - fail in Camunda
                error_msg = task_status.error_message or "Gateway processing failed"
                self.logger.error(f"Task {task_id} failed in Gateway: {error_msg}")
                TASK_COUNTER.labels(topic=topic, status='gateway_failure').inc()
                GATEWAY_TASKS.labels(topic=topic, status='failed').inc()
                
                return self.fail_task(task, error_msg)
            
            else:
                # Task still processing (em_andamento or aguardando) - return empty
                self.logger.debug(f"Task {task_id} still processing in Gateway (status: {task_status.status})")
                GATEWAY_TASKS.labels(topic=topic, status='processing').inc()
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error handling task {task_id} via Gateway: {e}")
            GATEWAY_TASKS.labels(topic=topic, status='error').inc()
            
            # Fallback: fail the task
            return self.fail_task(task, f"Gateway communication error: {str(e)}")
    
    def _handle_task_direct(self, task, topic: str, handler_func):
        """
        Handle task directly (legacy mode)
        
        Args:
            task: Camunda task
            topic: Task topic
            handler_func: Task handler function
            
        Returns:
            Task completion result
        """
        task_id = task.get_task_id()
        
        try:
            self.logger.info(f"Processing task {task_id} directly for topic {topic}")
            
            # Call the actual handler
            result = handler_func(task)
            
            # Record success metrics
            TASK_COUNTER.labels(topic=topic, status='direct_success').inc()
            self.logger.info(f"Successfully completed task {task_id} directly")
            
            return result
            
        except Exception as e:
            # Record failure metrics
            TASK_COUNTER.labels(topic=topic, status='direct_failure').inc()
            self.logger.error(f"Direct processing failed for task {task_id}: {str(e)}")
            
            # Report failure to Camunda
            return task.failure(
                error_message=str(e),
                error_details=f"Worker {self.worker_id} failed to process task directly",
                retry_timeout=5000,
                max_retries=3
            )
    
    def start(self):
        """Start the worker (blocking operation)"""
        self.logger.info(f"Starting worker {self.worker_id}")
        
        # Health check for Gateway if enabled
        if self.gateway_enabled and self.gateway_client:
            health = self.gateway_client.health_check()
            if health['gateway_status'] != 'healthy':
                self.logger.warning(f"Gateway health check failed: {health}")
            else:
                self.logger.info(f"Gateway health check passed: {health['response_time_ms']:.1f}ms")
        
        try:
            # This is a blocking call
            self.camunda_worker.start()
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
            self._cleanup()
        except Exception as e:
            self.logger.error(f"Worker error: {str(e)}")
            self._cleanup()
            raise
    
    def _cleanup(self):
        """Cleanup resources on shutdown"""
        try:
            if self.gateway_client:
                self.gateway_client.close()
                self.logger.info("Gateway client connection closed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_variable(self, task, name: str, default: Any = None) -> Any:
        """Safely get a variable from the task"""
        try:
            return task.get_variable(name)
        except Exception:
            self.logger.warning(f"Variable '{name}' not found, using default: {default}")
            return default
    
    def complete_task(self, task, variables: Dict[str, Any] = None) -> Any:
        """Complete a task with optional variables (following official Camunda examples)"""
        variables = variables or {}
        task_id = task.get_task_id()
        self.logger.info(f"Completing task {task_id} with variables: {variables}")
        
        try:
            result = task.complete(variables)
            self.logger.info(f"Task {task_id} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {str(e)}")
            raise
    
    def fail_task(self, task, error_message: str, error_details: str = None, retries: int = 3, retry_timeout: int = 5000) -> Any:
        """Fail a task with error information (following official Camunda examples)"""
        task_id = task.get_task_id()
        self.logger.error(f"Failing task {task_id}: {error_message}")
        
        try:
            result = task.failure(
                error_message=error_message,
                error_details=error_details or error_message,
                retry_timeout=retry_timeout,
                max_retries=retries
            )
            self.logger.info(f"Task {task_id} marked as failed with {retries} retries")
            return result
        except Exception as e:
            self.logger.error(f"Failed to mark task {task_id} as failed: {str(e)}")
            raise
    
    def bpmn_error(self, task, error_code: str, error_message: str = None, variables: Dict[str, Any] = None) -> Any:
        """Report a BPMN error (following official Camunda examples)"""
        task_id = task.get_task_id()
        variables = variables or {}
        
        self.logger.warning(f"BPMN Error on task {task_id}: {error_code} - {error_message or error_code}")
        
        try:
            result = task.bpmn_error(
                error_code=error_code,
                error_message=error_message or error_code,
                variables=variables
            )
            self.logger.info(f"Task {task_id} reported BPMN error: {error_code}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to report BPMN error for task {task_id}: {str(e)}")
            raise