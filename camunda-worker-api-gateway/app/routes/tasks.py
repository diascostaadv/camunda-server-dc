"""
Task management routes
Endpoints for task submission, status checking, and retry operations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional

from models.task import TaskSubmission, TaskStatus
from services.task_manager import TaskManager
from .dependencies import get_task_manager


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        404: {"description": "Task not found"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"},
    },
)


@router.post("/submit")
async def submit_task(
    task_submission: TaskSubmission,
    background_tasks: BackgroundTasks,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """
    Submit a new task for processing

    Args:
        task_submission: Task data from worker
        background_tasks: FastAPI background tasks
        task_manager: Task manager dependency

    Returns:
        dict: Task submission confirmation
    """
    try:
        # Create task in database
        task = await task_manager.create_task(
            task_id=task_submission.task_id,
            worker_id=task_submission.worker_id,
            topic=task_submission.topic,
            variables=task_submission.variables,
        )

        # Process task in background directly
        background_tasks.add_task(process_task_direct, task_submission, task_manager)

        return {
            "status": "submitted",
            "task_id": task_submission.task_id,
            "message": "Task submitted for processing",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str, task_manager: TaskManager = Depends(get_task_manager)
) -> TaskStatus:
    """
    Get task status and result

    Args:
        task_id: Camunda task ID
        task_manager: Task manager dependency

    Returns:
        TaskStatus: Current task status and details
    """
    try:
        task = await task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskStatus(
            task_id=task["task_id"],
            status=task["status"],
            substatus=task.get("substatus"),
            result=task.get("result"),
            error_message=task.get("metadata", {}).get("error_message"),
            timestamps=task["timestamps"],
            metadata=task.get("metadata", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """
    Retry a failed task

    Args:
        task_id: Camunda task ID
        background_tasks: FastAPI background tasks
        task_manager: Task manager dependency

    Returns:
        dict: Retry confirmation
    """
    try:
        task = await task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task["status"] != "erro":
            raise HTTPException(
                status_code=400, detail="Only failed tasks can be retried"
            )

        # Reset task status
        await task_manager.update_task_status(task_id, "em_andamento", "retrying")

        # Resubmit for processing
        task_submission = TaskSubmission(
            task_id=task["task_id"],
            worker_id=task["worker_id"],
            topic=task["topic"],
            variables=task["variables"],
        )

        background_tasks.add_task(process_task_direct, task_submission, task_manager)

        return {
            "status": "retrying",
            "task_id": task_id,
            "message": "Task resubmitted for processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry task: {str(e)}")


async def process_task_direct(
    task_submission: TaskSubmission, task_manager: TaskManager
):
    """
    Direct task processing (fallback when RabbitMQ is not available)

    Args:
        task_submission: Task to process
        task_manager: Task manager instance
    """
    try:
        # Import here to avoid circular imports
        from services.task_processor import TaskProcessor

        processor = TaskProcessor(task_manager)
        await processor.process_task(task_submission)

    except Exception as e:
        print(f"❌ Failed to process task {task_submission.task_id}: {e}")
        await task_manager.update_task_status(
            task_submission.task_id, "erro", error_message=str(e)
        )
