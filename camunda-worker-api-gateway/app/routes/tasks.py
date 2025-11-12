"""
Task management routes
Endpoints for task submission, status checking, and retry operations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional

from models.task import TaskSubmission, TaskStatus
from models.error import ErrorResponse, HTTP_ERROR_RESPONSES
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


@router.post(
    "/submit",
    summary="Submit nova tarefa para processamento",
    response_description="Confirmação de submissão da tarefa",
    responses={
        500: HTTP_ERROR_RESPONSES[500],
    }
)
async def submit_task(
    task_submission: TaskSubmission,
    background_tasks: BackgroundTasks,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """
    **Submit uma nova tarefa para processamento assíncrono no Gateway.**

    Este endpoint é usado pelos workers para submeter tarefas do Camunda BPM
    ao Gateway para processamento. A tarefa é armazenada no MongoDB e
    processada em background.

    **Fluxo:**
    1. Worker busca tarefa do Camunda External Task
    2. Worker submete tarefa ao Gateway via POST /tasks/submit
    3. Gateway cria registro no MongoDB com status "em_andamento"
    4. Gateway processa tarefa em background
    5. Worker monitora status via GET /tasks/{task_id}/status
    6. Worker completa ou falha tarefa no Camunda baseado no resultado

    **Processamento:**
    - Tarefa é processada imediatamente em background
    - Status pode ser monitorado via endpoint /tasks/{task_id}/status
    - Em caso de falha, pode ser retentada via /tasks/{task_id}/retry

    **Exemplo de uso:**
    ```python
    response = await client.post("/tasks/submit", json={
        "task_id": "abc123-task-456",
        "worker_id": "buscar-publicacoes-worker-01",
        "topic": "buscar-publicacoes-diarias",
        "variables": {
            "data_inicio": "2024-01-15",
            "data_fim": "2024-01-15"
        }
    })
    ```

    **Retorno:**
    - `status`: "submitted"
    - `task_id`: ID da tarefa para monitoramento
    - `message`: Mensagem de confirmação
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


@router.get(
    "/{task_id}/status",
    summary="Consultar status de tarefa",
    response_model=TaskStatus,
    response_description="Status atual da tarefa com metadados e resultado",
    responses={
        404: HTTP_ERROR_RESPONSES[404],
        500: HTTP_ERROR_RESPONSES[500],
    }
)
async def get_task_status(
    task_id: str, task_manager: TaskManager = Depends(get_task_manager)
) -> TaskStatus:
    """
    **Consulta o status e resultado de uma tarefa em processamento.**

    Workers devem fazer polling neste endpoint para monitorar o progresso
    das tarefas submetidas ao Gateway.

    **Status possíveis:**
    - `em_andamento`: Tarefa sendo processada
    - `aguardando`: Aguardando resposta de serviço externo
    - `sucesso`: Processamento concluído com sucesso
    - `erro`: Falha no processamento

    **Substatus:**
    Fornece informação granular sobre a etapa atual:
    - "soap_request_enviado"
    - "processando_resposta"
    - "salvando_bronze"
    - "transformando_silver"
    - "concluido"

    **Metadata inclui:**
    - Número de retries
    - Mensagem de erro (se houver)
    - Steps de processamento
    - Tempo total de processamento

    **Exemplo de uso:**
    ```python
    # Worker faz polling a cada 5 segundos
    while True:
        status = await client.get(f"/tasks/{task_id}/status")
        if status["status"] in ["sucesso", "erro"]:
            break
        await asyncio.sleep(5)
    ```

    **Retorno:**
    - `task_id`: ID da tarefa
    - `status`: Status atual (enum)
    - `substatus`: Etapa atual de processamento
    - `result`: Resultado final (se concluído)
    - `error_message`: Mensagem de erro (se falhou)
    - `timestamps`: Timestamps de criação, início, conclusão
    - `metadata`: Metadados adicionais e histórico
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


@router.post(
    "/{task_id}/retry",
    summary="Retentar tarefa falhada",
    response_description="Confirmação de retry",
    responses={
        400: HTTP_ERROR_RESPONSES[400],
        404: HTTP_ERROR_RESPONSES[404],
        500: HTTP_ERROR_RESPONSES[500],
    }
)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """
    **Retenta uma tarefa que falhou no processamento.**

    Permite que workers ou processos manuais resubmetam tarefas que
    falharam por erros temporários (timeouts, indisponibilidade de serviços, etc.)

    **Regras:**
    - Apenas tarefas com status `erro` podem ser retentadas
    - Tarefa é resetada para status `em_andamento`
    - Substatus é marcado como "retrying"
    - Processamento é iniciado novamente em background
    - Contador de retries é incrementado nos metadados

    **Quando usar:**
    - Timeout em chamadas SOAP/API externas
    - Indisponibilidade temporária de MongoDB/Redis
    - Erros de rede transientes
    - Problemas temporários em serviços externos (CPJ, DW LAW, N8N)

    **Quando NÃO usar:**
    - Erros de validação de dados (não resolverão com retry)
    - Dados corrompidos ou inválidos
    - Erros de lógica de negócio

    **Exemplo de uso:**
    ```python
    # Worker detecta falha e decide retentar
    status = await client.get(f"/tasks/{task_id}/status")
    if status["status"] == "erro" and status["metadata"]["retries"] < 3:
        await client.post(f"/tasks/{task_id}/retry")
    ```

    **Retorno:**
    - `status`: "retrying"
    - `task_id`: ID da tarefa
    - `message`: Confirmação de resubmissão
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
