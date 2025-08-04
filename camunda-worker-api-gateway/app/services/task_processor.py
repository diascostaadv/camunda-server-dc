"""
Task Processor Service
Handles the actual processing logic for different task types
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from models.task import TaskSubmission, TaskStatusEnum
from models.movimentacao import MovimentacaoJudicial, MovimentacaoProcessingResult
from services.task_manager import TaskManager
from services.text_processor import limpar_texto_publicacao
from services.date_processor import converter_data_publicacao
from services.hash_generator import gerar_hash_unica
from services.movimentacao_service import movimentacao_service
from core.config import settings


logger = logging.getLogger(__name__)


class TaskProcessor:
    """Task processing service with topic-specific handlers"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        
        # Map topics to their processing methods
        self.topic_handlers = {
            "nova_publicacao": self._process_nova_publicacao,
            "say_hello": self._process_say_hello,
            "validate_document": self._process_validate_document,
            "process_data": self._process_process_data,
            "publish_content": self._process_publish_content,
            "send_notification": self._process_send_notification
        }
    
    async def process_task(self, task_submission: TaskSubmission):
        """
        Process a task based on its topic
        
        Args:
            task_submission: Task to process
        """
        task_id = task_submission.task_id
        topic = task_submission.topic
        
        try:
            # Update status to indicate processing started
            await self.task_manager.update_task_status(
                task_id,
                TaskStatusEnum.EM_ANDAMENTO,
                substatus="iniciando_processamento"
            )
            
            # Get topic-specific handler
            handler = self.topic_handlers.get(topic)
            if not handler:
                raise ValueError(f"Unsupported topic: {topic}")
            
            logger.info(f"🔄 Processing task {task_id} for topic {topic}")
            
            # Execute topic-specific processing
            result = await handler(task_submission)
            
            # Update task as completed
            await self.task_manager.update_task_status(
                task_id,
                TaskStatusEnum.SUCESSO,
                substatus="processamento_concluido",
                result=result
            )
            
            await self.task_manager.add_processing_step(
                task_id,
                "Task completed successfully"
            )
            
            logger.info(f"✅ Successfully processed task {task_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to process task {task_id}: {error_msg}")
            
            # Update task as failed
            await self.task_manager.update_task_status(
                task_id,
                TaskStatusEnum.ERRO,
                substatus="erro_processamento",
                error_message=error_msg
            )
            
            await self.task_manager.add_processing_step(
                task_id,
                f"Task failed: {error_msg}"
            )
            
            # Increment retry count
            retry_count = await self.task_manager.increment_retry_count(task_id)
            
            # If we haven't exceeded retry limit, we could reschedule
            if retry_count < settings.TASK_RETRY_LIMIT:
                logger.info(f"🔄 Task {task_id} will be retried (attempt {retry_count + 1})")
    
    async def _process_nova_publicacao(self, task_submission: TaskSubmission) -> Dict[str, Any]:
        """
        Process nova_publicacao task - Passo 1: Persistência e Higienização
        
        Args:
            task_submission: Task submission data
            
        Returns:
            Processing result
        """
        await self.task_manager.update_task_status(
            task_submission.task_id,
            TaskStatusEnum.EM_ANDAMENTO,
            substatus="iniciando_processamento_movimentacao"
        )
        
        variables = task_submission.variables
        processing_result = MovimentacaoProcessingResult(success=False)
        
        try:
            # Passo 1: Validar campos obrigatórios
            await self.task_manager.add_processing_step(
                task_submission.task_id,
                "Validando campos obrigatórios"
            )
            
            required_fields = ['numero_processo', 'data_publicacao', 'texto_publicacao', 'fonte', 'tribunal', 'instancia']
            for field in required_fields:
                if not variables.get(field):
                    raise ValueError(f"Campo obrigatório ausente: {field}")
            
            processing_result.add_step("Validação de campos concluída")
            
            # Passo 2: Criar modelo da movimentação
            movimentacao = MovimentacaoJudicial(
                numero_processo=variables['numero_processo'],
                data_publicacao=variables['data_publicacao'],
                texto_publicacao=variables['texto_publicacao'],
                fonte=variables['fonte'],
                tribunal=variables['tribunal'],
                instancia=variables['instancia']
            )
            
            await self.task_manager.update_task_status(
                task_submission.task_id,
                TaskStatusEnum.EM_ANDAMENTO,
                substatus="convertendo_data_publicacao"
            )
            
            # Passo 3: Converter data de publicação
            processing_result.add_step("Convertendo data de publicação")
            movimentacao.data_publicacao_parsed = converter_data_publicacao(movimentacao.data_publicacao)
            
            await self.task_manager.update_task_status(
                task_submission.task_id,
                TaskStatusEnum.EM_ANDAMENTO,
                substatus="limpando_texto_publicacao"
            )
            
            # Passo 4: Limpar texto da publicação
            processing_result.add_step("Limpando e sanitizando texto")
            movimentacao.texto_publicacao_limpo = limpar_texto_publicacao(movimentacao.texto_publicacao)
            
            await self.task_manager.update_task_status(
                task_submission.task_id,
                TaskStatusEnum.EM_ANDAMENTO,
                substatus="gerando_hash_unica"
            )
            
            # Passo 5: Gerar hash única
            processing_result.add_step("Gerando hash única para detecção de duplicatas")
            movimentacao.hash_unica = gerar_hash_unica(
                movimentacao.numero_processo,
                movimentacao.data_publicacao,
                movimentacao.texto_publicacao,
                movimentacao.tribunal
            )
            
            await self.task_manager.update_task_status(
                task_submission.task_id,
                TaskStatusEnum.EM_ANDAMENTO,
                substatus="persistindo_mongodb"
            )
            
            # Passo 6: Definir status e metadata
            movimentacao.status_processamento = "step_1_complete"
            movimentacao.timestamp_processamento = datetime.utcnow()
            movimentacao.metadata = {
                "passo_atual": 1,
                "proximos_passos": ["tratamento_duplicadas", "classificacao_ia"],
                "task_id": task_submission.task_id,
                "worker_id": task_submission.worker_id,
                "validacoes": {
                    "data_valida": True,
                    "texto_limpo": True,
                    "hash_gerada": True
                }
            }
            
            # Passo 7: Salvar no MongoDB
            processing_result.add_step("Salvando movimentação no MongoDB")
            
            # Certificar que o serviço foi inicializado
            if not movimentacao_service.collection:
                from services.task_manager import TaskManager
                # Usar a mesma conexão do TaskManager
                await movimentacao_service.initialize(self.task_manager.database)
            
            save_result = await movimentacao_service.salvar_movimentacao(movimentacao)
            
            if not save_result.get("success"):
                if save_result.get("error") == "duplicate":
                    # Movimentação duplicada - não é erro, mas aviso
                    processing_result.add_step("Movimentação duplicada detectada via hash")
                    return {
                        "status": "warning",
                        "message": "Movimentação já existe (duplicata detectada)",
                        "hash_unica": movimentacao.hash_unica,
                        "numero_processo": movimentacao.numero_processo,
                        "timestamp": datetime.utcnow().isoformat(),
                        "step_1_status": "duplicate_detected"
                    }
                else:
                    raise Exception(f"Erro ao salvar movimentação: {save_result}")
            
            processing_result.success = True
            processing_result.movimentacao = movimentacao
            processing_result.add_step("Passo 1 concluído com sucesso")
            
            await self.task_manager.add_processing_step(
                task_submission.task_id,
                "Movimentação processada e salva com sucesso"
            )
            
            return {
                "status": "success",
                "message": "Passo 1 - Persistência e Higienização concluído",
                "movimentacao": {
                    "numero_processo": movimentacao.numero_processo,
                    "tribunal": movimentacao.tribunal,
                    "fonte": movimentacao.fonte,
                    "hash_unica": movimentacao.hash_unica,
                    "texto_original_length": len(movimentacao.texto_publicacao),
                    "texto_limpo_length": len(movimentacao.texto_publicacao_limpo),
                    "data_publicacao_original": movimentacao.data_publicacao,
                    "data_publicacao_parsed": movimentacao.data_publicacao_parsed.isoformat()
                },
                "processing_steps": processing_result.processing_steps,
                "timestamp": datetime.utcnow().isoformat(),
                "step_1_status": "completed",
                "next_steps": ["tratamento_duplicadas", "classificacao_ia"],
                "mongodb_id": save_result.get("id")
            }
            
        except Exception as e:
            error_msg = str(e)
            processing_result.error_message = error_msg
            processing_result.add_step(f"Erro no processamento: {error_msg}")
            
            logger.error(f"Erro no processamento da movimentação: {error_msg}")
            raise Exception(f"Falha no Passo 1: {error_msg}")
    
    async def _process_say_hello(self, task_submission: TaskSubmission) -> Dict[str, Any]:
        """
        Process say_hello task (migrated from HelloWorldWorker)
        
        Args:
            task_submission: Task submission data
            
        Returns:
            Processing result
        """
        await self.task_manager.update_task_status(
            task_submission.task_id,
            TaskStatusEnum.EM_ANDAMENTO,
            substatus="gerando_cumprimento"
        )
        
        variables = task_submission.variables
        name = variables.get("name", "World")
        
        await self.task_manager.add_processing_step(
            task_submission.task_id,
            f"Generating greeting for: {name}"
        )
        
        # Simulate processing
        await asyncio.sleep(1)
        
        greeting = f"Hello, {name}!"
        
        return {
            "greeting": greeting,
            "processed_at": datetime.utcnow().isoformat(),
            "worker_id": task_submission.worker_id,
            "original_name": name
        }
    
    async def _process_validate_document(self, task_submission: TaskSubmission) -> Dict[str, Any]:
        """
        Process validate_document task
        
        Args:
            task_submission: Task submission data
            
        Returns:
            Processing result
        """
        await self.task_manager.update_task_status(
            task_submission.task_id,
            TaskStatusEnum.EM_ANDAMENTO,
            substatus="validando_documento"
        )
        
        variables = task_submission.variables
        document = variables.get("document", {})
        
        await self.task_manager.add_processing_step(
            task_submission.task_id,
            "Starting document validation"
        )
        
        # Simulate validation logic
        await asyncio.sleep(2)
        
        # Mock validation result
        validation_result = "approved"  # or "rejected"
        
        return {
            "validation_result": validation_result,
            "validated_document": document,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _process_process_data(self, task_submission: TaskSubmission) -> Dict[str, Any]:
        """
        Process process_data task
        
        Args:
            task_submission: Task submission data
            
        Returns:
            Processing result
        """
        await self.task_manager.update_task_status(
            task_submission.task_id,
            TaskStatusEnum.EM_ANDAMENTO,
            substatus="processando_dados"
        )
        
        # Simulate data processing
        await asyncio.sleep(3)
        
        return {
            "processed_data": {"status": "processed"},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _process_publish_content(self, task_submission: TaskSubmission) -> Dict[str, Any]:
        """
        Process publish_content task
        
        Args:
            task_submission: Task submission data
            
        Returns:
            Processing result
        """
        await self.task_manager.update_task_status(
            task_submission.task_id,
            TaskStatusEnum.AGUARDANDO,
            substatus="publicando_conteudo"
        )
        
        # Simulate content publication
        await asyncio.sleep(4)
        
        return {
            "publication_status": "completed",
            "published_targets": 2,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _process_send_notification(self, task_submission: TaskSubmission) -> Dict[str, Any]:
        """
        Process send_notification task
        
        Args:
            task_submission: Task submission data
            
        Returns:
            Processing result
        """
        await self.task_manager.update_task_status(
            task_submission.task_id,
            TaskStatusEnum.EM_ANDAMENTO,
            substatus="enviando_notificacao"
        )
        
        # Simulate notification sending
        await asyncio.sleep(1)
        
        return {
            "notification_sent": True,
            "recipients": ["admin@example.com"],
            "timestamp": datetime.utcnow().isoformat()
        }