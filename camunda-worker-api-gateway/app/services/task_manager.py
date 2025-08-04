"""
Task Manager Service
Centralized task management with MongoDB persistence
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
import pymongo

from models.task import Task, TaskStatusEnum, TaskTimestamps, TaskMetadata, TaskQuery, TaskStatistics
from core.config import settings


logger = logging.getLogger(__name__)


class TaskManager:
    """Centralized task management service"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.tasks_collection: Optional[AsyncIOMotorCollection] = None
        self._connected = False
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                **settings.get_mongodb_connection_options()
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            self.database = self.client[settings.MONGODB_DATABASE]
            self.tasks_collection = self.database[settings.MONGODB_COLLECTION_TASKS]
            
            # Create indexes for better performance
            await self._create_indexes()
            
            self._connected = True
            logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DATABASE}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("📴 Disconnected from MongoDB")
    
    def is_connected(self) -> bool:
        """Check if connected to MongoDB"""
        return self._connected and self.client is not None
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Compound index for efficient queries
            await self.tasks_collection.create_index([
                ("task_id", pymongo.ASCENDING)
            ], unique=True)
            
            await self.tasks_collection.create_index([
                ("worker_id", pymongo.ASCENDING),
                ("status", pymongo.ASCENDING)
            ])
            
            await self.tasks_collection.create_index([
                ("topic", pymongo.ASCENDING),
                ("timestamps.created_at", pymongo.DESCENDING)
            ])
            
            await self.tasks_collection.create_index([
                ("status", pymongo.ASCENDING),
                ("timestamps.created_at", pymongo.DESCENDING)
            ])
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create indexes: {e}")
    
    async def create_task(
        self,
        task_id: str,
        worker_id: str,
        topic: str,
        variables: Dict[str, Any] = None
    ) -> Task:
        """
        Create a new task
        
        Args:
            task_id: Camunda task ID
            worker_id: Worker identifier
            topic: Task topic/type
            variables: Task variables from Camunda
            
        Returns:
            Created task
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            task = Task(
                task_id=task_id,
                worker_id=worker_id,
                topic=topic,
                variables=variables or {},
                status=TaskStatusEnum.EM_ANDAMENTO,
                timestamps=TaskTimestamps(),
                metadata=TaskMetadata()
            )
            
            # Insert into database
            await self.tasks_collection.insert_one(task.to_dict())
            
            logger.info(f"✅ Created task {task_id} for worker {worker_id} on topic {topic}")
            return task
            
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"⚠️ Task {task_id} already exists")
            # Return existing task
            existing_task = await self.get_task(task_id)
            if existing_task:
                return Task.from_dict(existing_task)
            raise
            
        except Exception as e:
            logger.error(f"❌ Failed to create task {task_id}: {e}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID
        
        Args:
            task_id: Camunda task ID
            
        Returns:
            Task document or None
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            task_doc = await self.tasks_collection.find_one({"task_id": task_id})
            if task_doc:
                # Remove MongoDB _id field
                task_doc.pop("_id", None)
            return task_doc
            
        except Exception as e:
            logger.error(f"❌ Failed to get task {task_id}: {e}")
            raise
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        substatus: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update task status
        
        Args:
            task_id: Camunda task ID
            status: New status
            substatus: Optional substatus
            result: Optional result data
            error_message: Optional error message
            
        Returns:
            True if updated successfully
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            update_data = {
                "status": status,
                "timestamps.last_updated": datetime.utcnow().isoformat()
            }
            
            if substatus:
                update_data["substatus"] = substatus
            
            if result:
                update_data["result"] = result
            
            if error_message:
                update_data["metadata.error_message"] = error_message
            
            # Set completion timestamp for final states
            if status in [TaskStatusEnum.SUCESSO, TaskStatusEnum.ERRO]:
                update_data["timestamps.completed_at"] = datetime.utcnow().isoformat()
            
            # Set started timestamp if moving from initial state
            if status != TaskStatusEnum.EM_ANDAMENTO:
                current_task = await self.get_task(task_id)
                if current_task and not current_task.get("timestamps", {}).get("started_at"):
                    update_data["timestamps.started_at"] = datetime.utcnow().isoformat()
            
            result = await self.tasks_collection.update_one(
                {"task_id": task_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated task {task_id} status to {status}")
                return True
            else:
                logger.warning(f"⚠️ Task {task_id} not found for status update")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update task {task_id} status: {e}")
            raise
    
    async def add_processing_step(self, task_id: str, step: str) -> bool:
        """
        Add a processing step to task metadata
        
        Args:
            task_id: Camunda task ID
            step: Processing step description
            
        Returns:
            True if added successfully
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            step_with_timestamp = f"{datetime.utcnow().isoformat()}: {step}"
            
            result = await self.tasks_collection.update_one(
                {"task_id": task_id},
                {
                    "$push": {"metadata.processing_steps": step_with_timestamp},
                    "$set": {"timestamps.last_updated": datetime.utcnow().isoformat()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to add processing step to task {task_id}: {e}")
            raise
    
    async def increment_retry_count(self, task_id: str) -> int:
        """
        Increment retry count for a task
        
        Args:
            task_id: Camunda task ID
            
        Returns:
            New retry count
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            result = await self.tasks_collection.update_one(
                {"task_id": task_id},
                {
                    "$inc": {"metadata.retries": 1},
                    "$set": {"timestamps.last_updated": datetime.utcnow().isoformat()}
                }
            )
            
            if result.modified_count > 0:
                task = await self.get_task(task_id)
                retry_count = task.get("metadata", {}).get("retries", 0) if task else 0
                logger.info(f"✅ Incremented retry count for task {task_id} to {retry_count}")
                return retry_count
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Failed to increment retry count for task {task_id}: {e}")
            raise
    
    async def query_tasks(self, query: TaskQuery) -> List[Dict[str, Any]]:
        """
        Query tasks with filtering
        
        Args:
            query: Task query parameters
            
        Returns:
            List of task documents
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            filter_criteria = {}
            
            if query.worker_id:
                filter_criteria["worker_id"] = query.worker_id
            
            if query.topic:
                filter_criteria["topic"] = query.topic
            
            if query.status:
                filter_criteria["status"] = query.status
            
            cursor = self.tasks_collection.find(filter_criteria)
            cursor = cursor.sort("timestamps.created_at", -1)
            cursor = cursor.skip(query.offset).limit(query.limit)
            
            tasks = []
            async for task_doc in cursor:
                task_doc.pop("_id", None)
                tasks.append(task_doc)
            
            return tasks
            
        except Exception as e:
            logger.error(f"❌ Failed to query tasks: {e}")
            raise
    
    async def get_task_statistics(self) -> TaskStatistics:
        """
        Get task processing statistics
        
        Returns:
            Task statistics
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            # Total tasks
            total_tasks = await self.tasks_collection.count_documents({})
            
            # By status
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_result = await self.tasks_collection.aggregate(status_pipeline).to_list(None)
            by_status = {item["_id"]: item["count"] for item in status_result}
            
            # By topic
            topic_pipeline = [
                {"$group": {"_id": "$topic", "count": {"$sum": 1}}}
            ]
            topic_result = await self.tasks_collection.aggregate(topic_pipeline).to_list(None)
            by_topic = {item["_id"]: item["count"] for item in topic_result}
            
            # By worker
            worker_pipeline = [
                {"$group": {"_id": "$worker_id", "count": {"$sum": 1}}}
            ]
            worker_result = await self.tasks_collection.aggregate(worker_pipeline).to_list(None)
            by_worker = {item["_id"]: item["count"] for item in worker_result}
            
            # Success rate
            success_count = by_status.get(TaskStatusEnum.SUCESSO, 0)
            success_rate = (success_count / total_tasks * 100) if total_tasks > 0 else 0
            
            return TaskStatistics(
                total_tasks=total_tasks,
                by_status=by_status,
                by_topic=by_topic,
                by_worker=by_worker,
                success_rate=success_rate
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to get task statistics: {e}")
            raise
    
    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """
        Clean up old completed tasks
        
        Args:
            days: Number of days to keep tasks
            
        Returns:
            Number of deleted tasks
        """
        if not self.is_connected():
            raise RuntimeError("Task Manager not connected to database")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            delete_criteria = {
                "status": {"$in": [TaskStatusEnum.SUCESSO, TaskStatusEnum.ERRO]},
                "timestamps.completed_at": {"$lt": cutoff_date.isoformat()}
            }
            
            result = await self.tasks_collection.delete_many(delete_criteria)
            
            if result.deleted_count > 0:
                logger.info(f"✅ Cleaned up {result.deleted_count} old tasks")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old tasks: {e}")
            raise
    
    def get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat()