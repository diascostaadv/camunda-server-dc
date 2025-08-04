"""
Movimentação Service
Serviço para persistência e gerenciamento de movimentações judiciais no MongoDB
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
import pymongo

from models.movimentacao import MovimentacaoJudicial, MovimentacaoQuery, MovimentacaoStatistics
from core.config import settings

logger = logging.getLogger(__name__)


class MovimentacaoService:
    """Serviço para gerenciamento de movimentações judiciais"""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database
        self.collection: Optional[AsyncIOMotorCollection] = None
        self._collection_name = "movimentacoes_judiciais"
        
    async def initialize(self, database: AsyncIOMotorDatabase):
        """
        Inicializa o serviço com conexão ao banco
        
        Args:
            database: Instância do banco MongoDB
        """
        try:
            self.database = database
            self.collection = database[self._collection_name]
            
            # Cria índices para performance
            await self._create_indexes()
            
            logger.info(f"✅ MovimentacaoService inicializado com collection: {self._collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar MovimentacaoService: {e}")
            raise
    
    async def _create_indexes(self):
        """Cria índices no MongoDB para otimizar consultas"""
        try:
            # Índice único para hash (detecção de duplicatas)
            await self.collection.create_index([
                ("hash_unica", pymongo.ASCENDING)
            ], unique=True, background=True)
            
            # Índices compostos para consultas frequentes
            await self.collection.create_index([
                ("numero_processo", pymongo.ASCENDING),
                ("tribunal", pymongo.ASCENDING)
            ], background=True)
            
            await self.collection.create_index([
                ("fonte", pymongo.ASCENDING),
                ("timestamp_processamento", pymongo.DESCENDING)
            ], background=True)
            
            await self.collection.create_index([
                ("data_publicacao_parsed", pymongo.DESCENDING)
            ], background=True)
            
            await self.collection.create_index([
                ("status_processamento", pymongo.ASCENDING),
                ("timestamp_processamento", pymongo.DESCENDING)
            ], background=True)
            
            # Índice de texto para busca textual
            await self.collection.create_index([
                ("texto_publicacao_limpo", pymongo.TEXT)
            ], background=True)
            
            logger.info("✅ Índices criados para movimentações judiciais")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar índices: {e}")
    
    async def salvar_movimentacao(self, movimentacao: MovimentacaoJudicial) -> Dict[str, Any]:
        """
        Salva movimentação no MongoDB
        
        Args:
            movimentacao: Dados da movimentação processada
            
        Returns:
            dict: Resultado da operação
            
        Raises:
            Exception: Se não conseguir salvar
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            # Adiciona timestamp de processamento se não existir
            if not movimentacao.timestamp_processamento:
                movimentacao.timestamp_processamento = datetime.utcnow()
            
            # Prepara documento para inserção
            doc = movimentacao.to_dict()
            
            # Remove campos None para economizar espaço
            doc = {k: v for k, v in doc.items() if v is not None}
            
            logger.debug(f"Salvando movimentação processo: {movimentacao.numero_processo}")
            
            # Tenta inserir no MongoDB
            result = await self.collection.insert_one(doc)
            
            if result.inserted_id:
                logger.info(f"✅ Movimentação salva com ID: {result.inserted_id}")
                return {
                    "success": True,
                    "id": str(result.inserted_id),
                    "hash_unica": movimentacao.hash_unica,
                    "numero_processo": movimentacao.numero_processo
                }
            else:
                raise Exception("Falha ao inserir no MongoDB")
                
        except pymongo.errors.DuplicateKeyError as e:
            # Hash duplicada - movimentação já existe
            logger.warning(f"⚠️ Movimentação duplicada detectada: {movimentacao.hash_unica}")
            return {
                "success": False,
                "error": "duplicate",
                "message": "Movimentação já existe (hash duplicada)",
                "hash_unica": movimentacao.hash_unica
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar movimentação: {e}")
            raise
    
    async def buscar_por_hash(self, hash_unica: str) -> Optional[Dict[str, Any]]:
        """
        Busca movimentação pela hash única
        
        Args:
            hash_unica: Hash única da movimentação
            
        Returns:
            dict: Documento da movimentação ou None
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            doc = await self.collection.find_one({"hash_unica": hash_unica})
            if doc:
                # Remove _id do MongoDB para retorno limpo
                doc.pop("_id", None)
            return doc
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar por hash {hash_unica}: {e}")
            raise
    
    async def buscar_duplicatas(
        self, 
        numero_processo: str, 
        tribunal: str,
        data_publicacao: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca possíveis duplicatas por processo e tribunal
        
        Args:
            numero_processo: Número do processo
            tribunal: Tribunal
            data_publicacao: Data de publicação (opcional)
            
        Returns:
            list: Lista de possíveis duplicatas
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            filtro = {
                "numero_processo": numero_processo,
                "tribunal": tribunal
            }
            
            if data_publicacao:
                filtro["data_publicacao"] = data_publicacao
            
            cursor = self.collection.find(filtro)
            duplicatas = []
            
            async for doc in cursor:
                doc.pop("_id", None)
                duplicatas.append(doc)
            
            return duplicatas
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar duplicatas: {e}")
            raise
    
    async def consultar_movimentacoes(self, query: MovimentacaoQuery) -> List[Dict[str, Any]]:
        """
        Consulta movimentações com filtros
        
        Args:
            query: Parâmetros de consulta
            
        Returns:
            list: Lista de movimentações
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            # Constrói filtros
            filtros = {}
            
            if query.numero_processo:
                filtros["numero_processo"] = query.numero_processo
            
            if query.tribunal:
                filtros["tribunal"] = query.tribunal
                
            if query.fonte:
                filtros["fonte"] = query.fonte
                
            if query.status_processamento:
                filtros["status_processamento"] = query.status_processamento
            
            # Filtros de data
            if query.data_inicio or query.data_fim:
                data_filter = {}
                if query.data_inicio:
                    data_filter["$gte"] = query.data_inicio
                if query.data_fim:
                    data_filter["$lte"] = query.data_fim
                filtros["data_publicacao_parsed"] = data_filter
            
            # Executa consulta
            cursor = self.collection.find(filtros)
            cursor = cursor.sort("timestamp_processamento", -1)
            cursor = cursor.skip(query.offset).limit(query.limit)
            
            movimentacoes = []
            async for doc in cursor:
                doc.pop("_id", None)
                movimentacoes.append(doc)
            
            logger.debug(f"Consulta retornou {len(movimentacoes)} movimentações")
            return movimentacoes
            
        except Exception as e:
            logger.error(f"❌ Erro na consulta: {e}")
            raise
    
    async def atualizar_status_processamento(
        self, 
        hash_unica: str, 
        novo_status: str,
        metadata_adicional: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atualiza status de processamento de uma movimentação
        
        Args:
            hash_unica: Hash única da movimentação
            novo_status: Novo status de processamento
            metadata_adicional: Metadados adicionais (opcional)
            
        Returns:
            bool: True se atualizou com sucesso
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            update_data = {
                "status_processamento": novo_status,
                "timestamp_processamento": datetime.utcnow()
            }
            
            if metadata_adicional:
                for key, value in metadata_adicional.items():
                    update_data[f"metadata.{key}"] = value
            
            result = await self.collection.update_one(
                {"hash_unica": hash_unica},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Status atualizado para {novo_status}: {hash_unica}")
                return True
            else:
                logger.warning(f"⚠️ Movimentação não encontrada para atualização: {hash_unica}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status: {e}")
            raise
    
    async def obter_estatisticas(self) -> MovimentacaoStatistics:
        """
        Obtém estatísticas de processamento
        
        Returns:
            MovimentacaoStatistics: Estatísticas das movimentações
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            # Total de movimentações
            total = await self.collection.count_documents({})
            
            # Por status
            pipeline_status = [
                {"$group": {"_id": "$status_processamento", "count": {"$sum": 1}}}
            ]
            status_result = await self.collection.aggregate(pipeline_status).to_list(None)
            por_status = {item["_id"]: item["count"] for item in status_result}
            
            # Por fonte
            pipeline_fonte = [
                {"$group": {"_id": "$fonte", "count": {"$sum": 1}}}
            ]
            fonte_result = await self.collection.aggregate(pipeline_fonte).to_list(None)
            por_fonte = {item["_id"]: item["count"] for item in fonte_result}
            
            # Por tribunal
            pipeline_tribunal = [
                {"$group": {"_id": "$tribunal", "count": {"$sum": 1}}}
            ]
            tribunal_result = await self.collection.aggregate(pipeline_tribunal).to_list(None)
            por_tribunal = {item["_id"]: item["count"] for item in tribunal_result}
            
            # Taxa de sucesso
            sucessos = por_status.get("step_1_complete", 0)
            taxa_sucesso = (sucessos / total * 100) if total > 0 else 0
            
            return MovimentacaoStatistics(
                total_movimentacoes=total,
                por_status=por_status,
                por_fonte=por_fonte,
                por_tribunal=por_tribunal,
                taxa_sucesso=taxa_sucesso
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            raise
    
    async def limpar_movimentacoes_antigas(self, dias: int = 30) -> int:
        """
        Remove movimentações antigas para limpeza
        
        Args:
            dias: Número de dias para manter
            
        Returns:
            int: Número de documentos removidos
        """
        if not self.collection:
            raise RuntimeError("MovimentacaoService não foi inicializado")
        
        try:
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - dias)
            
            result = await self.collection.delete_many({
                "timestamp_processamento": {"$lt": cutoff_date},
                "status_processamento": {"$in": ["step_1_complete", "error"]}
            })
            
            if result.deleted_count > 0:
                logger.info(f"✅ Removidas {result.deleted_count} movimentações antigas")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza: {e}")
            raise


# Instância global do serviço
movimentacao_service = MovimentacaoService()