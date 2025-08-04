"""
Task models for Worker API Gateway
Pydantic models for task data validation and serialization
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    """Task status enumeration"""
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO = "aguardando"
    SUCESSO = "sucesso"
    ERRO = "erro"


class TaskSubmission(BaseModel):
    """Model for task submission from workers"""
    
    task_id: str = Field(..., description="Camunda task ID")
    worker_id: str = Field(..., description="Worker identifier")
    topic: str = Field(..., description="Task topic/type")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Task variables from Camunda")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskTimestamps(BaseModel):
    """Task timestamp tracking"""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TaskMetadata(BaseModel):
    """Task metadata and processing information"""
    
    retries: int = 0
    error_message: Optional[str] = None
    processing_steps: List[str] = Field(default_factory=list)
    worker_version: Optional[str] = None
    processing_time_ms: Optional[int] = None


class TaskStatus(BaseModel):
    """Task status response model"""
    
    task_id: str
    status: TaskStatusEnum
    substatus: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamps: TaskTimestamps
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)


class TaskResult(BaseModel):
    """Task processing result"""
    
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_ms: int
    substatus_history: List[str] = Field(default_factory=list)


class Task(BaseModel):
    """Complete task model for database storage"""
    
    task_id: str = Field(..., description="Camunda task ID")
    worker_id: str = Field(..., description="Worker identifier")
    topic: str = Field(..., description="Task topic/type")
    status: TaskStatusEnum = TaskStatusEnum.EM_ANDAMENTO
    substatus: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    timestamps: TaskTimestamps = Field(default_factory=TaskTimestamps)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.model_dump()
        
        # Convert datetime objects to ISO strings for MongoDB
        timestamps = data.get("timestamps", {})
        for key, value in timestamps.items():
            if isinstance(value, datetime):
                timestamps[key] = value.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from MongoDB document"""
        # Convert ISO strings back to datetime objects
        timestamps = data.get("timestamps", {})
        for key, value in timestamps.items():
            if isinstance(value, str):
                try:
                    timestamps[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
        
        return cls(**data)


class SubstatusUpdate(BaseModel):
    """Model for substatus updates during processing"""
    
    task_id: str
    substatus: str
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskQuery(BaseModel):
    """Model for task queries and filtering"""
    
    worker_id: Optional[str] = None
    topic: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    
    
class TaskStatistics(BaseModel):
    """Model for task processing statistics"""
    
    total_tasks: int
    by_status: Dict[str, int]
    by_topic: Dict[str, int]
    by_worker: Dict[str, int]
    average_processing_time_ms: Optional[float] = None
    success_rate: float