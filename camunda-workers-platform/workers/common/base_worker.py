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
TASK_COUNTER = Counter(
    "camunda_tasks_total", "Total number of tasks processed", ["topic", "status"]
)
TASK_DURATION = Histogram(
    "camunda_task_duration_seconds", "Time spent processing tasks", ["topic"]
)
ACTIVE_TASKS = Gauge(
    "camunda_active_tasks", "Number of currently active tasks", ["topic"]
)
GATEWAY_TASKS = Counter(
    "gateway_tasks_total", "Total number of tasks sent to gateway", ["topic", "status"]
)


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
        default_url = (
            "http://localhost:8080/camunda/engine-rest"
            if os.getenv("WORKERS_MODE", "separated") == "embedded"
            else "http://camunda:8080/camunda/engine-rest"
        )
        self.base_url = base_url or os.getenv("CAMUNDA_URL", default_url)
        self.auth = auth or self._get_auth_from_env()

        # Setup logging
        self.logger = self._setup_logging()

        # Initialize Gateway Client
        self.gateway_enabled = os.getenv("GATEWAY_ENABLED", "false").lower() == "true"
        self.gateway_client = GatewayClient(worker_id) if self.gateway_enabled else None
        self.gateway_base_url = os.getenv(
            "GATEWAY_URL", "http://camunda-worker-api-gateway-gateway-1:8000"
        )

        if self.gateway_enabled:
            self.logger.info(f"Worker API Gateway integration enabled for {worker_id}")
            self.logger.info(f"Gateway URL: {self.gateway_base_url}")
        else:
            self.logger.info(f"Direct Camunda processing mode for {worker_id}")

        # Initialize primary Camunda worker
        self._init_camunda_worker()

        # Start Prometheus metrics server
        self._start_metrics_server()

    def _get_auth_from_env(self) -> Optional[tuple]:
        """Get authentication from environment variables"""
        username = os.getenv("CAMUNDA_USERNAME")
        password = os.getenv("CAMUNDA_PASSWORD")
        return (username, password) if username and password else None

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        from .config import WorkerConfig

        log_level = getattr(logging, WorkerConfig.LOG_LEVEL.upper(), logging.WARNING)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )
        return logging.getLogger(f"CamundaWorker-{self.worker_id}")

    def _init_camunda_worker(self):
        """Initialize the primary Camunda external task worker"""
        from .config import WorkerConfig

        config = {
            "maxTasks": WorkerConfig.MAX_TASKS,
            "lockDuration": WorkerConfig.LOCK_DURATION,
            "asyncResponseTimeout": WorkerConfig.ASYNC_RESPONSE_TIMEOUT,
            "retries": WorkerConfig.RETRIES,
            "retryTimeout": WorkerConfig.RETRY_TIMEOUT,
            "sleepSeconds": WorkerConfig.SLEEP_SECONDS,
        }

        # Primary worker for backward compatibility
        # Add auth to config if available
        if self.auth:
            config["auth_basic"] = {"username": self.auth[0], "password": self.auth[1]}

        self.camunda_worker = ExternalTaskWorker(
            worker_id=self.worker_id, base_url=self.base_url, config=config
        )

        self.logger.info(
            f"Initialized primary Camunda worker {self.worker_id} connecting to {self.base_url}"
        )

    def _start_metrics_server(self):
        """Start Prometheus metrics HTTP server"""
        try:
            metrics_port = int(os.getenv("METRICS_PORT", "8000"))
            start_http_server(metrics_port)
            self.logger.info(
                f"Started Prometheus metrics server on port {metrics_port}"
            )
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

    def subscribe_multiple(
        self, topic_handlers: Dict[str, Any], handler_manages_gateway: bool = True
    ):
        """
        Subscribe to multiple topics with their respective handlers.
        Uses a single subscribe call with multiple topics.

        Args:
            topic_handlers: Dictionary mapping topic names to handler functions
                          Format: {"topic_name": handler_function}
            handler_manages_gateway: If True, handlers manage their own Gateway calls (new pattern)
                                   If False, BaseWorker manages Gateway (old pattern)
        """
        self.logger.info(
            f"Subscribing to {len(topic_handlers)} topics: {list(topic_handlers.keys())}"
        )

        # Store handlers for later use
        self.topic_handlers = topic_handlers
        self.handler_manages_gateway = handler_manages_gateway

        # Create a unified handler that dispatches to the correct handler based on topic
        def unified_handler(task):
            """Unified handler that dispatches to the correct topic handler"""
            topic = task.get_topic_name()
            start_time = time.time()
            task_id = task.get_task_id()

            self.logger.info(
                f"Executing external task for Topic: {topic}, Task ID: {task_id}"
            )

            # Update active tasks metric
            ACTIVE_TASKS.labels(topic=topic).inc()

            try:
                # Find the appropriate handler for this topic
                if topic not in self.topic_handlers:
                    self.logger.error(f"No handler found for topic {topic}")
                    return self.fail_task(
                        task, f"No handler configured for topic {topic}"
                    )

                handler_func = self.topic_handlers[topic]

                # Always call the handler - it decides how to process
                # The handler will use process_via_gateway() if needed
                result = handler_func(task)

                # Log result type for debugging
                if result is not None:
                    self.logger.debug(f"Handler returned result for task {task_id}")
                else:
                    self.logger.debug(f"Handler returned None for task {task_id}")

                return result

            except Exception as e:
                self.logger.error(f"Error in handler for task {task_id}: {str(e)}")
                import traceback

                traceback.print_exc()
                return self.fail_task(task, f"Handler error: {str(e)}", retries=3)

            finally:
                # Update metrics
                duration = time.time() - start_time
                TASK_DURATION.labels(topic=topic).observe(duration)
                ACTIVE_TASKS.labels(topic=topic).dec()

        # Subscribe to all topics at once with the unified handler
        topic_list = list(topic_handlers.keys())
        self.camunda_worker.subscribe(topic_list, unified_handler)
        self.logger.info(f"✅ Subscribed to all topics: {topic_list}")

    def _subscribe_worker_to_topic(
        self, worker: ExternalTaskWorker, topic: str, handler_func
    ):
        """
        Subscribe a specific worker to a topic with monitoring and error handling

        Args:
            worker: The ExternalTaskWorker instance
            topic: The topic name to subscribe to
            handler_func: Function to handle the task
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

        # Subscribe to the topic - this should not block
        worker.subscribe(topic, wrapped_handler)

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
                    GATEWAY_TASKS.labels(topic=topic, status="submitted").inc()
                    self.logger.info(
                        f"Task {task_id} submitted to Gateway successfully"
                    )
                    # Return empty (don't complete task yet - gateway will handle it)
                    return None
                else:
                    GATEWAY_TASKS.labels(topic=topic, status="submit_failed").inc()
                    self.logger.error(f"Failed to submit task {task_id} to Gateway")
                    # Gateway is unavailable - fail the task with retries
                    return self.fail_task(
                        task,
                        "Worker API Gateway is unavailable",
                        "Gateway connection failed - will retry",
                        retries=5,
                        retry_timeout=60000,  # Retry after 1 minute
                    )

            elif task_status.status == "sucesso":
                # Task completed successfully - complete in Camunda
                self.logger.info(f"Task {task_id} completed successfully in Gateway")
                TASK_COUNTER.labels(topic=topic, status="gateway_success").inc()
                GATEWAY_TASKS.labels(topic=topic, status="completed").inc()

                return self.complete_task(task, task_status.result or {})

            elif task_status.status == "erro":
                # Task failed in Gateway - fail in Camunda
                error_msg = task_status.error_message or "Gateway processing failed"
                self.logger.error(f"Task {task_id} failed in Gateway: {error_msg}")
                TASK_COUNTER.labels(topic=topic, status="gateway_failure").inc()
                GATEWAY_TASKS.labels(topic=topic, status="failed").inc()

                return self.fail_task(task, error_msg)

            else:
                # Task still processing (em_andamento or aguardando) - return empty
                self.logger.debug(
                    f"Task {task_id} still processing in Gateway (status: {task_status.status})"
                )
                GATEWAY_TASKS.labels(topic=topic, status="processing").inc()

                return None

        except Exception as e:
            self.logger.error(f"Error handling task {task_id} via Gateway: {e}")
            GATEWAY_TASKS.labels(topic=topic, status="error").inc()

            # Fallback: fail the task with retries
            return self.fail_task(
                task,
                f"Gateway communication error: {str(e)}",
                "Gateway error - will retry",
                retries=5,
                retry_timeout=60000,  # Retry after 1 minute
            )

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
            TASK_COUNTER.labels(topic=topic, status="direct_success").inc()
            self.logger.info(f"Successfully completed task {task_id} directly")

            return result

        except Exception as e:
            # Record failure metrics
            TASK_COUNTER.labels(topic=topic, status="direct_failure").inc()
            self.logger.error(f"Direct processing failed for task {task_id}: {str(e)}")

            # Report failure to Camunda
            return task.failure(
                error_message=str(e),
                error_details=f"Worker {self.worker_id} failed to process task directly",
                retry_timeout=5000,
                max_retries=3,
            )

    def start(self):
        """Start the worker (blocking operation)"""
        self.logger.info(f"Starting worker {self.worker_id}")

        # Health check for Gateway if enabled
        if self.gateway_enabled and self.gateway_client:
            health = self.gateway_client.health_check()
            if health["gateway_status"] != "healthy":
                self.logger.warning(f"Gateway health check failed: {health}")
            else:
                self.logger.info(
                    f"Gateway health check passed: {health['response_time_ms']:.1f}ms"
                )

        try:
            # Log topics being monitored
            if hasattr(self, "topic_handlers") and self.topic_handlers:
                topics = list(self.topic_handlers.keys())
                self.logger.info(
                    f"Starting worker monitoring {len(topics)} topic(s): {topics}"
                )
            else:
                self.logger.info("Starting worker in single-topic mode")

            # Start the primary worker which handles all subscribed topics
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

    def process_via_gateway(
        self,
        task,
        endpoint: str,
        timeout: int = 90,
        custom_payload: Dict[str, Any] = None,
    ) -> Any:
        """
        Helper method to process tasks via Gateway with intelligent error handling

        Implements smart error categorization:
        - 400/404/422: BPMN Error (business logic errors, no retry)
        - 408/429/502/503/504: Task Failure (recoverable, with retry)
        - 500: Depends on retry_allowed flag from Gateway

        Args:
            task: Camunda external task
            endpoint: Gateway API endpoint to call
            timeout: Request timeout in seconds
            custom_payload: Custom payload to send instead of default structure

        Returns:
            Task completion result (complete_task, fail_task, or bpmn_error)
        """
        import requests

        task_id = task.get_task_id()
        topic = task.get_topic_name()

        try:
            gateway_url = f"{self.gateway_base_url}{endpoint}"

            # Prepare payload - use custom if provided, otherwise default
            if custom_payload:
                payload = custom_payload
            else:
                payload = {
                    "task_id": task_id,
                    "process_instance_id": task.get_process_instance_id(),
                    "business_key": task.get_business_key(),
                    "topic_name": topic,
                    "worker_id": self.worker_id,
                    "variables": task.get_variables(),
                }

            self.logger.info(f"📤 Calling Gateway: {gateway_url}")

            # Make request WITHOUT raise_for_status() - we'll handle errors manually
            response = requests.post(
                gateway_url,
                json=payload,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )

            # SUCCESS PATH (2xx)
            if response.status_code == 200:
                try:
                    result = response.json()
                except Exception as e:
                    self.logger.error(f"❌ Failed to parse Gateway response: {e}")
                    self.logger.error(f"   Response text: {response.text[:500]}")
                    GATEWAY_TASKS.labels(topic=topic, status="parse_error").inc()
                    return self.fail_task(
                        task, "Invalid JSON response from Gateway", retries=3
                    )

                # Check status in response body
                if result.get("status") == "success":
                    # Success - complete task
                    camunda_variables = {
                        k: v
                        for k, v in result.items()
                        if k not in ["status", "message", "task_id", "timestamp"]
                    }
                    self.logger.info(f"✅ Task {task_id} processed successfully via Gateway")
                    GATEWAY_TASKS.labels(topic=topic, status="success").inc()
                    return self.complete_task(task, camunda_variables)

                elif result.get("status") == "error":
                    # Gateway returned structured error in body
                    error_msg = result.get("error_message", "Gateway processing failed")
                    error_code = result.get("error_code", "UNKNOWN_ERROR")
                    retry_allowed = result.get("retry_allowed", False)

                    self.logger.error(f"❌ Gateway error: [{error_code}] {error_msg}")
                    GATEWAY_TASKS.labels(topic=topic, status="business_error").inc()

                    if retry_allowed:
                        return self.fail_task(
                            task, error_msg, error_details=error_code, retries=3, retry_timeout=30000
                        )
                    else:
                        return self.bpmn_error(
                            task, error_code=error_code, error_message=error_msg
                        )
                else:
                    # Unexpected response format
                    error_msg = result.get("message", "Unexpected Gateway response format")
                    self.logger.error(f"⚠️ Unexpected Gateway response: {result}")
                    GATEWAY_TASKS.labels(topic=topic, status="unexpected_format").inc()
                    return self.fail_task(task, error_msg, retries=3)

            # ERROR PATH (4xx, 5xx)
            else:
                # Try to parse error response body
                try:
                    error_body = response.json()
                    error_msg = error_body.get("error_message", response.text[:200])
                    error_code = error_body.get("error_code", f"HTTP_{response.status_code}")
                    retry_allowed = error_body.get("retry_allowed", False)
                except Exception:
                    # Failed to parse - use raw response
                    error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
                    error_code = f"HTTP_{response.status_code}"
                    retry_allowed = response.status_code in [408, 429, 500, 502, 503, 504]

                # Log detailed error information
                self.logger.error(f"❌ Gateway HTTP error: {response.status_code}")
                self.logger.error(f"   Error Code: {error_code}")
                self.logger.error(f"   Message: {error_msg}")
                self.logger.error(f"   Retry Allowed: {retry_allowed}")
                if len(response.text) <= 500:
                    self.logger.error(f"   Response Body: {response.text}")

                # CATEGORIZE BY STATUS CODE

                # 400, 404, 422 = Client errors (validation, not found, etc.) → BPMN Error
                if response.status_code in [400, 404, 422]:
                    self.logger.warning(
                        f"⚠️ Client error (no retry): {error_code} - {error_msg}"
                    )
                    GATEWAY_TASKS.labels(topic=topic, status="validation_error").inc()
                    return self.bpmn_error(
                        task, error_code=error_code, error_message=error_msg
                    )

                # 408, 429 = Timeout, Rate Limit → Task Failure (retry with longer backoff)
                elif response.status_code in [408, 429]:
                    self.logger.warning(
                        f"⏱️ Timeout/Rate limit (will retry): {error_code} - {error_msg}"
                    )
                    GATEWAY_TASKS.labels(topic=topic, status="timeout_ratelimit").inc()
                    retry_timeout = 120000 if response.status_code == 429 else 60000
                    return self.fail_task(
                        task,
                        error_msg,
                        error_details=error_code,
                        retries=5,
                        retry_timeout=retry_timeout,
                    )

                # 502, 503, 504 = Server/Gateway errors → Task Failure (retry)
                elif response.status_code in [502, 503, 504]:
                    self.logger.warning(
                        f"🔧 Server error (will retry): {error_code} - {error_msg}"
                    )
                    GATEWAY_TASKS.labels(topic=topic, status="server_error").inc()
                    return self.fail_task(
                        task,
                        error_msg,
                        error_details=error_code,
                        retries=5,
                        retry_timeout=60000,
                    )

                # 500 = Internal Server Error → Check retry_allowed flag
                elif response.status_code == 500:
                    GATEWAY_TASKS.labels(topic=topic, status="internal_error").inc()

                    if retry_allowed:
                        self.logger.warning(
                            f"⚙️ Internal error (retry allowed): {error_code} - {error_msg}"
                        )
                        return self.fail_task(
                            task,
                            error_msg,
                            error_details=error_code,
                            retries=3,
                            retry_timeout=30000,
                        )
                    else:
                        self.logger.error(
                            f"❌ Internal error (no retry): {error_code} - {error_msg}"
                        )
                        return self.bpmn_error(
                            task, error_code=error_code, error_message=error_msg
                        )

                # Other status codes → Task Failure (retry)
                else:
                    self.logger.error(
                        f"❓ Unknown HTTP status {response.status_code}: {error_msg}"
                    )
                    GATEWAY_TASKS.labels(topic=topic, status="unknown_error").inc()
                    return self.fail_task(
                        task,
                        error_msg,
                        error_details=error_code,
                        retries=3,
                        retry_timeout=30000,
                    )

        # EXCEPTION HANDLING
        except requests.exceptions.Timeout:
            error_msg = f"Gateway timeout after {timeout}s for endpoint {endpoint}"
            self.logger.error(f"⏱️ {error_msg}")
            GATEWAY_TASKS.labels(topic=topic, status="timeout").inc()
            return self.fail_task(
                task,
                error_msg,
                error_details="REQUEST_TIMEOUT",
                retries=5,
                retry_timeout=60000,
            )

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Gateway connection failed: {str(e)}"
            self.logger.error(f"🔌 {error_msg}")
            GATEWAY_TASKS.labels(topic=topic, status="connection_error").inc()
            return self.fail_task(
                task,
                error_msg,
                error_details="CONNECTION_ERROR",
                retries=5,
                retry_timeout=60000,
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Gateway request failed: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            GATEWAY_TASKS.labels(topic=topic, status="request_error").inc()
            return self.fail_task(
                task,
                error_msg,
                error_details="REQUEST_EXCEPTION",
                retries=3,
                retry_timeout=30000,
            )

        except Exception as e:
            error_msg = f"Unexpected error calling Gateway: {str(e)}"
            self.logger.error(f"💥 {error_msg}", exc_info=True)
            GATEWAY_TASKS.labels(topic=topic, status="exception").inc()
            return self.fail_task(
                task,
                error_msg,
                error_details="UNEXPECTED_ERROR",
                retries=3,
                retry_timeout=30000,
            )

    def get_variable(self, task, name: str, default: Any = None) -> Any:
        """Safely get a variable from the task"""
        try:
            return task.get_variable(name)
        except Exception:
            self.logger.warning(
                f"Variable '{name}' not found, using default: {default}"
            )
            return default

    def complete_task(self, task, variables: Dict[str, Any] = None, use_local_variables: bool = True) -> Any:
        """
        Complete a task with optional variables

        Args:
            task: Camunda external task
            variables: Variables to return to the process
            use_local_variables: If True (default), uses localVariables (isolated per iteration in loops)
                               If False, uses global variables (shared across process instance)

        Note:
            In BPMN loops/multi-instance patterns, use_local_variables=True prevents
            one iteration from overwriting another's variables. This is the recommended
            default for most use cases.
        """
        variables = variables or {}
        task_id = task.get_task_id()
        scope = "local" if use_local_variables else "global"
        self.logger.info(f"Completing task {task_id} with {scope} variables: {list(variables.keys())}")

        try:
            if use_local_variables:
                # Use local_variables to prevent overwrites in loop iterations
                # Pass empty dict for global_variables, all data goes to local_variables
                result = task.complete(global_variables={}, local_variables=variables)
            else:
                # Use global variables (legacy behavior)
                # Pass variables to global_variables parameter
                result = task.complete(global_variables=variables, local_variables={})

            self.logger.info(f"Task {task_id} completed successfully ({scope} scope)")
            return result
        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {str(e)}")
            raise

    def fail_task(
        self,
        task,
        error_message: str,
        error_details: str = None,
        retries: int = 3,
        retry_timeout: int = 5000,
    ) -> Any:
        """Fail a task with error information (following official Camunda examples)"""
        task_id = task.get_task_id()
        self.logger.error(f"Failing task {task_id}: {error_message}")

        try:
            result = task.failure(
                error_message=error_message,
                error_details=error_details or error_message,
                retry_timeout=retry_timeout,
                max_retries=retries,
            )
            self.logger.info(f"Task {task_id} marked as failed with {retries} retries")
            return result
        except Exception as e:
            self.logger.error(f"Failed to mark task {task_id} as failed: {str(e)}")
            raise

    def bpmn_error(
        self,
        task,
        error_code: str,
        error_message: str = None,
        variables: Dict[str, Any] = None,
    ) -> Any:
        """
        Report a BPMN error

        Args:
            task: Camunda external task
            error_code: BPMN error code (used for error handling in the process)
            error_message: Human-readable error message
            variables: Variables to pass with the error (always global scope)

        Note:
            Unlike complete(), bpmn_error() only supports global variables.
            The Camunda Python client does not support local variables for BPMN errors.
        """
        task_id = task.get_task_id()
        variables = variables or {}

        self.logger.warning(
            f"BPMN Error on task {task_id}: {error_code} - {error_message or error_code}"
        )

        try:
            # BPMN errors only support global variables in the Camunda Python client
            result = task.bpmn_error(
                error_code=error_code,
                error_message=error_message or error_code,
                variables=variables,
            )

            self.logger.info(f"Task {task_id} reported BPMN error: {error_code}")
            return result
        except Exception as e:
            self.logger.error(
                f"Failed to report BPMN error for task {task_id}: {str(e)}"
            )
            raise
