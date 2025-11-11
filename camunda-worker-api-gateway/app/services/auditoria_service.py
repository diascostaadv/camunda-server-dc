"""
Serviço de auditoria para marcação de publicações
Gerencia logs detalhados de todas as tentativas de marcação
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import MongoClient

from models.auditoria import (
    LogMarcacaoPublicacao,
    TentativaMarcacao,
    StatusMarcacao,
    ConsultaLogRequest,
    ConsultaLogResponse,
)

logger = logging.getLogger(__name__)


class AuditoriaService:
    """Serviço para gerenciar logs de auditoria de marcação de publicações"""

    def __init__(self, mongo_client: MongoClient, database_name: str = "worker_gateway"):
        """
        Inicializa o serviço de auditoria

        Args:
            mongo_client: Cliente MongoDB
            database_name: Nome do banco de dados
        """
        self.client = mongo_client
        self.db = mongo_client[database_name]
        self.col_logs_marcacao = self.db["logs_marcacao_publicacoes"]

        # Criar índices para otimizar consultas
        self._criar_indices()

    def _criar_indices(self):
        """Cria índices para otimizar consultas de logs"""
        try:
            # Índice por cod_publicacao (consultas mais comuns)
            self.col_logs_marcacao.create_index("cod_publicacao")

            # Índice por lote_id
            self.col_logs_marcacao.create_index("lote_id")

            # Índice por status atual
            self.col_logs_marcacao.create_index("status_atual")

            # Índice por timestamp (para queries por data)
            self.col_logs_marcacao.create_index("timestamp_primeira_tentativa")

            # Índice composto para consultas complexas
            self.col_logs_marcacao.create_index(
                [("lote_id", 1), ("status_atual", 1), ("timestamp_primeira_tentativa", -1)]
            )

            logger.debug("Índices de auditoria criados/verificados")
        except Exception as e:
            logger.warning(f"Erro ao criar índices de auditoria: {e}")

    def iniciar_log_marcacao(
        self,
        cod_publicacao: int,
        lote_id: Optional[str] = None,
        execucao_id: Optional[str] = None,
        publicacao_bronze_id: Optional[str] = None,
        snapshot_publicacao: Optional[Dict[str, Any]] = None,
        contexto: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Inicia um novo log de marcação

        Args:
            cod_publicacao: Código da publicação
            lote_id: ID do lote
            execucao_id: ID da execução
            publicacao_bronze_id: ID do documento bronze
            snapshot_publicacao: Cópia dos dados da publicação
            contexto: Contexto adicional (worker_id, task_id, etc.)

        Returns:
            str: ID do log criado
        """
        try:
            log = LogMarcacaoPublicacao(
                cod_publicacao=cod_publicacao,
                lote_id=lote_id,
                execucao_id=execucao_id,
                publicacao_bronze_id=publicacao_bronze_id,
                status_atual=StatusMarcacao.PENDENTE,
                snapshot_publicacao=snapshot_publicacao,
                timestamp_primeira_tentativa=datetime.now(),
            )

            # Adicionar contexto se fornecido
            if contexto:
                log.worker_id = contexto.get("worker_id")
                log.task_id = contexto.get("task_id")
                log.process_instance_id = contexto.get("process_instance_id")
                log.metadata = contexto.get("metadata", {})

            # Inserir no MongoDB
            result = self.col_logs_marcacao.insert_one(log.model_dump())
            log_id = str(result.inserted_id)

            logger.debug(f"Log de marcação iniciado: {log_id} (cod_publicacao={cod_publicacao})")
            return log_id

        except Exception as e:
            logger.error(f"Erro ao iniciar log de marcação para {cod_publicacao}: {e}")
            raise

    def registrar_tentativa(
        self,
        log_id: str,
        status: StatusMarcacao,
        duracao_ms: Optional[float] = None,
        mensagem_erro: Optional[str] = None,
        detalhes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Registra uma tentativa de marcação no log

        Args:
            log_id: ID do log
            status: Status da tentativa
            duracao_ms: Duração em milissegundos
            mensagem_erro: Mensagem de erro (se falhou)
            detalhes: Detalhes adicionais

        Returns:
            bool: True se registrado com sucesso
        """
        try:
            # Buscar log atual
            log_doc = self.col_logs_marcacao.find_one({"_id": ObjectId(log_id)})
            if not log_doc:
                logger.warning(f"Log {log_id} não encontrado")
                return False

            # Criar registro da tentativa
            numero_tentativa = log_doc.get("total_tentativas", 0) + 1
            tentativa = TentativaMarcacao(
                numero_tentativa=numero_tentativa,
                timestamp=datetime.now(),
                status=status,
                duracao_ms=duracao_ms,
                mensagem_erro=mensagem_erro,
                detalhes=detalhes or {},
            )

            # Atualizar log
            update_data = {
                "total_tentativas": numero_tentativa,
                "timestamp_ultima_tentativa": datetime.now(),
                "status_atual": status.value,
                "$push": {"tentativas": tentativa.model_dump()},
            }

            # Se foi sucesso, registrar timestamp de sucesso
            if status == StatusMarcacao.SUCESSO:
                update_data["marcada_com_sucesso"] = True
                update_data["timestamp_sucesso"] = datetime.now()

            # Calcular duração total (garantir que não seja None)
            if duracao_ms:
                duracao_total_atual = log_doc.get("duracao_total_ms") or 0
                update_data["duracao_total_ms"] = duracao_total_atual + duracao_ms

            self.col_logs_marcacao.update_one({"_id": ObjectId(log_id)}, {"$set": update_data})

            logger.debug(
                f"Tentativa {numero_tentativa} registrada para log {log_id}: {status.value}"
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao registrar tentativa no log {log_id}: {e}")
            return False

    def marcar_como_sucesso(
        self,
        log_id: str,
        duracao_ms: Optional[float] = None,
        detalhes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Marca o log como sucesso

        Args:
            log_id: ID do log
            duracao_ms: Duração da operação
            detalhes: Detalhes adicionais

        Returns:
            bool: True se marcado com sucesso
        """
        return self.registrar_tentativa(
            log_id=log_id,
            status=StatusMarcacao.SUCESSO,
            duracao_ms=duracao_ms,
            detalhes=detalhes,
        )

    def marcar_como_falha(
        self,
        log_id: str,
        status: StatusMarcacao,
        mensagem_erro: str,
        duracao_ms: Optional[float] = None,
        detalhes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Marca o log como falha

        Args:
            log_id: ID do log
            status: Status de falha específico
            mensagem_erro: Mensagem de erro
            duracao_ms: Duração da operação
            detalhes: Detalhes adicionais

        Returns:
            bool: True se marcado com sucesso
        """
        return self.registrar_tentativa(
            log_id=log_id,
            status=status,
            duracao_ms=duracao_ms,
            mensagem_erro=mensagem_erro,
            detalhes=detalhes,
        )

    def consultar_logs(self, filtros: ConsultaLogRequest) -> ConsultaLogResponse:
        """
        Consulta logs de marcação com filtros

        Args:
            filtros: Filtros de busca

        Returns:
            ConsultaLogResponse: Logs encontrados com estatísticas
        """
        try:
            # Construir query MongoDB
            query = {}

            if filtros.cod_publicacao:
                query["cod_publicacao"] = filtros.cod_publicacao

            if filtros.lote_id:
                query["lote_id"] = filtros.lote_id

            if filtros.status:
                query["status_atual"] = filtros.status.value

            if filtros.apenas_falhas:
                query["marcada_com_sucesso"] = False

            if filtros.data_inicio or filtros.data_fim:
                date_query = {}
                if filtros.data_inicio:
                    date_query["$gte"] = filtros.data_inicio
                if filtros.data_fim:
                    date_query["$lte"] = filtros.data_fim
                query["timestamp_primeira_tentativa"] = date_query

            # Contar total
            total = self.col_logs_marcacao.count_documents(query)

            # Buscar logs com paginação
            cursor = (
                self.col_logs_marcacao.find(query)
                .sort("timestamp_primeira_tentativa", -1)
                .skip(filtros.offset)
                .limit(filtros.limite)
            )

            logs = [LogMarcacaoPublicacao(**doc) for doc in cursor]

            # Calcular estatísticas
            stats_pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": "$status_atual",
                        "count": {"$sum": 1},
                        "total_tentativas": {"$sum": "$total_tentativas"},
                    }
                },
            ]

            stats_cursor = self.col_logs_marcacao.aggregate(stats_pipeline)
            estatisticas = {
                "por_status": {stat["_id"]: stat for stat in stats_cursor},
                "total_registros": total,
            }

            return ConsultaLogResponse(
                total_registros=total, logs=logs, estatisticas=estatisticas
            )

        except Exception as e:
            logger.error(f"Erro ao consultar logs: {e}")
            raise

    def obter_log_por_publicacao(self, cod_publicacao: int) -> Optional[LogMarcacaoPublicacao]:
        """
        Obtém o log mais recente de uma publicação

        Args:
            cod_publicacao: Código da publicação

        Returns:
            LogMarcacaoPublicacao ou None
        """
        try:
            doc = self.col_logs_marcacao.find_one(
                {"cod_publicacao": cod_publicacao},
                sort=[("timestamp_primeira_tentativa", -1)],
            )

            if doc:
                return LogMarcacaoPublicacao(**doc)
            return None

        except Exception as e:
            logger.error(f"Erro ao obter log da publicação {cod_publicacao}: {e}")
            return None

    def obter_estatisticas_lote(self, lote_id: str) -> Dict[str, Any]:
        """
        Obtém estatísticas de marcação de um lote

        Args:
            lote_id: ID do lote

        Returns:
            dict: Estatísticas do lote
        """
        try:
            pipeline = [
                {"$match": {"lote_id": lote_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_publicacoes": {"$sum": 1},
                        "sucesso": {
                            "$sum": {"$cond": [{"$eq": ["$marcada_com_sucesso", True]}, 1, 0]}
                        },
                        "falhas": {
                            "$sum": {"$cond": [{"$eq": ["$marcada_com_sucesso", False]}, 1, 0]}
                        },
                        "total_tentativas": {"$sum": "$total_tentativas"},
                        "duracao_total_ms": {"$sum": "$duracao_total_ms"},
                    }
                },
            ]

            result = list(self.col_logs_marcacao.aggregate(pipeline))

            if result:
                stats = result[0]
                stats.pop("_id", None)
                return stats

            return {"total_publicacoes": 0, "sucesso": 0, "falhas": 0}

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do lote {lote_id}: {e}")
            return {}
