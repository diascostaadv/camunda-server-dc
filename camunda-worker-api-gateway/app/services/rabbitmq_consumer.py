"""
RabbitMQ Consumer Service
Handles asynchronous task processing via RabbitMQ
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import aio_pika
from aio_pika import Message, IncomingMessage, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange, AbstractQueue

from models.task import TaskSubmission
from services.task_manager import TaskManager
from services.task_processor import TaskProcessor
from core.config import settings


logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """RabbitMQ consumer for asynchronous task processing"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.task_processor = TaskProcessor(task_manager)
        
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchange: Optional[AbstractExchange] = None
        self.queues: Dict[str, AbstractQueue] = {}
        
        self._connected = False
        self._consuming = False
    
    async def start(self):
        """Start RabbitMQ consumer"""
        try:
            # Connect to RabbitMQ
            await self._connect()
            
            # Setup exchange and queues
            await self._setup_exchange()
            await self._setup_queues()
            
            # Start consuming
            await self._start_consuming()
            
            self._consuming = True
            logger.info("✅ RabbitMQ consumer started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start RabbitMQ consumer: {e}")
            raise
    
    async def stop(self):
        """Stop RabbitMQ consumer"""
        try:
            self._consuming = False
            
            # Stop consuming from queues
            for queue in self.queues.values():
                await queue.cancel()
            
            # Close connection
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            self._connected = False
            logger.info("⏹️ RabbitMQ consumer stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop RabbitMQ consumer: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ"""
        return self._connected and self.connection and not self.connection.is_closed
    
    async def _connect(self):
        """Connect to RabbitMQ server"""
        try:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                **settings.get_rabbitmq_connection_options()
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)  # Process up to 10 messages concurrently
            
            self._connected = True
            logger.info(f"✅ Connected to RabbitMQ: {settings.RABBITMQ_URL}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    async def _setup_exchange(self):
        """Setup RabbitMQ exchange"""
        try:
            self.exchange = await self.channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info(f"✅ Exchange '{settings.RABBITMQ_EXCHANGE}' declared")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup exchange: {e}")
            raise
    
    async def _setup_queues(self):
        """Setup RabbitMQ queues for different topics"""
        try:
            # Create queues for each supported topic
            for topic in settings.SUPPORTED_TOPICS:
                queue_name = f"{settings.RABBITMQ_QUEUE_PREFIX}.submit.{topic}"
                routing_key = settings.get_task_routing_key(topic, "submit")
                
                queue = await self.channel.declare_queue(
                    queue_name,
                    durable=True,
                    arguments={
                        "x-message-ttl": settings.TASK_TIMEOUT * 1000,  # Convert to milliseconds
                        "x-max-retries": settings.TASK_RETRY_LIMIT
                    }
                )
                
                await queue.bind(self.exchange, routing_key)
                self.queues[topic] = queue
                
                logger.info(f"✅ Queue '{queue_name}' declared and bound to '{routing_key}'")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup queues: {e}")
            raise
    
    async def _start_consuming(self):
        """Start consuming messages from queues"""
        try:
            for topic, queue in self.queues.items():
                await queue.consume(
                    lambda message, t=topic: self._process_message(message, t),
                    no_ack=False
                )
                logger.info(f"✅ Started consuming from queue for topic '{topic}'")
                
        except Exception as e:
            logger.error(f"❌ Failed to start consuming: {e}")
            raise
    
    async def _process_message(self, message: IncomingMessage, topic: str):
        """
        Process incoming RabbitMQ message
        
        Args:
            message: Incoming RabbitMQ message
            topic: Task topic
        """
        async with message.process():
            try:
                # Parse message body
                body = json.loads(message.body.decode())
                task_submission = TaskSubmission(**body)
                
                logger.info(f"📨 Received task {task_submission.task_id} for topic {topic}")
                
                # Add processing step
                await self.task_manager.add_processing_step(
                    task_submission.task_id,
                    f"Started processing via RabbitMQ"
                )
                
                # Process the task
                await self.task_processor.process_task(task_submission)
                
                logger.info(f"✅ Completed processing task {task_submission.task_id}")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in message: {e}")
                # Reject message without requeue
                await message.reject(requeue=False)
                
            except Exception as e:
                logger.error(f"❌ Failed to process message for topic {topic}: {e}")
                
                # Try to update task status if we can parse the task_id
                try:
                    body = json.loads(message.body.decode())
                    task_id = body.get("task_id")
                    if task_id:
                        await self.task_manager.update_task_status(
                            task_id,
                            "erro",
                            error_message=f"RabbitMQ processing failed: {str(e)}"
                        )
                except:
                    pass
                
                # Reject message with requeue for retry
                retry_count = message.headers.get("x-delivery-count", 0) if message.headers else 0
                if retry_count < settings.TASK_RETRY_LIMIT:
                    await message.reject(requeue=True)
                else:
                    await message.reject(requeue=False)
                    logger.error(f"❌ Message exceeded retry limit, discarding")
    
    async def publish_task(self, task_submission: TaskSubmission):
        """
        Publish task to RabbitMQ for processing
        
        Args:
            task_submission: Task to publish
        """
        if not self.is_connected():
            raise RuntimeError("RabbitMQ consumer not connected")
        
        try:
            routing_key = settings.get_task_routing_key(task_submission.topic, "submit")
            
            message_body = task_submission.model_dump_json().encode()
            message = Message(
                message_body,
                headers={
                    "task_id": task_submission.task_id,
                    "worker_id": task_submission.worker_id,
                    "topic": task_submission.topic,
                    "timestamp": self.task_manager.get_timestamp()
                },
                delivery_mode=2  # Persistent message
            )
            
            await self.exchange.publish(message, routing_key)
            
            logger.info(f"📤 Published task {task_submission.task_id} to queue via {routing_key}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish task {task_submission.task_id}: {e}")
            raise
    
    async def publish_result(self, worker_id: str, task_id: str, result: Dict[str, Any]):
        """
        Publish task result to worker-specific queue
        
        Args:
            worker_id: Target worker ID
            task_id: Task ID
            result: Processing result
        """
        if not self.is_connected():
            raise RuntimeError("RabbitMQ consumer not connected")
        
        try:
            # Create worker-specific queue if it doesn't exist
            queue_name = settings.get_worker_queue_name(worker_id)
            queue = await self.channel.declare_queue(queue_name, durable=True)
            
            message_body = json.dumps({
                "task_id": task_id,
                "result": result,
                "timestamp": self.task_manager.get_timestamp()
            }).encode()
            
            message = Message(
                message_body,
                headers={
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "message_type": "result"
                },
                delivery_mode=2
            )
            
            await self.channel.default_exchange.publish(
                message,
                routing_key=queue_name
            )
            
            logger.info(f"📤 Published result for task {task_id} to worker {worker_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish result for task {task_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        RabbitMQ health check
        
        Returns:
            Health status information
        """
        return {
            "connected": self.is_connected(),
            "consuming": self._consuming,
            "queues_count": len(self.queues),
            "supported_topics": settings.SUPPORTED_TOPICS
        }